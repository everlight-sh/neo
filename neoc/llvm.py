"""LLVM IR backend: Neo graph -> LLVM IR -> native code (the rustc pipeline).

Lowering uses allocas for every binder and lets LLVM's mem2reg/SROA promote
them to SSA registers, as clang and rustc do. Parallel `sum`/`arr` regions are
outlined into separate functions with an explicit context struct (closure
conversion) and dispatched by the Neo runtime's per-region kernel workers.

Memory: array values are { ptr, len, owned, control }; heap elements store
{ ptr, len, tagged-control }, packing ownership into bit 2 of the aligned
control pointer. Bit 1 identifies private counts, and 1 is the immortal
sentinel. These tags are cleared before accessing a counted allocation.
Immutable copies retain a
reference-counted backing buffer; mutations detach when shared. Ownership moves
along a uniqueness
discipline decided per scope by `consume_plan`: a final consuming use with no
later read or consumption on any continuation (passed to a call, updated
with `set`, returned, stored into a loop state) is *moved* at that use, and
`set` then updates in place. Whatever still owns a buffer at scope exit frees
it. Arrays of records are laid out struct-of-arrays inside one buffer, fields
ordered by size; the program never sees the layout.

Proven facts reach LLVM as `llvm.assume` (index ranges, dereferenceable
buffers), so the optimizer can speculate and vectorize what the checker proved.
"""
from __future__ import annotations
import struct
import re
import os
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from . import syntax as S
from . import vectorize as VZ
from . import ranges as Ranges
from .linear import Lin, cmp, and_, entails

ARR = "%ax_arr"

@dataclass
class Val:
    name: str
    ty: str
    def __str__(self): return f"{self.ty} {self.name}"

@dataclass
class Slot:
    ptr: str
    ty: str
    own_ptr: Optional[str] = None            # i64 flag for array variables
    consume: Set[int] = field(default_factory=set)   # node ids at which this variable is moved
    axty: object = None
    borrowed: bool = False
    field_consume: dict = field(default_factory=dict)
    resource_live: Optional[str] = None
    unique_at_exit: bool = False
    always_unique: bool = False              # set-only loop state, made unique at loop entry
    linear: object = False                   # keeps UNIQUE flags on moves: True (array) or field names (record)

RUNTIME_LIBCALLS=frozenset({'memcpy','memmove','memset','memcmp','bcmp','bzero','calloc','memset_pattern16'})

def lty(t) -> str:
    if isinstance(t,S.TRef):return "{ i64, i64 }"
    if isinstance(t,S.TFn):return "ptr"
    if t == S.I64: return "i64"
    if t == S.F64: return "double"
    if t == S.BOOL: return "i1"
    if t == S.U8: return "i8"
    if t == S.U16: return "i16"
    if t == S.I32: return "i32"
    if t == S.PTR: return "ptr"
    if t == S.UNIT: return "i8"  # unit values have no payload; function ABI returns void
    if isinstance(t, S.TArr): return ARR
    if isinstance(t, S.TRec): return "{ " + ", ".join(lty(ft) for _, ft in t.fields) + " }"
    raise TypeError(t)

def scalar_size(t) -> int:
    if isinstance(t,S.TRef):return 16
    if isinstance(t, S.TArr): return 32
    if isinstance(t, S.TRec):
        offset, alignment = 0, 1
        for _, ft in t.fields:
            size = scalar_size(ft); align = min(8, size)
            offset = (offset + align - 1) // align * align + size
            alignment = max(alignment, align)
        return max(1,(offset + alignment - 1) // alignment * alignment)
    if t == S.I32: return 4
    if t == S.U16: return 2
    return 1 if t in (S.BOOL, S.U8, S.UNIT) else 8

def storage_ty(t) -> str:
    if isinstance(t,S.TArr):return '{ ptr, i64, i64 }'
    if isinstance(t,S.TRec):return '{ '+', '.join(storage_ty(ft) for _,ft in t.fields)+' }'
    return lty(t)

def storage_size(t) -> int:
    if isinstance(t,S.TArr):return 24
    if isinstance(t,S.TRec):
        offset,alignment=0,1
        for _,ft in t.fields:
            size=storage_size(ft);align=min(8,size)
            offset=(offset+align-1)//align*align+size;alignment=max(alignment,align)
        return max(1,(offset+alignment-1)//alignment*alignment)
    return scalar_size(t)

def return_type(t): return "void" if t == S.UNIT else lty(t)

def elem_size(t: S.TArr) -> int:
    if isinstance(t.elem, S.TRec): return max(1,sum(storage_size(ft) for _, ft in t.elem.fields))
    return storage_size(t.elem)

def rec_layout(rt: S.TRec) -> List[Tuple[int, str, int, int]]:
    """(field index, llvm type, size, prefix bytes per element) in layout order: big fields first."""
    order = sorted(range(len(rt.fields)), key=lambda k: -storage_size(rt.fields[k][1]))
    out, prefix = [], 0
    for k in order:
        ft = rt.fields[k][1]
        out.append((k, storage_ty(ft), storage_size(ft), prefix))
        prefix += storage_size(ft)
    return out

def zero(t) -> str:
    if isinstance(t,S.TRef):return 'zeroinitializer'
    if isinstance(t,S.TFn):return "null"
    if isinstance(t, S.TArr): return 'zeroinitializer'
    if t == S.F64: return "0.0"
    if isinstance(t, S.TRec): return "{ " + ", ".join(f"{lty(ft)} {zero(ft)}" for _, ft in t.fields) + " }"
    return "0"

def fresh_array_result(e):
    if isinstance(e,S.Check):return fresh_array_result(e.body)
    if isinstance(e,S.ArrC):return True
    return isinstance(e,S.Call) and getattr(e,'builtin',None) in ('set','push','concat','byte_copy','byte_write_le')

IN_PLACE_WRITERS = ('set', 'byte_write_le', 'byte_copy')

def set_only_state(loop, k) -> bool:
    """A scalar-array loop state that is only read (len, indexing, byte reads)
    and replaced by in-place writes of itself. Once unique at entry it stays
    unique: reads share nothing, and each successor is either the state
    itself or a chain of set/byte_write_le/byte_copy writes rooted at it,
    possibly selected by if/let/check, whose result is the unique buffer."""
    name = loop.names[k]
    t = loop.state_tys[k]
    if not isinstance(t, S.TArr) or managed(t.elem): return False
    writers = []
    def successor(node, written):
        # The tree of values the next state may be: every leaf is the state
        # (passed through unchanged) or an in-place writer chain over it.
        if isinstance(node, S.Var): return node.name == name
        if isinstance(node, S.Check): return reads_only(node.pred) and successor(node.body, written)
        if isinstance(node, S.If): return reads_only(node.cond) and successor(node.then, written) and successor(node.els, written)
        # A let naming the state would make the leaf another value.
        if isinstance(node, S.Let): return node.name != name and reads_only(node.value) and successor(node.body, written)
        if isinstance(node, S.Call) and getattr(node, 'builtin', None) in IN_PLACE_WRITERS:
            writers.append(node)
            return all(reads_only(a) for a in node.args[1:]) and successor(node.args[0], True)
        return False
    def reads_only(node):
        if isinstance(node, S.Var): return node.name != name
        if isinstance(node, S.Len) and isinstance(node.expr, S.Var): return True
        if isinstance(node, S.Index) and isinstance(node.arr, S.Var) and node.arr.name == name: return reads_only(node.idx)
        # Observers that copy bytes out and keep no reference to the state.
        if isinstance(node, S.Call) and getattr(node, 'builtin', None) in ('byte_read_le', 'byte_equal'):
            return all(reads_only(a) if not (isinstance(a, S.Var) and a.name == name) else True for a in node.args)
        return all(reads_only(c) for c in S.children(node))
    if not successor(loop.nexts[k], False) or not writers: return False
    others = [x for j, x in enumerate(loop.nexts) if j != k]
    return reads_only(loop.cond) and all(reads_only(x) for x in others)

def managed(t):
    return isinstance(t, S.TArr) or isinstance(t, S.TRec) and any(managed(ft) for _, ft in t.fields)

def case_constant(k):
    """The integer value of an i64/u8/u16 literal usable as a switch case."""
    if isinstance(k, S.Num): return k.value
    if isinstance(k, S.Byte): return k.value
    if isinstance(k, S.Cast) and k.to == S.U16 and isinstance(k.expr, S.Num): return k.expr.value & 0xFFFF
    return None

def pure_scrutinee(x):
    """A read that cannot trap, allocate or consume: a variable or its fields."""
    if isinstance(x, S.Var): return True
    return isinstance(x, S.Field) and pure_scrutinee(x.expr)

def fconst(v: float) -> str:
    return "0x" + struct.pack(">d", v).hex().upper()

def cstr(s: str) -> Tuple[str, int]:
    b = s.encode("utf-8") + b"\0"
    return "".join(chr(ch) if 32 <= ch < 127 and ch not in (34, 92) else f"\\{ch:02X}" for ch in b), len(b)

# ---------------------------------------------------------------- uniqueness analysis
@dataclass(frozen=True)
class Summary:
    c: int          # consumptions on this path
    r: bool         # any read on this path
    bad: bool       # a read after a consumption, or two consumptions
    ids: frozenset  # consuming node ids
    blocked: frozenset = frozenset()  # consuming sites followed by another use on any path

def seq(a: List[Summary], b: List[Summary]) -> List[Summary]:
    out = {}
    for x in a:
        for y in b:
            later_use = y.r or y.c > 0
            s = Summary(min(2, x.c + y.c), x.r or y.r, x.bad or y.bad or (x.c > 0 and later_use), x.ids | y.ids,
                        x.blocked | y.blocked | (x.ids if later_use else frozenset()) |
                        (y.ids if x.c > 0 else frozenset()))
            key = (s.c, s.r, s.bad)
            out[key] = Summary(s.c, s.r, s.bad, out[key].ids | s.ids, out[key].blocked | s.blocked) if key in out else s
    return list(out.values())

EMPTY = [Summary(0, False, False, frozenset())]
def READ(): return [Summary(0, True, False, frozenset())]
def downgrade(a: List[Summary]) -> List[Summary]:
    return [Summary(0, x.r or x.c > 0, x.bad, frozenset(), x.blocked | x.ids) for x in a]

def paths(e: S.Node, name: str, as_read: bool = False, projection=None) -> List[Summary]:
    def walk(child, binding, as_read=False): return paths(child,binding,as_read,projection)
    if isinstance(e, S.Var):
        if e.name != name: return EMPTY
        return READ() if as_read or projection is not None else [Summary(1, False, False, frozenset([id(e)]))]
    if isinstance(e, (S.Num, S.Flt, S.BoolLit, S.Str, S.Byte)): return EMPTY
    if isinstance(e, S.Bin):
        l, r = walk(e.left, name), walk(e.right, name)
        return seq(l, r) + l if e.op in ("&&", "||") else seq(l, r)
    if isinstance(e, S.Un): return walk(e.expr, name)
    if isinstance(e, S.Cast): return walk(e.expr, name)
    if isinstance(e, S.Len): return walk(e.expr, name, as_read=True)
    if isinstance(e, S.Index): return seq(walk(e.arr, name, as_read=True), walk(e.idx, name))
    if isinstance(e, S.Field) and isinstance(e.expr,S.Var) and e.expr.name==name and projection is not None:
        if e.name!=projection:return EMPTY
        return READ() if as_read or not managed(e.ty) else [Summary(1,False,False,frozenset([id(e)]))]
    if isinstance(e, S.Field): return walk(e.expr, name, as_read=as_read or not managed(e.ty))
    if isinstance(e, S.RecLit):
        out = EMPTY
        given = dict(e.fields)
        for field, _ in e.ty.fields: out = seq(out, walk(given[field], name))
        return out
    if isinstance(e, S.With):
        if projection is not None and isinstance(e.expr, S.Var) and e.expr.name == name:
            # Replaced fields are not read from the old value at all.
            replaced = {field for field, _ in e.fields}
            out = EMPTY if projection in replaced else [Summary(1,False,False,frozenset([id(e)]))]
        else:
            out = walk(e.expr, name)
        for _, v in e.fields: out = seq(out, walk(v, name))
        return out
    if isinstance(e, S.Call):
        if getattr(e, "builtin", None) == "data": return walk(e.args[0], name, as_read=True)
        if getattr(e, "builtin", None) == "addr": return EMPTY
        if getattr(e, "builtin", None) == "set":
            a, i, v = e.args
            root = a
            while isinstance(root, S.Field): root = root.expr
            if isinstance(root, S.Var):
                return seq(seq(walk(i, name), walk(v, name)), walk(a, name))
            return seq(seq(walk(a, name), walk(i, name)), walk(v, name))
        if getattr(e, "builtin", None) == "serve": return EMPTY
        if getattr(e,"builtin",None)=="concat":
            out,borrowed=EMPTY,EMPTY
            for index,arg in enumerate(e.args):
                if index>0 and lexical_view_expression(arg):
                    reads=walk(arg,name,as_read=True)
                    out=seq(out,reads);borrowed=seq(borrowed,downgrade(reads))
                else:out=seq(out,walk(arg,name))
            return seq(out,borrowed)
        # concat and user calls consume whole-array arguments after all arguments are evaluated
        out, deferred, borrowed = EMPTY, EMPTY, EMPTY
        for argument_index,a in enumerate(e.args):
            if argument_index in getattr(e,'borrowed_args',set()):
                # The callee can read this value until the call returns. A
                # different argument must not move/mutate the same owner while
                # that borrow is live, even if it is evaluated later.
                evaluated=walk(a,name,as_read=True)
                out=seq(out,evaluated)
                # Fresh record/array constructors own their results; scalar
                # dependencies used to construct them do not remain borrowed.
                # Ordinary array-returning calls may still return a view.
                may_alias=lexical_view_expression(a) or (isinstance(a.ty,S.TArr) and
                    not isinstance(a,S.ArrC) and getattr(a,'builtin',None) not in ('set','concat'))
                if may_alias:borrowed=seq(borrowed,downgrade(evaluated))
                continue
            if isinstance(a, S.Var) and a.name == name: deferred = seq(deferred, walk(a, name))
            else: out = seq(out, walk(a, name))
        return seq(seq(out, deferred),borrowed)
    if isinstance(e, S.Let):
        # A nested binding with the same spelling is a different owner.
        return seq(walk(e.value, name), EMPTY if e.name==name else walk(e.body, name))
    if isinstance(e, S.If): return seq(walk(e.cond, name), walk(e.then, name) + walk(e.els, name))
    if isinstance(e, (S.Sum, S.ArrC)):
        return seq(seq(walk(e.lo, name), walk(e.hi, name)), EMPTY if e.var==name else downgrade(walk(e.body, name)))
    if isinstance(e, S.Check): return seq(walk(e.pred, name), walk(e.body, name))
    if isinstance(e, S.Loop):
        out = EMPTY
        for x in e.inits: out = seq(out, walk(x, name))
        if name in e.names:return out
        inner = walk(e.cond, name)
        for x in e.nexts: inner = seq(inner, walk(x, name))
        inner = seq(inner, walk(e.yld, name))
        return seq(out, downgrade(inner))
    raise TypeError(type(e))

def consume_plan(exprs: List[S.Node], name: str, projection=None) -> Set[int]:
    """Move sites with no later use or prior escaping alias on their paths.

    An unrelated branch needing a copy does not invalidate a final use elsewhere.
    Sites preceding a branch are blocked if *any* continuation still needs them.
    Prior consuming uses can create borrowed array aliases, so they also block
    subsequent moves until a more precise alias-lifetime analysis is available.
    """
    out = EMPTY
    for e in exprs: out = seq(out, paths(e, name, projection=projection))
    ids, blocked = set(), set()
    for s in out:
        ids |= s.ids
        blocked |= s.blocked
    return ids - blocked


def field_consume_plan(exprs, name, ty):
    if not isinstance(ty,S.TRec):return {}
    return {field:consume_plan(exprs,name,projection=field) for field,child in ty.fields if managed(child)}

def lexical_observer(e):
    """Expressions that cannot consume/free a lexical parent's managed storage."""
    if isinstance(e,(S.Var,S.Num,S.Flt,S.BoolLit,S.Str,S.Byte)):return True
    if isinstance(e,(S.Field,S.Len,S.Un,S.Cast)):return lexical_observer(e.expr)
    if isinstance(e,S.Bin):return lexical_observer(e.left) and lexical_observer(e.right)
    if isinstance(e,S.Index):return lexical_observer(e.arr) and lexical_observer(e.idx)
    return False

def lexical_view_expression(e):
    if isinstance(e,S.Var):return True
    if isinstance(e,S.Field):return lexical_view_expression(e.expr)
    if isinstance(e,S.Index):return lexical_view_expression(e.arr) and lexical_observer(e.idx)
    return False

# ---------------------------------------------------------------- unique-reference flags
# An owned array reference whose flag is UNIQUE (3) is the only reference to
# its whole buffer: in-place writers (set, byte_write_le, byte_copy) produce
# it, and later writers trust it instead of re-testing the reference count.
# Temporaries have one holder. A slot keeps the flag on a move only when every
# use of its variable is a move or an observer that retains nothing (len,
# indexing, byte_read_le, byte_equal); any other slot clears it to 1 (owned,
# test before writing) whenever a value moves out. NEO_UNIQUE=0 disables.
UNIQUE = 3
FLAG_OBSERVERS = ('byte_read_le', 'byte_equal')

def flag_linear(exprs, name, ty, consume, field_consume):
    """Arrays: whether moves out of the slot may keep UNIQUE. Records: the
    top-level array fields that may (nested records always clear)."""
    record = isinstance(ty, S.TRec)
    fields = {f for f, t in ty.fields if isinstance(t, S.TArr)} if record else set()
    state = {'array': True, 'lost': set()}
    def observer(node, parent):
        if isinstance(parent, S.Len): return True
        if isinstance(parent, S.Index) and parent.arr is node: return True
        return isinstance(parent, S.Call) and getattr(parent, 'builtin', None) in FLAG_OBSERVERS and \
            any(a is node for a in (parent.args if parent.builtin == 'byte_equal' else parent.args[:1]))
    def occurrence(o, parent, grand):
        if id(o) in consume: return
        if not record:
            if not observer(o, parent): state['array'] = False
            return
        if isinstance(parent, S.Field) and parent.expr is o:
            child = dict(ty.fields).get(parent.name)
            if isinstance(child, S.TArr) and not (observer(parent, grand) or id(parent) in field_consume.get(parent.name, set())):
                state['lost'].add(parent.name)
            return
        if isinstance(parent, S.With) and parent.expr is o:
            replaced = {f for f, _ in parent.fields}
            state['lost'].update(f for f in fields if f not in replaced and id(parent) not in field_consume.get(f, set()))
            return
        state['lost'].update(fields)
    def visit(node, parent, grand):
        if isinstance(node, S.Var):
            if node.name == name: occurrence(node, parent, grand)
            return
        # The same shadowing rules as paths().
        if isinstance(node, S.Let):
            visit(node.value, node, parent)
            if node.name != name: visit(node.body, node, parent)
            return
        if isinstance(node, (S.Sum, S.ArrC)):
            visit(node.lo, node, parent); visit(node.hi, node, parent)
            if node.var != name: visit(node.body, node, parent)
            return
        if isinstance(node, S.Loop):
            for x in node.inits: visit(x, node, parent)
            if name not in node.names:
                for x in [node.cond, *node.nexts, node.yld]: visit(x, node, parent)
            return
        for child in S.children(node): visit(child, node, parent)
    for e in exprs: visit(e, None, None)
    return frozenset(fields - state['lost']) if record else state['array']

# ---------------------------------------------------------------- IR builder
class Block:
    def __init__(self, label: str):
        self.label = label; self.lines: List[str] = []

class FuncBuilder:
    def __init__(self, header: str):
        self.header = header
        self.allocas: List[str] = []
        self.blocks: List[Block] = []
        self.n = 0
        self.cur = self.block("entry")
    def tmp(self) -> str:
        self.n += 1; return f"%t{self.n}"
    def label(self, base: str) -> str:
        self.n += 1; return f"{base}{self.n}"
    def block(self, label: str) -> Block:
        b = Block(label); self.blocks.append(b); self.cur = b; return b
    def emit(self, line: str): self.cur.lines.append("  " + line)
    def ins(self, text: str, ty: str) -> Val:
        t = self.tmp(); self.emit(f"{t} = {text}"); return Val(t, ty)
    def alloca(self, ty: str) -> str:
        self.n += 1; p = f"%a{self.n}"; self.allocas.append(f"  {p} = alloca {ty}"); return p
    def store(self, v: Val, ptr: str): self.emit(f"store {v}, ptr {ptr}")
    def load(self, ty: str, ptr: str) -> Val: return self.ins(f"load {ty}, ptr {ptr}", ty)
    def br(self, label: str): self.emit(f"br label %{label}")
    def cbr(self, c: Val, a: str, b: str): self.emit(f"br i1 {c.name}, label %{a}, label %{b}")
    def render(self) -> str:
        out = [self.header + " {"]
        for i, b in enumerate(self.blocks):
            out.append(f"{b.label}:")
            if i == 0: out.extend(self.allocas)
            out.extend(b.lines)
        out.append("}")
        return "\n".join(out)

class LLVMGen:
    def __init__(self, fns: List[S.Fn], fn_hashes: Dict[str, str], triple: str, assume: bool = True, vectorize: bool = True, ranges: bool = True, literal_inline: bool = True, inline_budget: int = 160, library_roots=(), switches: bool = True, unique_flags: bool = True):
        self.fns = fns; self.fn_hashes = fn_hashes; self.triple = triple
        VZ.K = VZ.sum_lanes(triple)
        self.assume = assume; self.vectorize = vectorize
        self.fn_map = {f.name: f for f in fns}
        self.vector_sums: List[dict] = []
        self.vector_arrays: List[dict] = []
        self.funcs: List[str] = []
        self.strings: Dict[str, str] = {}
        self.byte_consts: Dict[bytes, str] = {}
        self.par_regions: List[dict] = []
        self.fb: FuncBuilder = None
        self.mode = "par"; self.fn: S.Fn = None
        self.region_k = 0
        self.library_names = {f.name for f in fns if getattr(f,'source',None) and any(Path(f.source).resolve().is_relative_to(Path(root).resolve()) for root in library_roots)}
        if ranges and self.library_names:
            self.value_ranges = {**Ranges.analyze([f for f in fns if f.name in self.library_names],self.library_names),
                                 **Ranges.analyze([f for f in fns if f.name not in self.library_names])}
        else:self.value_ranges = Ranges.analyze(fns) if ranges else {}
        self.bounded_remainders = []
        self.overflow_checks = []
        self.resource_finalizers = {}
        self.region_counters = {}
        self.literal_inlined = set()
        self.small_pure_inlined = set()
        # Else-if chains over one scalar lower to an LLVM switch (NEO_SWITCH=0 disables).
        self.switches = [] if switches else None
        self.unique_flags = unique_flags
        from .return_aliases import summaries
        self.return_aliases=summaries(fns)
        self.observed_parameters={f.name:{i for i,p in enumerate(f.params)
            if isinstance(p.ty,S.TArr) and p.ty.elem==S.U8 and i not in self.return_aliases[f.name]}
            if -1 not in self.return_aliases[f.name] else set() for f in fns}
        if literal_inline:
            from .inline import node_count, is_recursive
            def visit(node):
                # LLVM inlining preserves effect order and ownership lowering.
                # Expose small policy helpers called with a constant boolean so
                # dead policy branches disappear, including allocator variants.
                if isinstance(node,S.Call) and any(isinstance(a,S.BoolLit) for a in node.args):
                    target=self.fn_map.get(node.name)
                    if target and not (target.exported or target.external or getattr(target,'precompiled',False) or getattr(target,'native_library',False)) and node_count(target.body)<=256 and not is_recursive(target,self.fn_map):
                        self.literal_inlined.add(target.name)
                if isinstance(node,S.Call) and any(isinstance(a,S.Str) for a in node.args):
                    target=self.fn_map.get(node.name)
                    if target and not (target.effect or target.exported or target.external or getattr(target,'native_library',False)) and node_count(target.body)<=160 and not is_recursive(target,self.fn_map):
                        self.literal_inlined.add(target.name)
                for child in S.children(node):visit(child)
            for function in fns:
                if not function.external and not getattr(function,'precompiled',False):visit(function.body)
            # Checked operations and owned-return cleanup inflate LLVM cost
            # estimates. Small Neo helpers should expose their facts and
            # lifetimes to the caller before LLVM applies its cost model.
            for function in fns:
                if function.name!='main' and not (function.effect or function.exported or function.external or getattr(function,'precompiled',False) or getattr(function,'native_library',False)) and node_count(function.body)<=inline_budget and not is_recursive(function,self.fn_map):
                    self.small_pure_inlined.add(function.name)
        self.inline_report(fns, inline_budget)

    def inline_report(self, fns, inline_budget):
        """`inline fn` forces inlining; calls in loops that silently missed the budget are listed."""
        from .inline import node_count, is_recursive
        self.forced_inline, self.inline_ignored, self.inline_budget_misses = set(), [], []
        def internal(f): return not (f.exported or f.external or getattr(f,'precompiled',False) or getattr(f,'native_library',False))
        for f in fns:
            if not getattr(f,'inline',False): continue
            reason = 'main' if f.name == 'main' else None if internal(f) else 'external, exported or precompiled'
            if reason is None and is_recursive(f, self.fn_map): reason = 'recursive'
            if reason: self.inline_ignored.append({'fn': getattr(f,'display_name',f.name), 'pos': list(f.pos), 'reason': reason})
            else: self.forced_inline.add(f.name)
        runtime = Path(__file__).resolve().parents[1]/'runtime'
        sizes = {}
        def visit(node, caller, loop):
            if isinstance(node, S.Call) and loop and not getattr(node, 'builtin', None):
                callee = self.fn_map.get(node.name)
                if (callee is not None and internal(callee) and not callee.effect and callee.name != 'main'
                        and not getattr(callee,'cold',False) and callee.name not in self.forced_inline
                        and callee.name not in self.small_pure_inlined and callee.name not in self.literal_inlined):
                    if callee.name not in sizes: sizes[callee.name] = node_count(callee.body)
                    if sizes[callee.name] > inline_budget and not is_recursive(callee, self.fn_map):
                        self.inline_budget_misses.append({'fn': getattr(caller,'display_name',caller.name), 'pos': list(node.pos), 'callee': getattr(callee,'display_name',callee.name),
                                                          'callee_nodes': sizes[callee.name], 'inline_budget': inline_budget, 'in': loop})
            if isinstance(node, S.Loop):
                for x in node.inits: visit(x, caller, loop)
                for x in [node.cond] + list(node.nexts): visit(x, caller, 'loop')
                visit(node.yld, caller, loop); return
            if isinstance(node, (S.Sum, S.ArrC)):
                visit(node.lo, caller, loop); visit(node.hi, caller, loop)
                visit(node.body, caller, 'sum' if isinstance(node, S.Sum) else 'arr'); return
            for child in S.children(node): visit(child, caller, loop)
        for f in fns:
            source = getattr(f, 'source', None)
            if f.external or getattr(f,'precompiled',False) or source and Path(source).resolve().is_relative_to(runtime): continue
            visit(f.body, f, None)

    # ------------------------------------------------------------ module
    def string(self, s: str) -> str:
        if s not in self.strings: self.strings[s] = '@ax_string_'+hashlib.sha256(s.encode()).hexdigest() if self.library_names else f"@.str.{len(self.strings) + 1}"
        return self.strings[s]
    def bytes_const(self, b: bytes) -> str:
        if b not in self.byte_consts: self.byte_consts[b] = '@ax_bytes_'+hashlib.sha256(b).hexdigest() if self.library_names else f"@.bytes.{len(self.byte_consts) + 1}"
        return self.byte_consts[b]

    def program(self) -> str:
        for f in self.fns:
            if f.external or getattr(f,'precompiled',False): continue
            for mode in (("seq",) if f.effect or f.exported else ("par", "seq")):
                self.function(f, mode)
        self.main_wrapper()
        self.all_function_bodies = list(self.funcs)
        # Drop unreachable internal bodies before LLVM's inliner and codegen.
        # Keep every public ABI entry, and follow symbol references including
        # address-taken callbacks/outlined regions, rather than just calls.
        bodies = {}
        roots = set()
        from pathlib import Path
        runtime = Path(__file__).resolve().parents[1]/'runtime'
        runtime_exports = {f.name for f in self.fns if f.exported and getattr(f,'source',None) and Path(f.source).resolve().is_relative_to(runtime)}
        implicit_memory = {'memcpy','memmove','memset','bzero','calloc'}
        for body in self.funcs:
            match = re.search(r'^define (.*?)@([^\s(]+)\(', body, re.M)
            if match:
                bodies[match[2]] = body
                if not match[1].startswith('internal ') and (match[2] not in runtime_exports or match[2] in implicit_memory): roots.add(match[2])
        reachable = set()
        pending = list(roots)
        while pending:
            name = pending.pop()
            if name in reachable: continue
            reachable.add(name)
            pending.extend(symbol for symbol in re.findall(r'@([^\s(),]+)', bodies[name]) if symbol in bodies and symbol not in reachable)
        self.omitted_functions = sorted(bodies.keys() - reachable)
        # Managed arrays need shared pages only for the allocating fork
        # dispatcher, whose children write a parent-visible output buffer.
        # A program whose parallel regions all run on shared-address worker
        # threads (no reachable fork-dispatched region, no prebuilt library
        # code that may contain one) gets the private heap (mode 1) preset by
        # main for every worker count: private pages fault and free more
        # cheaply than shmem and can use transparent huge pages. Programs
        # without parallel regions keep the runtime's worker-count policy.
        prebuilt = any(getattr(f,'precompiled',False) or getattr(f,'native_library',False) for f in self.fns)
        self.private_heap = 'ax_par_for_shared' in reachable and 'ax_par_for' not in reachable and not prebuilt
        omitted = {bodies[name] for name in self.omitted_functions}
        self.funcs = [body for body in self.funcs if body not in omitted]
        # A BSS-only ELF segment must start on its own page for loaders that
        # do not map the partial first page when p_filesz is zero (Rosetta).
        # Other targets retain their existing layout.
        state_alignment = 4096 if self.triple.startswith('x86_64-') and 'linux' in self.triple else 16
        head = ['source_filename = "neo"' ,f'target triple = "{self.triple}"', "",
                f"{ARR} = type {{ ptr, i64, i64, ptr }}", "",
                f"@ax_runtime_state = internal global [256 x i64] zeroinitializer, align {state_alignment}",
                f"@ax_default_heap_mode = internal constant i64 {1 if self.private_heap else 0}",
                "declare double @llvm.sqrt.f64(double)", "declare void @llvm.assume(i1)",
                f"declare <{VZ.K} x double> @llvm.sqrt.v{VZ.K}f64(<{VZ.K} x double>)",
                f"declare i1 @llvm.vector.reduce.or.v{VZ.K}i1(<{VZ.K} x i1>)",
                f"declare i64 @llvm.vector.reduce.add.v{VZ.K}i64(<{VZ.K} x i64>)",
                f"declare double @llvm.vector.reduce.fadd.v{VZ.K}f64(double, <{VZ.K} x double>)",
                "declare void @llvm.memcpy.p0.p0.i64(ptr, ptr, i64, i1)", "declare i64 @llvm.ctlz.i64(i64, i1)", "declare i64 @llvm.cttz.i64(i64, i1)", 'declare i64 @llvm.bswap.i64(i64)', ""]
        head += ['declare { i64, i1 } @llvm.s'+op+'.with.overflow.i64(i64, i64)' for op in ('add','sub','mul')]
        # Decimal length and in-place formatting for int_text fused into concat.
        # Magnitudes are unsigned, so i64 minimum formats correctly.
        # Below 10000 the digit count is three comparisons, with no division loop.
        head += ['define internal i64 @ax_dec_len(i64 %x) {',
                 'entry:', '  %neg = icmp slt i64 %x, 0', '  %flip = sub i64 0, %x', '  %m = select i1 %neg, i64 %flip, i64 %x',
                 '  %s = zext i1 %neg to i64', '  %small = icmp ult i64 %m, 10000', '  br i1 %small, label %fast, label %loop',
                 'fast:', '  %c1 = icmp ugt i64 %m, 9', '  %c2 = icmp ugt i64 %m, 99', '  %c3 = icmp ugt i64 %m, 999',
                 '  %e1 = zext i1 %c1 to i64', '  %e2 = zext i1 %c2 to i64', '  %e3 = zext i1 %c3 to i64',
                 '  %f1 = add i64 %s, 1', '  %f2 = add i64 %f1, %e1', '  %f3 = add i64 %f2, %e2', '  %f4 = add i64 %f3, %e3', '  ret i64 %f4',
                 'loop:', '  %d = phi i64 [ 1, %entry ], [ %d1, %loop ]', '  %v = phi i64 [ %m, %entry ], [ %v1, %loop ]',
                 '  %more = icmp uge i64 %v, 10', '  %v1 = udiv i64 %v, 10', '  %d1 = add i64 %d, 1', '  br i1 %more, label %loop, label %done',
                 'done:', '  %r = add i64 %d, %s', '  ret i64 %r', '}',
                 'define internal void @ax_dec_write(ptr %dst, i64 %x, i64 %len) {',
                 'entry:', '  %neg = icmp slt i64 %x, 0', '  %flip = sub i64 0, %x', '  %m = select i1 %neg, i64 %flip, i64 %x',
                 '  br i1 %neg, label %sign, label %start',
                 'sign:', '  store i8 45, ptr %dst, align 1', '  br label %start',
                 'start:', '  %end = getelementptr inbounds i8, ptr %dst, i64 %len', '  br label %loop',
                 'loop:', '  %p = phi ptr [ %end, %start ], [ %p1, %loop ]', '  %v = phi i64 [ %m, %start ], [ %q, %loop ]',
                 '  %p1 = getelementptr inbounds i8, ptr %p, i64 -1', '  %q = udiv i64 %v, 10', '  %t = mul i64 %q, 10', '  %digit = sub i64 %v, %t',
                 '  %c64 = add i64 %digit, 48', '  %c = trunc i64 %c64 to i8', '  store i8 %c, ptr %p1, align 1',
                 '  %more = icmp uge i64 %v, 10', '  br i1 %more, label %loop, label %done',
                 'done:', '  ret void', '}',
                 # Like ax_dec_write, but below 10000 the digits are computed independently
                 # and stored as one 4-byte word, with no loop. Up to 3 zero bytes land past
                 # the number, so it is only used when the next concat piece is a literal of
                 # at least 3 bytes, written afterwards over them.
                 'define internal void @ax_dec_write4(ptr %dst, i64 %x, i64 %len) {',
                 'entry:', '  %neg = icmp slt i64 %x, 0', '  %flip = sub i64 0, %x', '  %m = select i1 %neg, i64 %flip, i64 %x',
                 '  %small = icmp ult i64 %m, 10000', '  br i1 %small, label %fast, label %slow',
                 'slow:', '  call void @ax_dec_write(ptr %dst, i64 %x, i64 %len)', '  ret void',
                 # The sign is stored first; for x >= 0 the first digit overwrites it.
                 'fast:', '  store i8 45, ptr %dst, align 1', '  %s = zext i1 %neg to i64',
                 '  %q1 = udiv i64 %m, 10', '  %q2 = udiv i64 %m, 100', '  %q3 = udiv i64 %m, 1000',
                 '  %t1 = mul i64 %q1, 10', '  %t2 = mul i64 %q2, 10', '  %t3 = mul i64 %q3, 10',
                 '  %d0 = sub i64 %m, %t1', '  %d1 = sub i64 %q1, %t2', '  %d2 = sub i64 %q2, %t3',
                 '  %w2 = shl i64 %d2, 8', '  %w1 = shl i64 %d1, 16', '  %w0 = shl i64 %d0, 24',
                 '  %wa = or i64 %q3, %w2', '  %wb = or i64 %wa, %w1', '  %wc = or i64 %wb, %w0', '  %wd = add i64 %wc, 808464432',
                 '  %nd = sub i64 %len, %s', '  %nd8 = shl i64 %nd, 3', '  %shift = sub i64 32, %nd8', '  %w = lshr i64 %wd, %shift',
                 '  %p0 = getelementptr inbounds i8, ptr %dst, i64 %s', '  %p1 = getelementptr inbounds i8, ptr %p0, i64 1',
                 '  %p2 = getelementptr inbounds i8, ptr %p0, i64 2', '  %p3 = getelementptr inbounds i8, ptr %p0, i64 3',
                 '  %v1 = lshr i64 %w, 8', '  %v2 = lshr i64 %w, 16', '  %v3 = lshr i64 %w, 24',
                 '  %b0 = trunc i64 %w to i8', '  %b1 = trunc i64 %v1 to i8', '  %b2 = trunc i64 %v2 to i8', '  %b3 = trunc i64 %v3 to i8',
                 '  store i8 %b0, ptr %p0, align 1', '  store i8 %b1, ptr %p1, align 1', '  store i8 %b2, ptr %p2, align 1', '  store i8 %b3, ptr %p3, align 1',
                 '  ret void', '}', '']
        # HTML escaping fused into concat: & < > " ' become &amp; &lt; &gt; &quot; &#x27;.
        # Entity bytes are stored inline: a library module keeps only the globals
        # its own function bodies name, so these helpers must not reference any.
        entity = lambda label, text, end: [label+':'] \
            + [f'  %{label}{k} = getelementptr inbounds i8, ptr %o, i64 {k}' for k in range(1, len(text))] \
            + [f'  store i8 {ord(c)}, ptr {"%o" if k == 0 else f"%{label}{k}"}, align 1' for k, c in enumerate(text)] \
            + [f'  {end} = getelementptr inbounds i8, ptr %o, i64 {len(text)}', '  br label %next']
        head += ['define internal i64 @ax_esc_len(ptr %p, i64 %n) {',
                 'entry:', '  %empty = icmp sle i64 %n, 0', '  br i1 %empty, label %done, label %loop',
                 'loop:', '  %i = phi i64 [ 0, %entry ], [ %i1, %loop ]', '  %t = phi i64 [ %n, %entry ], [ %t1, %loop ]',
                 '  %q = getelementptr inbounds i8, ptr %p, i64 %i', '  %b = load i8, ptr %q, align 1',
                 '  %amp = icmp eq i8 %b, 38', '  %lt = icmp eq i8 %b, 60', '  %gt = icmp eq i8 %b, 62', '  %qu = icmp eq i8 %b, 34', '  %ap = icmp eq i8 %b, 39',
                 '  %ltgt = or i1 %lt, %gt', '  %five = or i1 %qu, %ap',
                 '  %e1 = select i1 %amp, i64 4, i64 0', '  %e2 = select i1 %ltgt, i64 3, i64 %e1', '  %e3 = select i1 %five, i64 5, i64 %e2',
                 '  %t1 = add i64 %t, %e3', '  %i1 = add nuw nsw i64 %i, 1', '  %more = icmp slt i64 %i1, %n', '  br i1 %more, label %loop, label %done',
                 'done:', '  %r = phi i64 [ 0, %entry ], [ %t1, %loop ]', '  ret i64 %r', '}',
                 'define internal void @ax_esc_write(ptr %dst, ptr %p, i64 %n) {',
                 'entry:', '  %empty = icmp sle i64 %n, 0', '  br i1 %empty, label %done, label %loop',
                 'loop:', '  %i = phi i64 [ 0, %entry ], [ %i1, %next ]', '  %o = phi ptr [ %dst, %entry ], [ %o1, %next ]',
                 '  %q = getelementptr inbounds i8, ptr %p, i64 %i', '  %b = load i8, ptr %q, align 1',
                 '  switch i8 %b, label %plain [ i8 38, label %amp i8 60, label %lt i8 62, label %gt i8 34, label %quot i8 39, label %apos ]',
                 'plain:', '  store i8 %b, ptr %o, align 1', '  %op = getelementptr inbounds i8, ptr %o, i64 1', '  br label %next',
                 *entity('amp', '&amp;', '%oa'), *entity('lt', '&lt;', '%ol'), *entity('gt', '&gt;', '%og'),
                 *entity('quot', '&quot;', '%oq'), *entity('apos', '&#x27;', '%ox'),
                 'next:', '  %o1 = phi ptr [ %op, %plain ], [ %oa, %amp ], [ %ol, %lt ], [ %og, %gt ], [ %oq, %quot ], [ %ox, %apos ]',
                 '  %i1 = add nuw nsw i64 %i, 1', '  %more = icmp slt i64 %i1, %n', '  br i1 %more, label %loop, label %done',
                 'done:', '  ret void', '}', '']
        head += [f'declare {{ <{VZ.K} x i64>, <{VZ.K} x i1> }} @llvm.s'+op+f'.with.overflow.v{VZ.K}i64(<{VZ.K} x i64>, <{VZ.K} x i64>)' for op in ('add','sub','mul')]
        k=VZ.ARRAY_LANES
        head += [f'declare <{k} x double> @llvm.sqrt.v{k}f64(<{k} x double>)', f'declare i1 @llvm.vector.reduce.or.v{k}i1(<{k} x i1>)']
        head += [f'declare {{ <{k} x i64>, <{k} x i1> }} @llvm.s{op}.with.overflow.v{k}i64(<{k} x i64>, <{k} x i64>)' for op in ('add','sub','mul')]
        from .kernel_workers import assembly
        head += assembly(self.triple)
        for f in self.fns:
            if f.external:
                pts = [lty(p.ty) for p in f.params] + (["..."] if f.variadic else [])
                head.append(f"declare {return_type(f.ret)} @{f.name}({', '.join(pts)})")
        for s, name in self.strings.items():
            body, n = cstr(s)
            head.append(f'{name} = private unnamed_addr constant [{n} x i8] c"{body}"')
        for b, name in self.byte_consts.items():
            body = "".join(chr(ch) if 32 <= ch < 127 and ch not in (34, 92) else f"\\{ch:02X}" for ch in b)
            head.append(f'{name} = private unnamed_addr constant [{len(b)} x i8] c"{body}"')
        head.append("")
        self.module_header = '\n'.join(head)
        return self.module_header + "\n\n".join(self.funcs) + "\n"

    def fname(self, f: S.Fn, mode: str) -> str:
        if f.external or f.exported: return f"@{f.name}"
        if f.effect: mode = "seq"
        return f"@ax_{f.name}__{mode}"

    def parameter_byref(self, f, index):
        if index>=len(f.params):return False
        p=f.params[index]
        return isinstance(p.ty,S.TRec) and managed(p.ty) and not (f.external or f.exported)

    def parameter_borrowed(self, f, index):
        p=f.params[index]
        # Match the caller's inferred borrow convention. Pure observers cannot
        # return managed aliases; leaving a dynamic owner flag in their ABI body
        # needlessly emits release paths and prevents tiny helpers from inlining.
        return p.borrowed or (isinstance(p.ty,S.TArr) and not managed(f.ret) and
                              not (f.effect or f.exported or f.external or p.owned))

    def function(self, f: S.Fn, mode: str):
        params = ", ".join(f"{'ptr' if self.parameter_byref(f,i) else lty(p.ty)} %p_{p.name}" for i,p in enumerate(f.params))
        runtime=Path(__file__).resolve().parents[1]/'runtime'
        trusted=bool(getattr(f,'source',None) and Path(f.source).resolve().is_relative_to(runtime))
        specialized=trusted and f.name in {'rt_heap_small_private','rt_heap_small_shared'}
        fresh=trusted and f.name in {'ax_alloc','ax_heap_alloc','ax_heap_small','calloc','rt_heap_small_private','rt_heap_small_shared'}
        inline=f.name in (self.literal_inlined | self.small_pure_inlined | self.forced_inline) or trusted and f.name=='ax_heap_small'
        # cold: rare paths (escapes, error recovery) stay out of their callers,
        # whose hot code then keeps its registers; LLVM treats calls as unlikely.
        cold=getattr(f,'cold',False)
        policy='noinline cold ' if cold else 'noinline ' if specialized else 'alwaysinline ' if inline else ''
        # Only the runtime's own libc-named primitives must not be recognized
        # as (recursive) builtins; everything else may use llvm.memcpy/memset
        # lowering and loop-idiom recognition.
        if trusted and f.name in RUNTIME_LIBCALLS: policy+='"no-builtins" '
        # Profiling builds keep frame pointers so samplers can attribute callers.
        if os.environ.get('NEO_FRAME_POINTERS')=='1': policy+='"frame-pointer"="all" '
        fb = FuncBuilder(f"; {f.name}  graph:{self.fn_hashes.get(f.name, '')[:16]}\n"
                         f"define {'internal ' if not f.exported else ''}{'noalias align 16 ' if fresh else ''}{return_type(f.ret)} {self.fname(f, mode)}({params}) {policy.rstrip()}")
        self.fb, self.mode, self.fn = fb, mode, f
        env: Dict[str, Slot] = {}
        for parameter_index,p in enumerate(f.params):
            ty = lty(p.ty)
            if self.parameter_byref(f,parameter_index):
                ptr=f'%p_{p.name}'
            else:
                ptr=fb.alloca(ty);v=Val(f'%p_{p.name}',ty);fb.store(v,ptr)
            s = Slot(ptr, ty, axty=p.ty)
            if isinstance(p.ty, S.TArr):
                s.own_ptr = fb.alloca("i64")
                s.borrowed = self.parameter_borrowed(f,parameter_index)
                fb.store(Val('0','i64') if s.borrowed else fb.ins(f"extractvalue {v}, 2", "i64"), s.own_ptr)
                s.consume = consume_plan([f.body], p.name)
                s.linear = flag_linear([f.body], p.name, p.ty, s.consume, {})
                s.unique_at_exit=parameter_index in self.observed_parameters[f.name]
                self.assume_array(v, p.ty)
            elif managed(p.ty):
                if p.borrowed or not f.effect and not f.exported and not p.owned:
                    s.borrowed = True
                else:
                    s.own_ptr = fb.alloca('i64'); fb.store(Val('1','i64'), s.own_ptr)
                    s.consume = consume_plan([f.body], p.name)
                    s.field_consume = field_consume_plan([f.body],p.name,p.ty)
                    s.linear = flag_linear([f.body], p.name, p.ty, s.consume, s.field_consume)
                    if self.unique_flags:
                        # The caller's private argument copy, or this frame's: clear what may be shared.
                        fb.store(self.plain_value(fb.load(ty, ptr), p.ty, s.linear), ptr)
            env[p.name] = s
        for s, carrier in f.size_binders:
            a = fb.load(ARR, env[carrier].ptr)
            n = fb.ins(f"extractvalue {a}, 1", "i64")
            ptr = fb.alloca("i64"); fb.store(n, ptr); env[s] = Slot(ptr, "i64", axty=S.I64)
        v, own = self.gen(f.body, env, par=(mode == "par"))
        if isinstance(f.ret, S.TArr):
            # Secure an escaping reference before releasing any local owners.
            v = self.owning_value(v, own, f.ret)
            own = fb.ins(f'extractvalue {v}, 2', 'i64')
        self.free_scope([env[p.name] for p in f.params if managed(p.ty)], None)
        if f.ret == S.UNIT: fb.emit("ret void")
        elif isinstance(f.ret, S.TArr):
            owned=self.nz(own)
            normalized=fb.ins(f'zext i1 {owned.name if owned is not None else "false"} to i64','i64')
            fb.emit(f"ret {self.with_own(v, normalized)}")
        else:
            fb.emit(f"ret {v}")
        self.funcs.append(fb.render())

    def main_wrapper(self):
        m = next(f for f in self.fns if f.name == "main")
        fb = FuncBuilder("define i32 @main(i32 %argc, ptr %argv)")
        self.fb, self.mode, self.fn = fb, "par", m
        argc64 = fb.ins("zext i32 %argc to i64", "i64")
        endargv = fb.ins(f"getelementptr ptr, ptr %argv, i64 {argc64.name}", "ptr")
        envp = fb.ins(f"getelementptr ptr, {endargv}, i64 1", "ptr")
        # Heap mode preset before the runtime selects its small allocator:
        # @ax_default_heap_mode is defined after reachability pruning (program()).
        mode_slot = fb.ins('getelementptr i8, ptr @ax_runtime_state, i64 184','ptr')
        fb.store(fb.load('i64','@ax_default_heap_mode'),mode_slot.name)
        fb.emit(f"call void @ax_runtime_init({envp})")
        argc_slot = fb.ins('getelementptr i8, ptr @ax_runtime_state, i64 40','ptr')
        argv_slot = fb.ins('getelementptr i8, ptr @ax_runtime_state, i64 48','ptr')
        fb.store(argc64,argc_slot.name); fb.store(Val('%argv','ptr'),argv_slot.name)
        n = len(m.params)
        ok = Val('true','i1') if n == 0 else fb.ins(f"icmp eq i32 %argc, {n + 1}", "i1")
        parse, usage = fb.label("parse"), fb.label("usage")
        fb.cbr(ok, parse, usage)
        fb.block(usage)
        argv0 = fb.load("ptr", "%argv")
        fb.emit(f"call void @ax_usage(ptr {argv0.name}, ptr {self.string(' '.join(p.name for p in m.params))})")
        fb.emit("ret i32 2")
        fb.block(parse)
        env: Dict[str, Slot] = {}
        for i, p in enumerate(m.params):
            ap = fb.ins(f"getelementptr inbounds ptr, ptr %argv, i64 {i + 1}", "ptr")
            s = fb.load("ptr", ap.name)
            v = fb.ins(f"call i64 @ax_parse_i64(ptr {s.name}, ptr {self.string(p.name)})", "i64")
            ptr = fb.alloca("i64"); fb.store(v, ptr); env[p.name] = Slot(ptr, "i64", axty=S.I64)
        for p in m.params:
            for q in p.preds:
                c, _ = self.gen(q, env, par=False)
                good, bad = fb.label("pre_ok"), fb.label("pre_fail")
                fb.cbr(c, good, bad)
                fb.block(bad)
                fb.emit(f"call void @ax_precondition_failed(ptr {self.string(S.show(q))})")
                fb.emit("ret i32 3")
                fb.block(good)
        args = ", ".join(str(fb.load("i64", env[p.name].ptr)) for p in m.params)
        if m.ret == S.UNIT:
            fb.emit(f"call void {self.fname(m,'par')}({args})")
            r = None
        else: r = fb.ins(f"call {lty(m.ret)} {self.fname(m, 'par')}({args})", lty(m.ret))
        if isinstance(m.ret, S.TArr):                      # main returned bytes: write them to stdout
            data = fb.ins(f"extractvalue {r}, 0", "ptr"); ln = fb.ins(f"extractvalue {r}, 1", "i64")
            fb.emit(f"call void @ax_print_bytes(ptr {data.name}, i64 {ln.name})")
            self.maybe_free(r, self.nz(fb.ins(f"extractvalue {r}, 2", "i64")), m.ret)
        elif m.ret != S.UNIT:
            fb.emit(f"call void @ax_print_{'f64' if m.ret == S.F64 else 'i64'}({r})")
        fb.emit("ret i32 0")
        self.funcs.append(fb.render())
        if "linux" in self.triple:
            # The kernel enters with argc/argv/envp on the initial stack. This
            # is machine entry glue; no CRT or libc startup object is linked.
            if self.triple.startswith(("aarch64", "arm64")):
                entry = 'mov x0, sp; bl ax_process_start; brk #0'
            else:
                entry = 'movq %rsp, %rdi; andq $$-16, %rsp; callq ax_process_start; ud2'
            entry = entry.replace('; ', '\\0A')
            self.funcs.append(f'define void @_start() naked noreturn {{\n  call void asm sideeffect "{entry}", "~{{memory}}"()\n  unreachable\n}}')
            self.funcs.append('''define void @ax_process_start(ptr %stack) noreturn {
  %argc64 = load i64, ptr %stack
  %argc = trunc i64 %argc64 to i32
  %argv = getelementptr i64, ptr %stack, i64 1
  %status = call i32 @main(i32 %argc, ptr %argv)
  %status64 = sext i32 %status to i64
  call void @ax_exit(i64 %status64)
  unreachable
}''')

    # ------------------------------------------------------------ helpers
    def nz(self, own: Val) -> Optional[Val]:
        """i64 ownership flag -> i1 condition; None means statically false."""
        if own.name == "0": return None
        if own.name == "1": return Val("true", "i1")
        return self.fb.ins(f"icmp ne i64 {own.name}, 0", "i1")

    def and_(self, a: Optional[Val], b: Optional[Val]) -> Optional[Val]:
        if a is None or b is None: return None
        if a.name == "true": return b
        if b.name == "true": return a
        return self.fb.ins(f"and i1 {a.name}, {b.name}", "i1")

    def capacity(self, length: Val) -> Val:
        """The runtime's capacity class for a length: max(16, next power of two), inline."""
        fb = self.fb
        m1 = fb.ins(f"sub i64 {length.name}, 1", "i64")
        lz = fb.ins(f"call i64 @llvm.ctlz.i64(i64 {m1.name}, i1 false)", "i64")
        sh = fb.ins(f"sub i64 64, {lz.name}", "i64")
        p2 = fb.ins(f"shl i64 1, {sh.name}", "i64")
        small = fb.ins(f"icmp sle i64 {length.name}, 16", "i1")
        return fb.ins(f"select i1 {small.name}, i64 16, i64 {p2.name}", "i64")

    def with_own(self, arr: Val, own: Val) -> Val:
        return self.fb.ins(f"insertvalue {arr}, i64 {own.name}, 2", ARR)

    def plain_own(self, own: Val) -> Val:
        """UNIQUE becomes an ordinary owned flag; 0, 1 and 2 are unchanged."""
        if not self.unique_flags or own.name in ('0', '1', '2'): return own
        unique = self.fb.ins(f'icmp eq i64 {own.name}, {UNIQUE}', 'i1')
        return self.fb.ins(f'select i1 {unique.name}, i64 1, i64 {own.name}', 'i64')

    def plain_value(self, value: Val, ty, keep=frozenset()) -> Val:
        """Clear UNIQUE on the managed parts of a value moved out of a slot,
        except the top-level array fields named in keep."""
        if not self.unique_flags or not managed(ty): return value
        fb = self.fb
        if isinstance(ty, S.TArr):
            return self.with_own(value, self.plain_own(fb.ins(f'extractvalue {value}, 2', 'i64')))
        for k, (field, child) in enumerate(ty.fields):
            if not managed(child) or isinstance(child, S.TArr) and field in keep: continue
            part = self.plain_value(fb.ins(f'extractvalue {value}, {k}', lty(child)), child)
            value = fb.ins(f'insertvalue {value}, {part}, {k}', lty(ty))
        return value

    def owned_unique(self, own: Val, owned: Optional[Val], value: Val) -> Optional[Val]:
        """owned && uniquely referenced, trusting a UNIQUE flag before testing the count."""
        if owned is None: return None
        if not self.unique_flags or own.name in ('0', '1', '2'): return self.and_(owned, self.array_unique(value))
        if own.name == str(UNIQUE): return Val('true', 'i1')
        fb = self.fb; result = fb.alloca('i1')
        known, test, done = fb.label('flag_unique'), fb.label('flag_test'), fb.label('flag_known')
        fb.cbr(fb.ins(f'icmp eq i64 {own.name}, {UNIQUE}', 'i1'), known, test)
        fb.block(known); fb.store(Val('true', 'i1'), result); fb.br(done)
        fb.block(test); fb.store(self.and_(owned, self.array_unique(value)), result); fb.br(done)
        fb.block(done); return fb.load('i1', result)

    def control_address(self, control):
        # Allocations are 16-byte aligned. Bit 1 tags private ownership; bit 0
        # remains reserved for the immortal sentinel. Never dereference a tag.
        fb=self.fb
        bits=fb.ins(f'ptrtoint ptr {control.name} to i64','i64')
        address=fb.ins(f'and i64 {bits.name}, -4','i64')
        return fb.ins(f'inttoptr i64 {address.name} to ptr','ptr')

    def private_control(self, control):
        fb=self.fb
        bits=fb.ins(f'ptrtoint ptr {control.name} to i64','i64')
        tag=fb.ins(f'and i64 {bits.name}, 2','i64')
        return fb.ins(f'icmp ne i64 {tag.name}, 0','i1')

    def array_unique(self, arr):
        """Owning a reference is distinct from uniquely owning its buffer."""
        fb=self.fb
        control=fb.ins(f'extractvalue {arr}, 3','ptr')
        result=fb.alloca('i1');legacy,shared,end=fb.label('unique_raw'),fb.label('unique_shared'),fb.label('unique_end')
        fb.cbr(fb.ins(f'icmp eq ptr {control.name}, null','i1'),legacy,shared)
        fb.block(legacy);fb.store(Val('true','i1'),result);fb.br(end)
        fb.block(shared)
        immortal,ordinary=fb.label('unique_immortal'),fb.label('unique_counted')
        fb.cbr(fb.ins(f'icmp eq ptr {control.name}, inttoptr (i64 1 to ptr)','i1'),immortal,ordinary)
        fb.block(immortal);fb.store(Val('false','i1'),result);fb.br(end)
        fb.block(ordinary);address=self.control_address(control)
        count_slot=fb.alloca('i64')
        local,atomic,loaded=fb.label('unique_local'),fb.label('unique_atomic'),fb.label('unique_loaded')
        fb.cbr(self.private_control(control),local,atomic)
        fb.block(local);fb.store(fb.ins(f'load i64, ptr {address.name}, align 8','i64'),count_slot);fb.br(loaded)
        fb.block(atomic);fb.store(fb.ins(f'load atomic i64, ptr {address.name} acquire, align 8','i64'),count_slot);fb.br(loaded)
        fb.block(loaded);count=fb.load('i64',count_slot)
        data=fb.ins(f'extractvalue {arr}, 0','ptr');base=fb.ins(f'getelementptr i8, ptr {address.name}, i64 16','ptr')
        unique=fb.ins(f'icmp eq i64 {count.name}, 1','i1');whole=fb.ins(f'icmp eq ptr {data.name}, {base.name}','i1')
        fb.store(self.and_(unique,whole),result);fb.br(end)
        fb.block(end);return fb.load('i1',result)

    def ensure_unique(self, slot, t):
        """Copy a shared owned buffer once, so later in-place sets need no test."""
        fb=self.fb;value=fb.load(ARR,slot.ptr);result=fb.alloca(ARR)
        keep,copy,done=fb.label('unique_keep'),fb.label('unique_copy'),fb.label('unique_ready')
        fb.cbr(self.array_unique(value),keep,copy)
        fb.block(keep);fb.store(value,result);fb.br(done)
        fb.block(copy);fresh=self.detached_array(value,t);self.maybe_free(value,Val('true','i1'),t)
        fb.store(self.with_own(fresh,Val('1','i64')),result);fb.br(done)
        fb.block(done);fb.store(fb.load(ARR,result),slot.ptr);fb.store(Val('1','i64'),slot.own_ptr)

    def refcount_change(self, control, delta):
        # Private managed allocations cannot be observed by another process.
        # Shared worker buffers keep their atomic retain/release protocol.
        fb=self.fb;result=fb.alloca('i64')
        address=self.control_address(control)
        local,shared,done=fb.label('refcount_local'),fb.label('refcount_atomic'),fb.label('refcount_done')
        fb.cbr(self.private_control(control),local,shared)
        fb.block(local)
        previous=fb.ins(f'load i64, ptr {address.name}, align 8','i64')
        updated=fb.ins(f'add i64 {previous.name}, {delta}','i64')
        if delta==-1:
            # A final private release destroys the allocation immediately; no
            # observer can use a zero count. Cached managed allocations reset
            # their count before reuse, so only surviving aliases need a store.
            write,ready=fb.label('refcount_survives'),fb.label('refcount_released')
            fb.cbr(fb.ins(f'icmp eq i64 {previous.name}, 1','i1'),ready,write)
            fb.block(write);fb.emit(f'store i64 {updated.name}, ptr {address.name}, align 8');fb.br(ready)
            fb.block(ready)
        else:fb.emit(f'store i64 {updated.name}, ptr {address.name}, align 8')
        fb.store(previous,result);fb.br(done)
        fb.block(shared)
        operation='add' if delta==1 else 'sub';order='monotonic' if delta==1 else 'acq_rel'
        previous=fb.ins(f'atomicrmw {operation} ptr {address.name}, i64 1 {order}','i64')
        fb.store(previous,result);fb.br(done);fb.block(done)
        return fb.load('i64',result)

    def maybe_free(self, arr: Val, cond: Optional[Val], t: S.TArr, drop_children=True, unique_at_exit=None):
        """Release one owned reference; destroy children only on final release."""
        fb = self.fb
        if cond is None: return
        finish=fb.label('release_end');release=fb.label('release_ref')
        fb.cbr(cond,release,finish);fb.block(release)
        control=fb.ins(f'extractvalue {arr}, 3','ptr')
        shared,destroy=fb.label('release_shared'),fb.label('release_destroy')
        fb.cbr(fb.ins(f'icmp eq ptr {control.name}, null','i1'),destroy,shared)
        fb.block(shared)
        counted=fb.label('release_counted')
        fb.cbr(fb.ins(f'icmp eq ptr {control.name}, inttoptr (i64 1 to ptr)','i1'),finish,counted)
        fb.block(counted)
        if unique_at_exit is not None:
            ordinary=fb.label('release_observed')
            fb.cbr(self.and_(unique_at_exit,self.private_control(control)),destroy,ordinary)
            fb.block(ordinary)
        previous=self.refcount_change(control,-1)
        fb.cbr(fb.ins(f'icmp eq i64 {previous.name}, 1','i1'),destroy,finish)
        fb.block(destroy)
        if drop_children and managed(t.elem):
            length = fb.ins(f'extractvalue {arr}, 1', 'i64')
            self.counted_loop(Val('0', 'i64'), length, '$drop', {},
                              lambda env, i: self.drop_value(self.load_elem(arr, i, t), t.elem))
        data = fb.ins(f"extractvalue {arr}, 0", "ptr")
        ln = fb.ins(f"extractvalue {arr}, 1", "i64")
        by = fb.ins(f"mul i64 {ln.name}, {elem_size(t)}", "i64")
        address=self.control_address(control)
        base=fb.ins(f'getelementptr i8, ptr {address.name}, i64 16','ptr')
        is_shared=fb.ins(f'icmp ne ptr {control.name}, null','i1')
        allocation=fb.ins(f'select i1 {is_shared.name}, ptr {base.name}, ptr {data.name}','ptr')
        fb.emit(f"call void @ax_free(ptr {allocation.name}, i64 {by.name})")
        fb.br(finish);fb.block(finish)

    def drop_value(self, value, ty):
        if isinstance(ty, S.TArr):
            own = self.fb.ins(f'extractvalue {value}, 2', 'i64')
            self.maybe_free(value, self.nz(own), ty)
        elif isinstance(ty, S.TRec):
            for k, (_, field) in enumerate(ty.fields):
                if managed(field):
                    child = self.fb.ins(f'extractvalue {value}, {k}', lty(field))
                    self.drop_value(child, field)

    def drop_record_slot(self, slot):
        fb = self.fb
        if not slot.own_ptr: return  # borrowed region capture
        flag = self.nz(fb.load('i64', slot.own_ptr))
        do, end = fb.label('record_drop'), fb.label('record_end')
        fb.cbr(flag, do, end); fb.block(do)
        self.drop_value(fb.load(slot.ty, slot.ptr), slot.axty)
        fb.br(end); fb.block(end)

    def detached_array(self, value, ty):
        """Copy a buffer before mutation, retaining immutable child buffers."""
        fb=self.fb
        length=fb.ins(f'extractvalue {value}, 1','i64')
        out=self.new_array(ty,length)
        if managed(ty.elem):
            self.counted_loop(Val('0','i64'),length,'$clone',{},
                lambda env,i:self.store_elem(out,i,ty,self.clone_value(self.load_elem(value,i,ty),ty.elem)))
        elif isinstance(ty.elem,S.TRec):
            # Record arrays use SoA: preserve the field layout at this length.
            self.counted_loop(Val('0','i64'),length,'$clone',{},
                lambda env,i:self.store_elem(out,i,ty,self.load_elem(value,i,ty)))
        else:
            src=fb.ins(f'extractvalue {value}, 0','ptr');dst=fb.ins(f'extractvalue {out}, 0','ptr')
            size=fb.ins(f'mul i64 {length.name}, {elem_size(ty)}','i64')
            fb.emit(f'call void @llvm.memcpy.p0.p0.i64(ptr {dst.name}, ptr {src.name}, i64 {size.name}, i1 false)')
        return out

    def clone_value(self, value, ty):
        fb = self.fb
        if isinstance(ty, S.TArr):
            control=fb.ins(f'extractvalue {value}, 3','ptr')
            result=fb.alloca(ARR)
            shared,copy,end=fb.label('retain_shared'),fb.label('retain_copy'),fb.label('retain_end')
            fb.cbr(fb.ins(f'icmp ne ptr {control.name}, null','i1'),shared,copy)
            fb.block(shared)
            immortal,counted=fb.label('retain_immortal'),fb.label('retain_counted')
            fb.cbr(fb.ins(f'icmp eq ptr {control.name}, inttoptr (i64 1 to ptr)','i1'),immortal,counted)
            fb.block(immortal);fb.store(self.with_own(value,Val('1','i64')),result);fb.br(end)
            fb.block(counted)
            self.refcount_change(control,1)
            fb.store(self.with_own(value,Val('1','i64')),result);fb.br(end)
            fb.block(copy);fb.store(self.detached_array(value,ty),result);fb.br(end)
            fb.block(end);return fb.load(ARR,result)
        if isinstance(ty, S.TRec):
            out = value
            for k, (_, field) in enumerate(ty.fields):
                if managed(field):
                    child = fb.ins(f'extractvalue {value}, {k}', lty(field))
                    out = fb.ins(f'insertvalue {out}, {self.clone_value(child, field)}, {k}', lty(ty))
            return out
        return value

    def owning_value(self, value, own, ty):
        if not isinstance(ty, S.TArr): return value
        if own.name == '1': return self.with_own(value, own)
        if own.name == '0': return self.clone_value(value, ty)
        fb = self.fb; result = fb.alloca(ARR)
        take, copy, end = fb.label('take'), fb.label('clone'), fb.label('owned')
        fb.cbr(self.nz(own), take, copy)
        fb.block(take); fb.store(self.with_own(value, own), result); fb.br(end)
        fb.block(copy); fb.store(self.clone_value(value, ty), result); fb.br(end)
        fb.block(end); return fb.load(ARR, result)

    def free_scope(self, slots: List[Slot], result_own: Optional[Val]):
        """At scope exit free every array slot that still holds its buffer. If the scope's
        result is an array that might be a borrowed alias (own == 0), keep the buffers alive."""
        fb = self.fb
        guard = Val("true", "i1") if result_own is None else self.nz(result_own)
        for s in slots:
            if isinstance(s.axty, S.TRec) and managed(s.axty):
                self.drop_record_slot(s)
                continue
            if not s.own_ptr: continue
            flag = self.nz(fb.load("i64", s.own_ptr))
            unique=fb.ins(f'icmp eq i64 {fb.load("i64",s.own_ptr).name}, 2','i1') if s.unique_at_exit else None
            self.maybe_free(fb.load(ARR, s.ptr), self.and_(flag, guard), s.axty,unique_at_exit=unique)

    def new_array(self, t: S.TArr, length: Val) -> Val:
        fb = self.fb
        neg = fb.ins(f"icmp slt i64 {length.name}, 0", "i1")
        ln = fb.ins(f"select i1 {neg.name}, i64 0, i64 {length.name}", "i64")
        maximum=(1<<62)//max(1,elem_size(t))
        large=fb.ins(f'icmp ugt i64 {ln.name}, {maximum}','i1')
        self.trap_if(large,self.fn.body,'array allocation size overflow')
        by = fb.ins(f"mul i64 {ln.name}, {elem_size(t)}", "i64")
        result = fb.alloca(ARR)
        empty, allocate, end = fb.label('array_empty'), fb.label('array_allocate'), fb.label('array_ready')
        fb.cbr(fb.ins(f'icmp eq i64 {ln.name}, 0','i1'), empty, allocate)
        fb.block(empty); fb.store(Val('zeroinitializer',ARR),result); fb.br(end)
        fb.block(allocate)
        pointer=fb.alloca('ptr');small,large,allocated=fb.label('array_small'),fb.label('array_large'),fb.label('array_allocated')
        fb.cbr(fb.ins(f'icmp ule i64 {by.name}, 16','i1'),small,large)
        fb.block(small)
        dispatch=fb.ins('getelementptr i8, ptr @ax_runtime_state, i64 192','ptr')
        allocator=fb.load('ptr',dispatch.name)
        fb.store(fb.ins(f'call noalias align 16 ptr {allocator.name}(i64 {by.name})','ptr'),pointer);fb.br(allocated)
        fb.block(large);fb.store(fb.ins(f'call noalias align 16 ptr @ax_heap_alloc(i64 {by.name})','ptr'),pointer);fb.br(allocated)
        fb.block(allocated);data=fb.load('ptr',pointer)
        control=fb.ins(f'getelementptr i8, ptr {data.name}, i64 -16','ptr')
        flags_ptr=fb.ins(f'getelementptr i8, ptr {data.name}, i64 -8','ptr')
        flags=fb.ins(f'load i64, ptr {flags_ptr.name}, align 8','i64')
        private=fb.ins(f'and i64 {flags.name}, 2','i64')
        bits=fb.ins(f'ptrtoint ptr {control.name} to i64','i64')
        tagged=fb.ins(f'or i64 {bits.name}, {private.name}','i64')
        control=fb.ins(f'inttoptr i64 {tagged.name} to ptr','ptr')
        a = fb.ins(f"insertvalue {ARR} undef, ptr {data.name}, 0", ARR)
        a = fb.ins(f"insertvalue {a}, i64 {ln.name}, 1", ARR)
        a = fb.ins(f"insertvalue {a}, i64 1, 2", ARR)
        a = fb.ins(f"insertvalue {a}, ptr {control.name}, 3", ARR)
        fb.store(a,result); fb.br(end); fb.block(end)
        a=fb.load(ARR,result); self.assume_array(a, t)
        return a

    def assume_array(self, a: Val, t: S.TArr):
        if not self.assume: return
        fb = self.fb
        data = fb.ins(f"extractvalue {a}, 0", "ptr")
        ln = fb.ins(f"extractvalue {a}, 1", "i64")
        by = fb.ins(f"mul i64 {ln.name}, {elem_size(t)}", "i64")
        nn = fb.ins(f"icmp sge i64 {ln.name}, 0", "i1")
        fb.emit(f"call void @llvm.assume(i1 {nn.name})")
        fb.emit(f'call void @llvm.assume(i1 true) ["dereferenceable"(ptr {data.name}, i64 {by.name})]')

    def assume_index(self, idx: Val, ln: Val):
        if not self.assume: return
        fb = self.fb
        a = fb.ins(f"icmp sge i64 {idx.name}, 0", "i1"); fb.emit(f"call void @llvm.assume(i1 {a.name})")
        b = fb.ins(f"icmp slt i64 {idx.name}, {ln.name}", "i1"); fb.emit(f"call void @llvm.assume(i1 {b.name})")

    # -- element addressing (scalar arrays: one plane; record arrays: struct-of-arrays in one buffer)
    def elem_ptrs(self, arr: Val, idx: Val, t: S.TArr) -> List[Tuple[int, str, Val]]:
        """[(field index or -1, llvm type, pointer)] for the element at idx."""
        fb = self.fb
        data = fb.ins(f"extractvalue {arr}, 0", "ptr")
        ln = fb.ins(f"extractvalue {arr}, 1", "i64")
        self.assume_index(idx, ln)
        if not isinstance(t.elem, S.TRec):
            return [(-1, storage_ty(t.elem), fb.ins(f"getelementptr inbounds {storage_ty(t.elem)}, ptr {data.name}, i64 {idx.name}", "ptr"))]
        out = []
        for k, fty, size, prefix in rec_layout(t.elem):
            if prefix:
                off = fb.ins(f"mul i64 {ln.name}, {prefix}", "i64")
                base = fb.ins(f"getelementptr inbounds i8, ptr {data.name}, i64 {off.name}", "ptr")
            else:
                base = data
            out.append((k, fty, fb.ins(f"getelementptr inbounds {fty}, ptr {base.name}, i64 {idx.name}", "ptr")))
        return out

    def pack_storage(self,value,t):
        fb=self.fb
        if isinstance(t,S.TArr):
            data=fb.ins(f'extractvalue {value}, 0','ptr');length=fb.ins(f'extractvalue {value}, 1','i64')
            own=fb.ins(f'extractvalue {value}, 2','i64');control=fb.ins(f'extractvalue {value}, 3','ptr')
            bits=fb.ins(f'ptrtoint ptr {control.name} to i64','i64')
            owned=fb.ins(f'icmp ne i64 {own.name}, 0','i1');flag=fb.ins(f'select i1 {owned.name}, i64 4, i64 0','i64')
            encoded=fb.ins(f'or i64 {bits.name}, {flag.name}','i64')
            out=Val('undef',storage_ty(t))
            for k,v in enumerate([data,length,encoded]):out=fb.ins(f'insertvalue {out}, {v}, {k}',storage_ty(t))
            return out
        if isinstance(t,S.TRec):
            out=Val('undef',storage_ty(t))
            for k,(_,ft) in enumerate(t.fields):
                child=fb.ins(f'extractvalue {value}, {k}',lty(ft));packed=self.pack_storage(child,ft)
                out=fb.ins(f'insertvalue {out}, {packed}, {k}',storage_ty(t))
            return out
        return value

    def unpack_storage(self,value,t):
        fb=self.fb
        if isinstance(t,S.TArr):
            data=fb.ins(f'extractvalue {value}, 0','ptr');length=fb.ins(f'extractvalue {value}, 1','i64');encoded=fb.ins(f'extractvalue {value}, 2','i64')
            flag=fb.ins(f'and i64 {encoded.name}, 4','i64');own=fb.ins(f'lshr i64 {flag.name}, 2','i64')
            bits=fb.ins(f'and i64 {encoded.name}, -5','i64');control=fb.ins(f'inttoptr i64 {bits.name} to ptr','ptr')
            out=Val('undef',ARR)
            for k,v in enumerate([data,length,own,control]):out=fb.ins(f'insertvalue {out}, {v}, {k}',ARR)
            return out
        if isinstance(t,S.TRec):
            out=Val('undef',lty(t))
            for k,(_,ft) in enumerate(t.fields):
                child=fb.ins(f'extractvalue {value}, {k}',storage_ty(ft));unpacked=self.unpack_storage(child,ft)
                out=fb.ins(f'insertvalue {out}, {unpacked}, {k}',lty(t))
            return out
        return value

    def load_elem(self, arr: Val, idx: Val, t: S.TArr, only_field: Optional[int] = None) -> Val:
        fb = self.fb
        ptrs = self.elem_ptrs(arr, idx, t)
        if not isinstance(t.elem, S.TRec): return self.unpack_storage(fb.load(ptrs[0][1], ptrs[0][2].name),t.elem)
        if only_field is not None:
            k, fty, p = next(x for x in ptrs if x[0] == only_field)
            return self.unpack_storage(fb.load(fty, p.name),t.elem.fields[k][1])
        rec = Val("undef", lty(t.elem))
        for k, fty, p in ptrs:
            v = self.unpack_storage(fb.load(fty, p.name),t.elem.fields[k][1])
            rec = fb.ins(f"insertvalue {rec}, {v}, {k}", lty(t.elem))
        return rec

    def store_elem(self, arr: Val, idx: Val, t: S.TArr, v: Val):
        fb = self.fb
        ptrs = self.elem_ptrs(arr, idx, t)
        if not isinstance(t.elem, S.TRec): fb.store(self.pack_storage(v,t.elem), ptrs[0][2].name); return
        for k, fty, p in ptrs:
            ft=t.elem.fields[k][1]
            fv = fb.ins(f"extractvalue {v}, {k}", lty(ft))
            fb.store(self.pack_storage(fv,ft), p.name)

    def add_vals(self, a: Val, b: Val, t, node=None) -> Val:
        fb = self.fb
        if t == S.F64: return fb.ins(f"fadd reassoc {a}, {b.name}", "double")   # Neo sums are order-free
        if t == S.I64:
            # A sum whose accumulation is bounded (sum_bounded) cannot overflow.
            if isinstance(node,S.Sum) and getattr(node,'arithmetic_proven',False): return fb.ins(f"add nsw {a}, {b.name}", "i64")
            return self.checked_operation('+',a,b,self.fn.body) if self.checked_integer() else fb.ins(f"add {a}, {b.name}", "i64")
        acc = a
        for k, (_, ft) in enumerate(t.fields):
            x = fb.ins(f"extractvalue {acc}, {k}", lty(ft)); y = fb.ins(f"extractvalue {b}, {k}", lty(ft))
            acc = fb.ins(f"insertvalue {acc}, {self.add_vals(x, y, ft)}, {k}", lty(t))
        return acc

    # ------------------------------------------------------------ expressions
    def bounded_remainder(self, e, a, b, lanes=1):
        """Strength-reduce small, statically bounded signed remainders."""
        bounds = self.value_ranges.get(id(e.left))
        if not bounds or not isinstance(e.right, S.Num) or e.right.value <= 0: return None
        d = e.right.value
        lo, hi = bounds
        limit = max(abs(lo), abs(hi))
        if lo == Ranges.MIN or limit >= d * 8 or d * 8 > Ranges.MAX: return None
        fb = self.fb
        negative = None
        value = a
        width = 32 if -(1 << 31) <= lo <= hi < (1 << 31) and d * 8 < (1 << 31) else 64
        scalar = f"i{width}"
        ty = scalar if lanes == 1 else f'<{lanes} x {scalar}>'
        boolty = 'i1' if lanes == 1 else f'<{lanes} x i1>'
        wide = 'i64' if lanes == 1 else f'<{lanes} x i64>'
        def constant(n): return str(n) if lanes == 1 else '<'+', '.join(f'{scalar} {n}' for _ in range(lanes))+'>'
        if width == 32: value = fb.ins(f"trunc {a} to {ty}", ty)
        if lo < 0:
            negative = fb.ins(f"icmp slt {value}, {constant(0)}", boolty)
            negated = fb.ins(f"sub {ty} {constant(0)}, {value.name}", ty)
            value = fb.ins(f"select {negative}, {negated}, {value}", ty)
        for factor in (4, 2, 1):
            threshold = d * factor
            if limit < threshold: continue
            ge = fb.ins(f"icmp uge {value}, {constant(threshold)}", boolty)
            reduced = fb.ins(f"sub {value}, {constant(threshold)}", ty)
            value = fb.ins(f"select {ge}, {reduced}, {value}", ty)
        if negative is not None:
            negated = fb.ins(f"sub {ty} {constant(0)}, {value.name}", ty)
            value = fb.ins(f"select {negative}, {negated}, {value}", ty)
        if width == 32: value = fb.ins(f"sext {value} to {wide}", wide)
        self.bounded_remainders.append({'fn': self.fn.name, 'pos': list(e.pos), 'divisor': d, 'bounds': list(bounds), 'width': width, 'lanes':lanes})
        return value

    def checked_integer(self):
        from pathlib import Path
        source=getattr(self.fn,'source',None)
        return not source or not Path(source).resolve().is_relative_to(Path(__file__).resolve().parents[1]/'runtime')

    def trap_if(self, condition, node, message):
        fb=self.fb;bad,good=fb.label('arithmetic_bad'),fb.label('arithmetic_ok')
        fb.cbr(condition,bad,good);fb.block(bad)
        fb.emit(f'call void @ax_trap(ptr {self.string(message+" at "+self.fn.name+":"+str(node.pos[0]))})')
        fb.emit('unreachable');fb.block(good)
        self.overflow_checks.append({'fn':self.fn.name,'pos':list(node.pos),'kind':message})

    def interval_proven(self, node):
        """Retry the checker's overflow goal with interval bounds of its operand nodes."""
        context=getattr(node,'arithmetic_context',None)
        if context is None:return False
        cached=getattr(node,'interval_proof',None)
        if cached is not None:return cached
        facts,goal,operands=context;extra=[]
        for operand,lin in operands:
            bounds=self.value_ranges.get(id(operand))
            if not bounds or bounds==Ranges.TOP:continue
            if bounds[0]>Ranges.MIN:extra.append(cmp('>=',lin,Lin.num(bounds[0])))
            if bounds[1]<Ranges.MAX:extra.append(cmp('<=',lin,Lin.num(bounds[1])))
        node.interval_proof=bool(extra) and entails(and_(facts,*extra),goal,diagnostics=False)[0]=='proven'
        return node.interval_proof

    def checked_operation(self, op, a, b, node, proven=False):
        operation={'+':'add','-':'sub','*':'mul'}[op]
        # Proven operations cannot wrap; nsw lets LLVM reason about the result,
        # for example that i <= n - 8 leaves eight readable bytes at i.
        if proven or self.interval_proven(node):return self.fb.ins(f'{operation} nsw {a}, {b.name}','i64')
        def bounds(value, expression):
            try:v=int(value.name);return v,v
            except ValueError:return self.value_ranges.get(id(expression),Ranges.TOP)
        left=bounds(a,getattr(node,'left',None))
        right=bounds(b,getattr(node,'right',getattr(node,'expr',None)))
        if left is None:left=Ranges.TOP
        if right is None:right=Ranges.TOP
        if op=='+':lo,hi=left[0]+right[0],left[1]+right[1]
        elif op=='-':lo,hi=left[0]-right[1],left[1]-right[0]
        else:
            possibilities=[x*y for x in left for y in right];lo,hi=min(possibilities),max(possibilities)
        if Ranges.MIN<=lo<=hi<=Ranges.MAX:return self.fb.ins(f'{operation} nsw {a}, {b.name}','i64')
        result=self.fb.ins(f'call {{ i64, i1 }} @llvm.s{operation}.with.overflow.i64({a}, {b})','{ i64, i1 }')
        value=self.fb.ins(f'extractvalue {result}, 0','i64')
        overflow=self.fb.ins(f'extractvalue {result}, 1','i1')
        self.trap_if(overflow,node,'integer overflow')
        return value

    def gen(self, e: S.Node, env: Dict[str, Slot], par: bool) -> Tuple[Val, Optional[Val]]:
        fb = self.fb
        if isinstance(e, S.Num): return Val(str(e.value), "i64"), None
        if isinstance(e, S.Flt): return Val(fconst(e.value), "double"), None
        if isinstance(e, S.BoolLit): return Val("true" if e.value else "false", "i1"), None
        if isinstance(e, S.Byte): return Val(str(e.value), "i8"), None
        if isinstance(e, S.Str):
            g = self.bytes_const(e.value)
            a = fb.ins(f"insertvalue {ARR} undef, ptr {g}, 0", ARR)
            a = fb.ins(f"insertvalue {a}, i64 {len(e.value)}, 1", ARR)
            a = fb.ins(f"insertvalue {a}, i64 1, 2", ARR)           # owning immortal reference
            a = fb.ins(f"insertvalue {a}, ptr inttoptr (i64 1 to ptr), 3", ARR)
            return a, Val("1", "i64")
        if isinstance(e, S.Var):
            s = env[e.name]
            v = fb.load(s.ty, s.ptr)
            if getattr(e, 'resource_move', False) and s.resource_live:
                fb.store(Val('false', 'i1'), s.resource_live)
            if s.ty != ARR:
                if managed(s.axty) and s.own_ptr and id(e) in s.consume:
                    fb.store(Val('0','i64'), s.own_ptr); return v, None
                return self.clone_value(v, s.axty) if managed(s.axty) else v, None
            if s.own_ptr and id(e) in s.consume:                    # move: take the flag, leave 0 behind
                own = fb.load("i64", s.own_ptr); fb.store(Val("0", "i64"), s.own_ptr)
                return v, own
            return v, Val("0", "i64")
        if isinstance(e, S.Bin):
            if e.op in ("&&", "||"):
                a, _ = self.gen(e.left, env, par)
                res = fb.alloca("i1"); fb.store(a, res)
                rhs, join = fb.label("rhs"), fb.label("join")
                if e.op == "&&": fb.cbr(a, rhs, join)
                else: fb.cbr(a, join, rhs)
                fb.block(rhs)
                b, _ = self.gen(e.right, env, par); fb.store(b, res); fb.br(join)
                fb.block(join)
                return fb.load("i1", res), None
            a, _ = self.gen(e.left, env, par)
            b, _ = self.gen(e.right, env, par)
            fl = a.ty == "double"
            if e.op == "%" and a.ty == "i64":
                reduced = self.bounded_remainder(e, a, b)
                if reduced is not None: return reduced, None
            if e.op in ("+", "-", "*", "/", "%"):
                if not fl and a.ty=='i64' and self.checked_integer():
                    if e.op in ('+','-','*'):
                        return self.checked_operation(e.op,a,b,e,getattr(e,'arithmetic_proven',False)),None
                    overflow = fb.ins(f'icmp eq i64 {a.name}, -9223372036854775808','i1')
                    negative = fb.ins(f'icmp eq i64 {b.name}, -1','i1')
                    bad = fb.ins(f'and i1 {overflow.name}, {negative.name}','i1')
                    self.trap_if(bad,e,'integer division overflow')
                op = {"+": "fadd" if fl else "add", "-": "fsub" if fl else "sub", "*": "fmul" if fl else "mul",
                      "/": "fdiv" if fl else "sdiv", "%": "srem"}[e.op]
                return fb.ins(f"{op} {a}, {b.name}", a.ty), None
            if fl:
                op = {"<": "olt", "<=": "ole", ">": "ogt", ">=": "oge", "==": "oeq", "!=": "une"}[e.op]
                return fb.ins(f"fcmp {op} {a}, {b.name}", "i1"), None
            if a.ty in ("i8", "i16"):
                op = {"<": "ult", "<=": "ule", ">": "ugt", ">=": "uge", "==": "eq", "!=": "ne"}[e.op]
                return fb.ins(f"icmp {op} {a}, {b.name}", "i1"), None
            op = {"<": "slt", "<=": "sle", ">": "sgt", ">=": "sge", "==": "eq", "!=": "ne"}[e.op]
            return fb.ins(f"icmp {op} {a}, {b.name}", "i1"), None
        if isinstance(e, S.Un):
            if e.op=='-' and isinstance(e.expr,S.Num) and e.expr.value==1<<63:return Val('-9223372036854775808','i64'),None
            a, _ = self.gen(e.expr, env, par)
            if e.op == "!": return fb.ins(f"xor i1 {a.name}, true", "i1"), None
            if a.ty == "double": return fb.ins(f"fneg {a}", "double"), None
            if self.checked_integer():return self.checked_operation('-',Val('0','i64'),a,e,getattr(e,'arithmetic_proven',False)),None
            return fb.ins(f"sub i64 0, {a.name}", "i64"), None
        if isinstance(e, S.Field) and isinstance(e.expr, S.Index):
            a=self.record_argument_view(e.expr.arr,env)
            if a is None:a,own=self.gen(e.expr.arr,env,par)
            else:own=Val('0','i64')
            if not lexical_observer(e.expr.idx):
                # The index may consume the lexical owner. Keep the parent
                # alive until its element/field has been loaded and retained.
                a=self.owning_value(a,own,e.expr.arr.ty)
                own=fb.ins(f'extractvalue {a}, 2','i64')
            i, _ = self.gen(e.expr.idx, env, par)
            v = self.load_elem(a, i, e.expr.arr.ty, only_field=e.expr.arr.ty.elem.index(e.name))
            if managed(e.ty):v=self.clone_value(v,e.ty)
            self.maybe_free(a, self.nz(own), e.expr.arr.ty)
            return v, fb.ins(f'extractvalue {v}, 2','i64') if isinstance(e.ty,S.TArr) else None
        if isinstance(e, S.Index):
            a=self.record_argument_view(e.arr,env)
            if a is None:a,own=self.gen(e.arr,env,par)
            else:own=Val('0','i64')
            if not lexical_observer(e.idx):
                a=self.owning_value(a,own,e.arr.ty)
                own=fb.ins(f'extractvalue {a}, 2','i64')
            i, _ = self.gen(e.idx, env, par)
            v = self.load_elem(a, i, e.arr.ty)
            if managed(e.ty): v = self.clone_value(v, e.ty)
            self.maybe_free(a, self.nz(own), e.arr.ty)
            return v, fb.ins(f'extractvalue {v}, 2', 'i64') if isinstance(e.ty, S.TArr) else None
        if isinstance(e, S.Len):
            borrowed=self.record_argument_view(e.expr,env,True)
            if borrowed is not None:return fb.ins(f'extractvalue {borrowed}, 1','i64'),None
            a, own = self.gen(e.expr, env, par)
            n = fb.ins(f"extractvalue {a}, 1", "i64")
            self.maybe_free(a, self.nz(own), e.expr.ty)
            return n, None
        if isinstance(e, S.Cast):
            a, _ = self.gen(e.expr, env, par)
            if e.to == S.I32: return fb.ins(f"trunc {a} to i32", "i32"), None
            if a.ty == "i32": return fb.ins(f"sext {a} to i64", "i64"), None
            if e.to == S.F64: return fb.ins(f"sitofp {a} to double", "double"), None
            if e.to == S.U8: return fb.ins(f"trunc {a} to i8", "i8"), None
            if e.to == S.U16: return fb.ins(f"trunc {a} to i16", "i16"), None
            if a.ty in ("i8", "i16"): return fb.ins(f"zext {a} to i64", "i64"), None
            low=fb.ins(f'fcmp oge double {a.name}, {fconst(float(-(1<<63)))}','i1')
            high=fb.ins(f'fcmp olt double {a.name}, {fconst(float(1<<63))}','i1')
            valid=fb.ins(f'and i1 {low.name}, {high.name}','i1')
            bad=fb.ins(f'xor i1 {valid.name}, true','i1');self.trap_if(bad,e,'float to integer out of range')
            return fb.ins(f"fptosi {a} to i64", "i64"), None
        if isinstance(e, S.RecLit):
            rt = e.ty; given = dict(e.fields)
            rec = Val("undef", lty(rt))
            for k, (fname, ft) in enumerate(rt.fields):
                v, own = self.gen(given[fname], env, par)
                if isinstance(ft, S.TArr) and not isinstance(given[fname], S.Str): v = self.owning_value(v, own, ft)
                rec = fb.ins(f"insertvalue {rec}, {v}, {k}", lty(rt))
            return rec, None
        if isinstance(e, S.Field):
            if not managed(e.ty) or not isinstance(e.expr,S.Var):
                view = self.record_argument_view(e.expr, env)
                if view is not None:
                    value = fb.ins(f'extractvalue {view}, {e.expr.ty.index(e.name)}', lty(e.ty))
                    if managed(e.ty): value = self.clone_value(value,e.ty)
                    return value,fb.ins(f'extractvalue {value}, 2','i64') if isinstance(e.ty,S.TArr) else None
            borrowed = isinstance(e.expr, S.Var)
            r = fb.load(env[e.expr.name].ty, env[e.expr.name].ptr) if borrowed else self.gen(e.expr, env, par)[0]
            if borrowed:
                slot = env[e.expr.name]
                if slot.own_ptr and id(e.expr) in slot.consume:
                    fb.store(Val('0','i64'), slot.own_ptr); borrowed = False
            k = e.expr.ty.index(e.name)
            value = fb.ins(f"extractvalue {r}, {k}", lty(e.ty))
            if borrowed and slot.own_ptr and id(e) in slot.field_consume.get(e.name,set()):
                # Transfer just this field; scope cleanup still owns the other fields.
                rest = fb.ins(f'insertvalue {r}, {lty(e.ty)} {zero(e.ty)}, {k}',lty(e.expr.ty))
                fb.store(rest,slot.ptr)
                return value, fb.ins(f'extractvalue {value}, 2','i64') if isinstance(e.ty,S.TArr) else None
            if borrowed and isinstance(e.ty, S.TArr) and slot.borrowed:
                return self.with_own(value, Val('0','i64')), Val('0','i64')
            if borrowed and managed(e.ty): value = self.clone_value(value, e.ty)
            if not borrowed:
                for j, (_, field) in enumerate(e.expr.ty.fields):
                    if j != k and managed(field):
                        self.drop_value(fb.ins(f'extractvalue {r}, {j}',lty(field)),field)
            return value, fb.ins(f'extractvalue {value}, 2', 'i64') if isinstance(e.ty, S.TArr) else None
        if isinstance(e, S.With):
            if isinstance(e.expr, S.Var):
                # A record update only needs the unchanged fields. Cloning the
                # whole base first would copy and immediately discard each
                # replaced buffer, including entire database states.
                slot = env[e.expr.name]
                rt = e.expr.ty
                source = fb.load(slot.ty, slot.ptr)
                replaced = {field for field, _ in e.fields}
                r = Val('undef', lty(rt))
                for k, (field, child) in enumerate(rt.fields):
                    if field in replaced: continue
                    value = fb.ins(f'extractvalue {source}, {k}', lty(child))
                    if managed(child):
                        if slot.own_ptr and id(e) in slot.field_consume.get(field,set()):
                            current = fb.load(slot.ty, slot.ptr)
                            rest = fb.ins(f'insertvalue {current}, {lty(child)} {zero(child)}, {k}',slot.ty)
                            fb.store(rest,slot.ptr)
                        else:
                            value = self.clone_value(value, child)
                    r = fb.ins(f'insertvalue {r}, {value}, {k}',lty(rt))
                for field, expression in e.fields:
                    value, own = self.gen(expression, env, par)
                    if isinstance(expression.ty,S.TArr):value=self.owning_value(value,own,expression.ty)
                    r = fb.ins(f'insertvalue {r}, {value}, {rt.index(field)}',lty(rt))
                return r,None
            r, _ = self.gen(e.expr, env, par)
            rt = e.expr.ty
            for fname, fe in e.fields:
                v, own = self.gen(fe, env, par)
                if managed(fe.ty):
                    old = fb.ins(f'extractvalue {r}, {rt.index(fname)}', lty(fe.ty))
                    self.drop_value(old, fe.ty)
                    if isinstance(fe.ty, S.TArr): v = self.owning_value(v, own, fe.ty)
                r = fb.ins(f"insertvalue {r}, {v}, {rt.index(fname)}", lty(rt))
            return r, None
        if isinstance(e, S.Call):
            return self.call(e, env, par)
        if isinstance(e, S.Let):
            v, own = self.gen(e.value, env, par)
            consume = consume_plan([e.body], e.name) if managed(e.value.ty) else set()
            fields = field_consume_plan([e.body], e.name, e.value.ty) if managed(e.value.ty) and v.ty != ARR else {}
            linear = flag_linear([e.body], e.name, e.value.ty, consume, fields) if self.unique_flags and managed(e.value.ty) else \
                (frozenset() if isinstance(e.value.ty, S.TRec) else False)
            if v.ty == ARR and linear is not True: own = self.plain_own(own)
            elif v.ty != ARR and managed(e.value.ty): v = self.plain_value(v, e.value.ty, linear)
            ptr = fb.alloca(v.ty); fb.store(v, ptr)
            slot = Slot(ptr, v.ty, axty=e.value.ty)
            if getattr(e, 'resource_scope', False):
                slot.resource_live = fb.alloca("i1"); fb.store(Val("true", "i1"), slot.resource_live)
            if v.ty == ARR:
                slot.own_ptr = fb.alloca("i64"); fb.store(own, slot.own_ptr)
                slot.consume = consume
                slot.linear = linear
                self.assume_array(v, e.value.ty)
            elif managed(e.value.ty):
                slot.own_ptr = fb.alloca('i64'); fb.store(Val('1','i64'),slot.own_ptr)
                slot.consume = consume
                slot.field_consume = fields
                slot.linear = linear
            env2 = dict(env); env2[e.name] = slot
            bv, bown = self.gen(e.body, env2, par)
            if managed(e.value.ty):
                if isinstance(e.body.ty,S.TArr):
                    bv=self.owning_value(bv,bown,e.body.ty)
                    bown=fb.ins(f'extractvalue {bv}, 2','i64')
                self.free_scope([slot],None)
            return bv, bown
        if isinstance(e, S.If):
            chain = self.switch_chain(e) if self.switches is not None else None
            if chain is not None: return self.switch(e, chain, env, par)
            c, _ = self.gen(e.cond, env, par)
            ty = lty(e.ty); res = fb.alloca(ty)
            ores = fb.alloca("i64") if ty == ARR else None
            then, els, join = fb.label("then"), fb.label("else"), fb.label("join")
            fb.cbr(c, then, els)
            for label, branch in ((then, e.then), (els, e.els)):
                fb.block(label)
                v, own = self.gen(branch, env, par)
                fb.store(v, res)
                if ores: fb.store(own, ores)
                fb.br(join)
            fb.block(join)
            return fb.load(ty, res), (fb.load("i64", ores) if ores else None)
        if isinstance(e, S.Check):
            if getattr(e, 'statically_proven', False): return self.gen(e.body, env, par)
            p, _ = self.gen(e.pred, env, par)
            ok, bad = fb.label("chk_ok"), fb.label("chk_fail")
            fb.cbr(p, ok, bad); fb.block(bad)
            fb.emit(f"call void @ax_trap(ptr {self.string(f'check failed: {S.show(e.pred)} at {e.pos[0]}:{e.pos[1]}')})")
            fb.emit("unreachable"); fb.block(ok)
            return self.gen(e.body, env, par)
        if isinstance(e, (S.Sum, S.ArrC)):
            return self.comprehension(e, env, par)
        if isinstance(e, S.Loop):
            return self.loop(e, env, par)
        raise TypeError(type(e))

    # ------------------------------------------------------------ dispatch
    def case_values(self, cond, scrutinee):
        """(x, [constants]) when cond is x == k1 || x == k2 ... over one pure scalar x."""
        if isinstance(cond, S.Bin) and cond.op == '||':
            left = self.case_values(cond.left, scrutinee)
            if left is None: return None
            right = self.case_values(cond.right, left[0])
            return None if right is None else (left[0], left[1] + right[1])
        if not (isinstance(cond, S.Bin) and cond.op == '=='): return None
        for x, k in ((cond.left, cond.right), (cond.right, cond.left)):
            value = case_constant(k)
            if value is None or x.ty not in (S.I64, S.U8, S.U16) or not pure_scrutinee(x): continue
            if scrutinee is not None and S.show(x) != S.show(scrutinee): continue
            return x, [value]
        return None

    def switch_chain(self, e):
        """An else-if chain testing one variable or field against constants.

        No binder sits between the tests of such a chain, so equal text is the
        same binding; the scrutinee is a trap-free read, evaluated once."""
        arms, seen, node, scrutinee = [], set(), e, None
        while isinstance(node, S.If):
            found = self.case_values(node.cond, scrutinee)
            if found is None: break
            scrutinee, values = found
            fresh = [v for v in dict.fromkeys(values) if v not in seen]
            seen.update(fresh)
            arms.append((fresh, node.then))       # an arm whose values all came earlier is dead
            node = node.els
        if len(seen) < 4: return None
        return scrutinee, arms, node

    def switch(self, e, chain, env, par):
        fb = self.fb
        scrutinee, arms, default = chain
        x, _ = self.gen(scrutinee, env, par)
        bits = {'i64': 64, 'i16': 16, 'i8': 8}[x.ty]
        def literal(v):
            v &= (1 << bits) - 1
            return v - (1 << bits) if v >> (bits - 1) else v
        ty = lty(e.ty); res = fb.alloca(ty)
        ores = fb.alloca("i64") if ty == ARR else None
        labels = [fb.label("case") if values else None for values, _ in arms]
        other, join = fb.label("case_default"), fb.label("join")
        cases = " ".join(f"{x.ty} {literal(v)}, label %{label}" for (values, _), label in zip(arms, labels) for v in values)
        fb.emit(f"switch {x}, label %{other} [ {cases} ]")
        self.switches.append({'fn': self.fn.name, 'pos': list(e.pos), 'cases': sum(len(v) for v, _ in arms), 'arms': len(arms) + 1})
        for label, (_, branch) in [(l, a) for l, a in zip(labels, arms) if l is not None] + [(other, (None, default))]:
            fb.block(label)
            v, own = self.gen(branch, env, par)
            fb.store(v, res)
            if ores: fb.store(own, ores)
            fb.br(join)
        fb.block(join)
        return fb.load(ty, res), (fb.load("i64", ores) if ores else None)

    # ------------------------------------------------------------ calls and builtins
    def record_argument_pointer(self, e, env):
        """A borrowed record's lexical address; SoA elements use a temporary."""
        if isinstance(e,S.Var) and isinstance(e.ty,S.TRec):return env[e.name].ptr
        if isinstance(e,S.Field) and isinstance(e.ty,S.TRec):
            parent=self.record_argument_pointer(e.expr,env)
            if parent is not None:
                return self.fb.ins(f'getelementptr {lty(e.expr.ty)}, ptr {parent}, i32 0, i32 {e.expr.ty.index(e.name)}','ptr').name
        return None

    def record_argument_view(self, e, env, allow_index=False):
        """Borrow only storage rooted in a live lexical binding, never a temporary."""
        if isinstance(e, S.Var):
            slot = env[e.name]
            return self.fb.load(slot.ty, slot.ptr)
        if isinstance(e, S.Field):
            parent = self.record_argument_view(e.expr, env, allow_index)
            if parent is not None:
                return self.fb.ins(f'extractvalue {parent}, {e.expr.ty.index(e.name)}', lty(e.ty))
        if allow_index and isinstance(e,S.Index) and lexical_observer(e.idx):
            parent=self.record_argument_view(e.arr,env,True)
            if parent is not None:
                index,_=self.gen(e.idx,env,self.mode=='par')
                return self.load_elem(parent,index,e.arr.ty)
        return None

    def call(self, e: S.Call, env, par, resource_guard=True):
        fb = self.fb
        if resource_guard and getattr(e, 'resource_cleanup', False):
            slot = env[e.args[0].name]
            if slot.resource_live:
                live = fb.load('i1', slot.resource_live)
                cleanup, join = fb.label('resource_drop'), fb.label('resource_join')
                fb.cbr(live, cleanup, join); fb.block(cleanup)
                fb.store(Val('false', 'i1'), slot.resource_live)
                self.call(e, env, par, resource_guard=False)
                fb.br(join); fb.block(join)
                return Val('0', 'i8'), None
        b = getattr(e, "builtin", None)
        if b=='ref_null':return Val('zeroinitializer',lty(e.ty)),None
        if b=='adopt':
            resource=e.resource_target;value,_=self.gen(e.args[0],env,par);arena,_=self.gen(e.args[1],env,par)
            token=fb.ins(f'extractvalue {arena}, 0','i64')
            finalizer=self.resource_finalizers.get(resource.name)
            if finalizer is None:
                finalizer='@ax_resource_finalizer_'+(hashlib.sha256(resource.name.encode()).hexdigest() if self.library_names else str(len(self.resource_finalizers)));self.resource_finalizers[resource.name]=finalizer
                saved=self.fb;dropper=FuncBuilder(f'define internal void {finalizer}(ptr %box)');self.fb=dropper
                payload=Val('%box','ptr') if self.parameter_byref(e.resource_drop,0) else dropper.load(lty(resource),'%box')
                dropper.emit(f'call void {self.fname(e.resource_drop,"seq")}({payload})');dropper.emit('ret void');self.funcs.append(dropper.render());self.fb=saved
            # The arena box is read again by borrows and the finalizer: no UNIQUE flags inside.
            value=self.plain_value(value,resource)
            box=fb.ins(f'call ptr @ax_alloc(i64 {scalar_size(resource)})','ptr');fb.store(value,box.name)
            slot=fb.ins(f'call i64 @ax_rt_arena_register__seq({token}, {box}, ptr {finalizer})','i64')
            failed=fb.ins(f'icmp slt i64 {slot.name}, 0','i1')
            self.trap_if(failed,e,'resource arena is closed or full')
            ref=fb.ins(f'insertvalue {lty(e.ty)} zeroinitializer, {token}, 0',lty(e.ty));return fb.ins(f'insertvalue {ref}, {slot}, 1',lty(e.ty)),None
        if b in ('borrow_ref','ref_live','ref_release'):
            reference,_=self.gen(e.args[0],env,par);token=fb.ins(f'extractvalue {reference}, 0','i64');slot=fb.ins(f'extractvalue {reference}, 1','i64')
            if b=='ref_release':fb.emit(f'call void @ax_rt_arena_release__seq({token}, {slot})');return Val('0','i8'),None
            pointer=fb.ins(f'call ptr @ax_rt_arena_lookup__seq({token}, {slot})','ptr');live=fb.ins(f'icmp ne ptr {pointer.name}, null','i1')
            if b=='ref_live':return live,None
            self.trap_if(fb.ins(f'xor i1 {live.name}, true','i1'),e,'borrow of a closed resource reference')
            value=fb.load(lty(e.ty),pointer.name);return self.clone_value(value,e.ty) if managed(e.ty) else value,None
        if b=='function_null':return Val('null','ptr'),None
        if b=='function':return Val(self.fname(e.target,'seq'),'ptr'),None
        if b=='allocation_stats_enabled':return Val('true' if os.environ.get('NEO_ALLOC_STATS')=='1' else 'false','i1'),None
        if b=='byte_equal':
            # Retain before evaluating an argument that may consume a borrowed
            # source; plain lexical observers cannot mutate either operand.
            safe=all(lexical_view_expression(arg) and lexical_observer(arg) for arg in e.args)
            operands=[];released=[]
            for arg in e.args:
                view=self.record_argument_view(arg,env,True) if safe else None
                value,own=(view,Val('0','i64')) if view is not None else self.gen(arg,env,par)
                if not safe:
                    value=self.owning_value(value,own,arg.ty);released.append((value,arg.ty))
                operands.append(value)
            left,right=operands
            answer=fb.alloca('i1');index=fb.alloca('i64');same=fb.alloca('i1')
            ln=fb.ins(f'extractvalue {left}, 1','i64');rn=fb.ins(f'extractvalue {right}, 1','i64')
            lp=fb.ins(f'extractvalue {left}, 0','ptr');rp=fb.ins(f'extractvalue {right}, 0','ptr')
            mismatch,checkptr,identical,words,wordbody,tail,tailbody,finish,done=[fb.label(n) for n in ('equal_length','equal_pointer','equal_identity','equal_words','equal_word','equal_tail','equal_byte','equal_finish','equal_done')]
            fb.cbr(fb.ins(f'icmp eq i64 {ln.name}, {rn.name}','i1'),checkptr,mismatch)
            fb.block(mismatch);fb.store(Val('false','i1'),answer);fb.br(done)
            fb.block(checkptr);fb.cbr(fb.ins(f'icmp eq ptr {lp.name}, {rp.name}','i1'),identical,words)
            fb.block(identical);fb.store(Val('true','i1'),answer);fb.br(done)
            fb.block(words);fb.store(Val('0','i64'),index);fb.store(Val('true','i1'),same)
            header=fb.label('equal_word_header');fb.br(header);fb.block(header)
            i=fb.load('i64',index);ok=fb.load('i1',same);limit=fb.ins(f'sub i64 {ln.name}, 8','i64')
            fb.cbr(self.and_(ok,fb.ins(f'icmp sle i64 {i.name}, {limit.name}','i1')),wordbody,tail)
            fb.block(wordbody)
            pa=fb.ins(f'getelementptr i8, ptr {lp.name}, i64 {i.name}','ptr');pb=fb.ins(f'getelementptr i8, ptr {rp.name}, i64 {i.name}','ptr')
            av=fb.ins(f'load i64, ptr {pa.name}, align 1','i64');bv=fb.ins(f'load i64, ptr {pb.name}, align 1','i64')
            fb.store(fb.ins(f'icmp eq i64 {av.name}, {bv.name}','i1'),same);fb.store(fb.ins(f'add i64 {i.name}, 8','i64'),index);fb.br(header)
            fb.block(tail);i=fb.load('i64',index);ok=fb.load('i1',same)
            fb.cbr(self.and_(ok,fb.ins(f'icmp slt i64 {i.name}, {ln.name}','i1')),tailbody,finish)
            fb.block(tailbody)
            pa=fb.ins(f'getelementptr i8, ptr {lp.name}, i64 {i.name}','ptr');pb=fb.ins(f'getelementptr i8, ptr {rp.name}, i64 {i.name}','ptr')
            av=fb.ins(f'load i8, ptr {pa.name}, align 1','i8');bv=fb.ins(f'load i8, ptr {pb.name}, align 1','i8')
            fb.store(fb.ins(f'icmp eq i8 {av.name}, {bv.name}','i1'),same);fb.store(fb.ins(f'add i64 {i.name}, 1','i64'),index);fb.br(tail)
            fb.block(finish);fb.store(fb.load('i1',same),answer);fb.br(done);fb.block(done)
            result=fb.load('i1',answer)
            for value,ty in released:self.drop_value(value,ty)
            return result,None
        if b in ('bit_and','bit_or','bit_xor'):
            a,c=[self.gen(x,env,par)[0] for x in e.args]
            return fb.ins(f'{b[4:]} {a}, {c.name}','i64'),None
        if b == 'count_trailing_zeros':
            a=self.gen(e.args[0],env,par)[0]
            return fb.ins(f'call i64 @llvm.cttz.i64({a}, i1 false)','i64'),None
        if b == 'byte_swap64':
            a=self.gen(e.args[0],env,par)[0]
            return fb.ins(f'call i64 @llvm.bswap.i64({a})','i64'),None
        if b in ('shift_left','shift_right','arithmetic_shift_right'):
            a,c=[self.gen(x,env,par)[0] for x in e.args]
            count=fb.ins(f'and i64 {c.name}, 63','i64')
            return fb.ins(f'{dict(shift_left="shl",shift_right="lshr",arithmetic_shift_right="ashr")[b]} {a}, {count.name}','i64'),None
        if b in ('wrapping_add','wrapping_sub','wrapping_mul'):
            a,c=[self.gen(x,env,par)[0] for x in e.args]
            return fb.ins(f'{b[9:]} {a}, {c.name}','i64'),None
        if b == "null": return Val("null", "ptr"), None
        if b == "noop": return Val("0", "i8"), None
        if b == "runtime_state": return Val("@ax_runtime_state", "ptr"), None
        if b in ('atomic_load_i64','atomic_store_i64','atomic_compare_exchange_i64','atomic_load_i32','atomic_store_i32'):
            args=[self.gen(a,env,False)[0] for a in e.args]
            p=fb.ins(f'getelementptr i8, {args[0]}, {args[1]}','ptr')
            if b=='atomic_load_i64':return fb.ins(f'load atomic i64, {p} acquire, align 8','i64'),None
            if b=='atomic_store_i64':
                fb.emit(f'store atomic {args[2]}, {p} release, align 8');return Val('0','i8'),None
            if b=='atomic_load_i32':return fb.ins(f'load atomic i32, {p} acquire, align 4','i32'),None
            if b=='atomic_store_i32':
                fb.emit(f'store atomic {args[2]}, {p} release, align 4');return Val('0','i8'),None
            value=fb.ins(f'cmpxchg {p}, {args[2]}, {args[3]} acq_rel acquire, align 8','{ i64, i1 }')
            return fb.ins(f'extractvalue {value}, 0','i64'),None
        if b in ('counter_ticks','counter_frequency'):
            if not self.triple.startswith(('arm64','aarch64')):raise ValueError(b+' requires an ARM64 target')
            instruction='isb\\0Amrs $0, cntvct_el0' if b=='counter_ticks' else 'mrs $0, cntfrq_el0'
            return fb.ins(f'call i64 asm sideeffect "{instruction}", "=r,~{{memory}}"()','i64'),None
        if b == 'spawn_thread':
            args = [self.gen(a,env,False)[0] for a in e.args]
            return fb.ins('call i64 @ax_spawn_thread('+', '.join(map(str,args))+')','i64'),None
        if b == "stack_alloc":
            size, _ = self.gen(e.args[0], env, False)
            return fb.ins(f"alloca i8, {size}, align 16", "ptr"), None
        if b in ("ptr_to_i64", "ptr_from_i64", "float_bits", "bits_float"):
            value, _ = self.gen(e.args[0], env, False)
            operation = {"ptr_to_i64": "ptrtoint", "ptr_from_i64": "inttoptr", "float_bits": "bitcast", "bits_float": "bitcast"}[b]
            return fb.ins(f"{operation} {value} to {lty(e.ty)}", lty(e.ty)), None
        if b in ("syscall6", "fork_syscall"):
            darwin = "apple" in self.triple
            arm = self.triple.startswith(("aarch64", "arm64"))
            if b == "fork_syscall":
                if not darwin:
                    number = 220 if arm else 57
                    vals = [Val(str(number), "i64")] + [Val("0", "i64")] * 6
                    if arm: vals[1] = Val("17", "i64")  # clone(SIGCHLD), fork semantics
                else: vals = [Val("2", "i64")] + [Val("0", "i64")] * 6
            else: vals = [self.gen(a, env, False)[0] for a in e.args]
            number, *args = vals
            if arm:
                asm = "svc #0x80; cneg x0, x0, cs" if darwin else "svc #0"
                if b == "fork_syscall" and darwin:
                    asm = "svc #0x80; b.cs 1f; cbz x1, 2f; mov x0, #0; b 2f; 1: neg x0, x0; 2:"
                # Darwin returns a second value in x1 (fork's child flag,
                # getpid's parent PID, etc.). Mark it as an output so LLVM
                # cannot reuse the pre-syscall x1 value after the trap.
                constraints = "={x0},={x1},0,1,{x2},{x3},{x4},{x5},{x16},~{memory},~{cc}" if darwin else "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"
            else:
                asm = "syscall; jnc 1f; negq %rax; 1:" if darwin else "syscall"
                if darwin: number = fb.ins(f"add {number}, 33554432", "i64")
                constraints = "={rax},{rdi},{rsi},{rdx},{r10},{r8},{r9},{rax},~{rcx},~{r11},~{memory},~{cc}"
            operands = ", ".join(str(v) for v in args + [number])
            # Darwin's ARM assembler treats ';' as a comment, not an
            # instruction separator. LLVM strings encode newlines as \0A.
            asm = asm.replace('; ', '\\0A')
            rty = "{ i64, i64 }" if darwin and arm else "i64"
            result = fb.ins(f'call {rty} asm sideeffect "{asm}", "{constraints}"({operands})', rty)
            if rty != "i64": result = fb.ins(f"extractvalue {result}, 0", "i64")
            return result, None
        if b == "addr": return Val(self.fname(e.target, "seq"), "ptr"), None
        if b == "data":
            a, _ = self.gen(e.args[0], env, False)
            return fb.ins(f"extractvalue {a}, 0", "ptr"), None
        if b in ("view", "handler_call"):
            args = [self.gen(a, env, False)[0] for a in e.args]
            data, ln = args[-2:]
            a = fb.ins(f"insertvalue {ARR} undef, ptr {data.name}, 0", ARR)
            a = fb.ins(f"insertvalue {a}, i64 {ln.name}, 1", ARR)
            a = fb.ins(f"insertvalue {a}, i64 0, 2", ARR)
            a = fb.ins(f"insertvalue {a}, ptr null, 3", ARR)
            if b == "view": return a, Val("0", "i64")
            r = fb.ins(f"call {ARR} {args[0].name}({a})", ARR)
            return r, fb.ins(f"extractvalue {r}, 2", "i64")
        if b == "ptr_add" or (b and (b.startswith(("load_", "store_", "volatile_load_", "volatile_store_")))):
            args = [self.gen(a, env, False)[0] for a in e.args]
            p = fb.ins(f"getelementptr i8, {args[0]}, {args[1]}", "ptr")
            if b == "ptr_add": return p, None
            volatile = "volatile " if b.startswith("volatile_") else ""
            if "load_" in b: return fb.ins(f"load {volatile}{lty(e.ty)}, {p}, align 1", lty(e.ty)), None
            fb.emit(f"store {volatile}{args[2]}, {p}, align 1")
            return Val("0", "i8"), None
        if b=='invoke_finalizer':
            fn,context=[self.gen(arg,env,False)[0] for arg in e.args];fb.emit(f'call void {fn.name}({context})');return Val('0','i8'),None
        if b == "invoke_region":
            fn, ctx, chunk = [self.gen(a, env, False)[0] for a in e.args]
            fb.emit(f"call void {fn.name}({ctx}, {chunk})")
            return Val("0", "i8"), None
        if b == "serve":
            port, _ = self.gen(e.args[0], env, par)
            return fb.ins(f"call i64 @ax_serve(i64 {port.name}, ptr {self.fname(e.handler, 'seq')})", "i64"), None
        if b == "sqrt":
            x, _ = self.gen(e.args[0], env, par)
            return fb.ins(f"call double @llvm.sqrt.f64({x})", "double"), None
        if b=='byte_read_le':
            # Keep lexical owners live until every argument has been evaluated;
            # indexed/temporary sources use normal owned-temporary protection.
            indexed_view=all(lexical_observer(arg) for arg in e.args[1:])
            view=self.record_argument_view(e.args[0],env,indexed_view) if lexical_view_expression(e.args[0]) else None
            value,own=(view,Val('0','i64')) if view is not None else self.gen(e.args[0],env,par)
            offset,_=self.gen(e.args[1],env,par);width,_=self.gen(e.args[2],env,par)
            if not getattr(e,'bounds_proven',False):
                valid=fb.ins(f'icmp eq i64 {width.name}, 1','i1')
                for size in (2,4,8):valid=fb.ins(f'or i1 {valid.name}, '+fb.ins(f'icmp eq i64 {width.name}, {size}','i1').name,'i1')
                self.trap_if(fb.ins(f'xor i1 {valid.name}, true','i1'),e,'byte read width')
                length=fb.ins(f'extractvalue {value}, 1','i64')
                # 0 <= offset <= length - width, the shape of a source guard such as
                # i >= 0 && i <= n - 8. Lengths are non-negative, so it cannot wrap.
                limit=fb.ins(f'sub nsw i64 {length.name}, {width.name}','i64')
                valid=self.and_(fb.ins(f'icmp sge i64 {offset.name}, 0','i1'),fb.ins(f'icmp sle i64 {offset.name}, {limit.name}','i1'))
                self.trap_if(fb.ins(f'xor i1 {valid.name}, true','i1'),e,'byte read bounds')
            data=fb.ins(f'extractvalue {value}, 0','ptr')
            source=fb.ins(f'getelementptr i8, ptr {data.name}, i64 {offset.name}','ptr')
            out=fb.alloca('i64');done=fb.label('byte_read_done')
            for size in (1,2,4,8):
                if size<8:
                    yes,no=fb.label('byte_read_word'),fb.label('byte_read_next')
                    fb.cbr(fb.ins(f'icmp eq i64 {width.name}, {size}','i1'),yes,no);fb.block(yes)
                loaded=fb.ins(f'load i{size*8}, ptr {source.name}, align 1',f'i{size*8}')
                result=loaded if size==8 else fb.ins(f'zext {loaded} to i64','i64')
                fb.store(result,out);fb.br(done)
                if size<8:fb.block(no)
            fb.block(done);result=fb.load('i64',out)
            self.maybe_free(value,self.nz(own),e.args[0].ty)
            return result,None
        if b in ('byte_copy','byte_write_le'):
            # Secure every dependency before consuming a destination field.
            offset,_=self.gen(e.args[1],env,par)
            source=None
            if b=='byte_copy':
                view=self.record_argument_view(e.args[2],env,True) if lexical_view_expression(e.args[2]) else None
                source,sown=(view,Val('0','i64')) if view is not None else self.gen(e.args[2],env,par)
                source=self.owning_value(source,sown,e.args[2].ty)
                size=fb.ins(f'extractvalue {source}, 1','i64')
            else:
                number,_=self.gen(e.args[2],env,par);size,_=self.gen(e.args[3],env,par)
                valid=self.and_(fb.ins(f'icmp sge i64 {size.name}, 0','i1'),fb.ins(f'icmp sle i64 {size.name}, 8','i1'))
                self.trap_if(fb.ins(f'xor i1 {valid.name}, true','i1'),e,'byte write width')
            value,own=self.gen(e.args[0],env,par)
            length=fb.ins(f'extractvalue {value}, 1','i64')
            # Both sizes are non-negative, so length - size cannot wrap.
            limit=fb.ins(f'sub nsw i64 {length.name}, {size.name}','i64')
            valid=self.and_(fb.ins(f'icmp sge i64 {offset.name}, 0','i1'),fb.ins(f'icmp sle i64 {offset.name}, {limit.name}','i1'))
            self.trap_if(fb.ins(f'xor i1 {valid.name}, true','i1'),e,'byte write bounds')
            owned=self.nz(own)
            # A set-only loop state (see set_only_state) is owned and unique on
            # every iteration; when it was moved here, no test is needed.
            always=isinstance(e.args[0],S.Var) and e.args[0].name in env and env[e.args[0].name].always_unique
            if owned is None:unique=None
            elif always:unique=Val('true','i1')
            elif fresh_array_result(e.args[0]):unique=owned
            else:unique=self.owned_unique(own,owned,value)
            if unique is not None and unique.name=='true':out=value
            else:
                result=fb.alloca(ARR)
                copy,inplace,done=fb.label('bytes_copy'),fb.label('bytes_inplace'),fb.label('bytes_ready')
                if unique is None:fb.br(copy)
                else:fb.cbr(unique,inplace,copy)
                fb.block(copy);fresh=self.detached_array(value,e.ty);self.maybe_free(value,owned,e.ty);fb.store(fresh,result);fb.br(done)
                if unique is not None:
                    fb.block(inplace);fb.store(value,result);fb.br(done)
                fb.block(done);out=fb.load(ARR,result)
            data=fb.ins(f'extractvalue {out}, 0','ptr')
            dest=fb.ins(f'getelementptr i8, ptr {data.name}, i64 {offset.name}','ptr')
            if source is not None:
                src=fb.ins(f'extractvalue {source}, 0','ptr')
                fb.emit(f'call void @llvm.memcpy.p0.p0.i64(ptr {dest.name}, ptr {src.name}, i64 {size.name}, i1 false)')
                self.drop_value(source,e.args[2].ty)
            else:
                def write_byte(env,i):
                    shift=fb.ins(f'mul i64 {i.name}, 8','i64')
                    shifted=fb.ins(f'lshr i64 {number.name}, {shift.name}','i64')
                    byte=fb.ins(f'trunc i64 {shifted.name} to i8','i8')
                    ptr=fb.ins(f'getelementptr i8, ptr {dest.name}, i64 {i.name}','ptr');fb.emit(f'store {byte}, {ptr}, align 1')
                self.counted_loop(Val('0','i64'),size,'$write_byte',{},write_byte)
            if self.unique_flags:
                # In place on a unique buffer, or a fresh copy: either way the only reference.
                out=self.with_own(out,Val(str(UNIQUE),'i64'));return out,Val(str(UNIQUE),'i64')
            return out,fb.ins(f'extractvalue {out}, 2','i64')
        if b == 'byte_slice':
            view=self.record_argument_view(e.args[0],env,True) if lexical_view_expression(e.args[0]) else None
            value,own=(view,Val('0','i64')) if view is not None else self.gen(e.args[0],env,par)
            lo,_=self.gen(e.args[1],env,par);hi,_=self.gen(e.args[2],env,par)
            length=fb.ins(f'extractvalue {value}, 1','i64')
            if not getattr(e,'bounds_proven',False):
                valid=self.and_(fb.ins(f'icmp sge i64 {lo.name}, 0','i1'),fb.ins(f'icmp sge i64 {hi.name}, {lo.name}','i1'))
                valid=self.and_(valid,fb.ins(f'icmp sle i64 {hi.name}, {length.name}','i1'))
                self.trap_if(fb.ins(f'xor i1 {valid.name}, true','i1'),e,'byte slice bounds')
            size=fb.ins(f'sub i64 {hi.name}, {lo.name}','i64')
            result=fb.alloca(ARR);empty,nonempty,done=fb.label('slice_empty'),fb.label('slice_data'),fb.label('slice_end')
            fb.cbr(fb.ins(f'icmp eq i64 {size.name}, 0','i1'),empty,nonempty)
            fb.block(empty);fb.store(Val('zeroinitializer',ARR),result);fb.br(done)
            fb.block(nonempty)
            control=fb.ins(f'extractvalue {value}, 3','ptr');data=fb.ins(f'extractvalue {value}, 0','ptr')
            start=fb.ins(f'getelementptr i8, ptr {data.name}, i64 {lo.name}','ptr')
            sliced=fb.ins(f'insertvalue {value}, ptr {start.name}, 0',ARR)
            sliced=fb.ins(f'insertvalue {sliced}, i64 {size.name}, 1',ARR)
            fb.store(self.clone_value(sliced,e.ty),result);fb.br(done)
            fb.block(done);self.maybe_free(value,self.nz(own),e.args[0].ty)
            out=fb.load(ARR,result);return out,fb.ins(f'extractvalue {out}, 2','i64')
        if b == "concat":
            parts=[]
            # int_text(x) as a concat argument is formatted straight into the
            # destination: no temporary digit string is allocated, copied or freed.
            # Only the standard library's int_text has the bare name; module
            # functions are mangled.
            fused=[isinstance(a,S.Call) and a.name=='int_text' and getattr(a,'builtin',None) is None
                   and len(a.args)==1 and a.args[0].ty==S.I64 and 'int_text' in self.fn_map for a in e.args]
            # html_escape(text) likewise: its escaped length is counted from the
            # source bytes, then the entities are written in place.
            escaped=[isinstance(a,S.Call) and a.name=='html_escape' and getattr(a,'builtin',None) is None and len(a.args)==1
                     and isinstance(a.args[0].ty,S.TArr) and a.args[0].ty.elem==S.U8 and 'html_escape' in self.fn_map for a in e.args]
            for index,arg in enumerate(e.args):
                if fused[index]:
                    parts.append((self.gen(arg.args[0],env,par)[0],None));continue
                if escaped[index]:
                    view=self.record_argument_view(arg.args[0],env,True) if lexical_view_expression(arg.args[0]) else None
                    parts.append((view,Val('0','i64')) if view is not None else self.gen(arg.args[0],env,par));continue
                view=self.record_argument_view(arg,env,True) if index>0 and lexical_view_expression(arg) else None
                parts.append((view,Val('0','i64')) if view is not None else self.gen(arg,env,par))
            def escaped_len(v):
                data = fb.ins(f"extractvalue {v}, 0", "ptr"); n = fb.ins(f"extractvalue {v}, 1", "i64")
                return fb.ins(f"call i64 @ax_esc_len(ptr {data.name}, i64 {n.name})", "i64")
            lens = [fb.ins(f"call i64 @ax_dec_len(i64 {v.name})", "i64") if fused[i] else escaped_len(v) if escaped[i]
                    else Val(str(len(a.value)), "i64") if isinstance(a, S.Str) else fb.ins(f"extractvalue {v}, 1", "i64")
                    for i, ((v, _), a) in enumerate(zip(parts, e.args))]
            def write(d, v, own, l, a, i):
                if fused[i]:
                    following = e.args[i+1] if i+1 < len(e.args) else None
                    spill = 'ax_dec_write4' if isinstance(following, S.Str) and len(following.value) >= 3 else 'ax_dec_write'
                    fb.emit(f"call void @{spill}(ptr {d.name}, i64 {v.name}, i64 {l.name})");return
                if escaped[i]:
                    data = fb.ins(f"extractvalue {v}, 0", "ptr"); n = fb.ins(f"extractvalue {v}, 1", "i64")
                    fb.emit(f"call void @ax_esc_write(ptr {d.name}, ptr {data.name}, i64 {n.name})")
                    self.maybe_free(v, self.nz(own), a.args[0].ty);return
                src = fb.ins(f"extractvalue {v}, 0", "ptr")
                # Existing parts' byte sizes were allocated, so they cannot overflow.
                nbytes = l if esize == 1 else fb.ins(f"mul nuw nsw i64 {l.name}, {esize}", "i64")
                fb.emit(f"call void @llvm.memcpy.p0.p0.i64(ptr {d.name}, ptr {src.name}, i64 {nbytes.name}, i1 false)")
                self.maybe_free(v, self.nz(own), a.ty)
            # Byte strings and UTF-16 code-unit strings: lengths count elements.
            esize = elem_size(e.ty); element = storage_ty(e.ty.elem)
            total = lens[0]
            for l in lens[1:]: total = self.checked_operation('+',total,l,e)
            v0, own0 = parts[0]
            if fused[0] or escaped[0]: own0 = Val('0', 'i64')
            res = fb.alloca(ARR)
            # If we own the first buffer and its capacity class has room, append in place
            # (amortised O(appended bytes), like String::push_str); otherwise allocate and copy all.
            c0 = self.nz(own0)
            grow, fresh, join = fb.label("cat_grow"), fb.label("cat_fresh"), fb.label("cat_join")
            if c0 is None: fb.br(fresh)
            else:
                cap = self.capacity(lens[0] if esize == 1 else fb.ins(f"mul nuw nsw i64 {lens[0].name}, {esize}", "i64"))
                # Compare in elements: capacity classes are powers of two of at least 16 bytes.
                if esize != 1: cap = fb.ins(f"lshr i64 {cap.name}, {esize.bit_length() - 1}", "i64")
                fits = fb.ins(f"icmp sle i64 {total.name}, {cap.name}", "i1")
                ok = self.and_(self.and_(c0,self.array_unique(v0)), fits)
                fb.cbr(ok, grow, fresh)
                fb.block(grow)
                dst = fb.ins(f"extractvalue {v0}, 0", "ptr")
                off = lens[0]
                for i, ((v, own), l, a) in list(enumerate(zip(parts, lens, e.args)))[1:]:
                    d = fb.ins(f"getelementptr inbounds {element}, ptr {dst.name}, i64 {off.name}", "ptr")
                    write(d, v, own, l, a, i)
                    off = fb.ins(f"add i64 {off.name}, {l.name}", "i64")
                grown = fb.ins(f"insertvalue {v0}, i64 {total.name}, 1", ARR)
                grown = fb.ins(f"insertvalue {grown}, i64 1, 2", ARR)
                fb.store(grown, res); fb.br(join)
            fb.block(fresh)
            out = self.new_array(e.ty, total)
            dst = fb.ins(f"extractvalue {out}, 0", "ptr")
            off = Val("0", "i64")
            for i, ((v, own), l, a) in enumerate(zip(parts, lens, e.args)):
                d = fb.ins(f"getelementptr inbounds {element}, ptr {dst.name}, i64 {off.name}", "ptr")
                write(d, v, own, l, a, i)
                off = fb.ins(f"add i64 {off.name}, {l.name}", "i64")
            fb.store(out, res); fb.br(join)
            fb.block(join)
            value=fb.load(ARR,res)
            return value, fb.ins(f'extractvalue {value}, 2','i64')
        if b == 'push':
            t=e.args[0].ty
            a,own=self.gen(e.args[0],env,par)
            value,vown=self.gen(e.args[1],env,par)
            if isinstance(t.elem,S.TArr):value=self.owning_value(value,vown,t.elem)
            length=fb.ins(f'extractvalue {a}, 1','i64')
            total=self.checked_operation('+',length,Val('1','i64'),e)
            old_bytes=fb.ins(f'mul i64 {length.name}, {elem_size(t)}','i64')
            new_bytes=fb.ins(f'mul i64 {total.name}, {elem_size(t)}','i64')
            maximum=(1<<62)//max(1,elem_size(t))
            self.trap_if(fb.ins(f'icmp ugt i64 {total.name}, {maximum}','i1'),e,'array push size overflow')
            result=fb.alloca(ARR);fresh,join=fb.label('push_allocate'),fb.label('push_join')
            owned=self.nz(own)
            flag=self.and_(owned,self.array_unique(a)) if owned is not None else None
            if not isinstance(t.elem,S.TRec) and flag is not None:
                grow=fb.label('push_inplace')
                size=elem_size(t)
                if size<=16 and size>0 and size&(size-1)==0:
                    # Adding one power-of-two-sized element crosses the
                    # allocator's rounded capacity exactly at a power-of-two
                    # length (above its minimum 16-byte payload). This is the
                    # same growth policy, without a ctlz/variable shift per push.
                    previous=fb.ins(f'sub i64 {length.name}, 1','i64')
                    bits=fb.ins(f'and i64 {length.name}, {previous.name}','i64')
                    interior=fb.ins(f'icmp ne i64 {bits.name}, 0','i1')
                    small=fb.ins(f'icmp ult i64 {length.name}, {16//size}','i1')
                    fits=fb.ins(f'or i1 {interior.name}, {small.name}','i1')
                else:
                    cap=self.capacity(old_bytes)
                    fits=fb.ins(f'icmp ule i64 {new_bytes.name}, {cap.name}','i1')
                fb.cbr(self.and_(flag,fits),grow,fresh);fb.block(grow)
                grown=fb.ins(f'insertvalue {a}, i64 {total.name}, 1',ARR)
                self.store_elem(grown,length,e.ty,value);fb.store(grown,result);fb.br(join)
            else:fb.br(fresh)
            fb.block(fresh);out=self.new_array(e.ty,total)
            if not managed(t.elem) and not isinstance(t.elem,S.TRec):
                src=fb.ins(f'extractvalue {a}, 0','ptr');dst=fb.ins(f'extractvalue {out}, 0','ptr')
                fb.emit(f'call void @llvm.memcpy.p0.p0.i64(ptr {dst.name}, ptr {src.name}, i64 {old_bytes.name}, i1 false)')
            else:
                # Transfer initialized children when unique; otherwise deep-copy.
                transfer,copy,done=fb.label('push_transfer'),fb.label('push_clone'),fb.label('push_copied')
                fb.cbr(flag or Val('false','i1'),transfer,copy)
                fb.block(transfer)
                self.counted_loop(Val('0','i64'),length,'$push',{},lambda env,i:self.store_elem(out,i,e.ty,self.load_elem(a,i,t)))
                fb.br(done);fb.block(copy)
                self.counted_loop(Val('0','i64'),length,'$push_copy',{},lambda env,i:self.store_elem(out,i,e.ty,self.clone_value(self.load_elem(a,i,t),t.elem)))
                fb.br(done);fb.block(done)
            self.store_elem(out,length,e.ty,value)
            # Unique old buffers transferred their children; shared buffers
            # still have another owner and will not run child destruction here.
            self.maybe_free(a,owned,t,drop_children=False)
            fb.store(out,result);fb.br(join);fb.block(join)
            out=fb.load(ARR,result);return out,fb.ins(f'extractvalue {out}, 2','i64')
        if b == "set":
            t = e.args[0].ty
            root = e.args[0]
            while isinstance(root, S.Field): root = root.expr
            if isinstance(root, S.Var):
                # A field move clears its source slot. Read index/replacement first,
                # so set(record.buffer, i, record.buffer[j]) remains valid.
                i, _ = self.gen(e.args[1], env, par)
                v, vown = self.gen(e.args[2], env, par)
                a, own = self.gen(e.args[0], env, par)
            else:
                a, own = self.gen(e.args[0], env, par)
                i, _ = self.gen(e.args[1], env, par)
                v, vown = self.gen(e.args[2], env, par)
            if isinstance(t.elem, S.TArr): v = self.owning_value(v, vown, t.elem)
            # in place when we own the buffer, else copy-on-write
            res = fb.alloca(ARR)
            owned=self.nz(own)
            unique=isinstance(e.args[0],S.Var) and e.args[0].name in env and env[e.args[0].name].always_unique
            # A set-only loop state is owned and unique on every iteration.
            if owned is None:c=None
            elif unique:c=Val('true','i1')
            elif fresh_array_result(e.args[0]):c=owned
            else:c=self.owned_unique(own,owned,a)
            if c is None or c.name != "true":
                inplace, copy, join = fb.label("set_inplace"), fb.label("set_copy"), fb.label("set_join")
                if c is None: fb.br(copy)
                else: fb.cbr(c, inplace, copy)
                fb.block(copy)
                ln = fb.ins(f"extractvalue {a}, 1", "i64")
                fresh = self.detached_array(a, t)
                self.maybe_free(a,owned,t)
                if managed(t.elem): self.drop_value(self.load_elem(fresh, i, t), t.elem)
                self.store_elem(fresh, i, t, v)
                fb.store(fresh, res); fb.br(join)
                if c is not None:
                    fb.block(inplace)
                    if managed(t.elem): self.drop_value(self.load_elem(a, i, t), t.elem)
                    self.store_elem(a, i, t, v)
                    fb.store(a, res); fb.br(join)
                fb.block(join)
            else:
                if managed(t.elem): self.drop_value(self.load_elem(a, i, t), t.elem)
                self.store_elem(a, i, t, v)
                fb.store(a, res)
            value=fb.load(ARR,res)
            if self.unique_flags:
                # In place on a unique buffer, or a fresh copy: either way the only reference.
                value=self.with_own(value,Val(str(UNIQUE),'i64'));return value,Val(str(UNIQUE),'i64')
            return value, fb.ins(f'extractvalue {value}, 2','i64')
        signature=getattr(e,'indirect_signature',None)
        if signature is not None:
            from types import SimpleNamespace
            callee=SimpleNamespace(ret=signature.ret,effect=signature.capabilities is not None,exported=False,external=False,variadic=False,params=[S.Param(str(i),t,[]) for i,t in enumerate(signature.params)])
            function=self.fb.load('ptr',env[e.name].ptr).name
        else:
            callee = next(f for f in self.fns if f.name == e.name)
            function=None
        vals = []; temporaries = []
        for argument_index,a in enumerate(e.args):
            # A borrowed element must not outlive a different argument that can
            # consume its parent during the call. Restrict indexed views to calls
            # whose other managed arguments are borrowed or static literals.
            indexed_view=all(j==argument_index or lexical_observer(other) and
                             (not managed(other.ty) or j in getattr(e,'borrowed_args',set()) or isinstance(other,S.Str))
                             for j,other in enumerate(e.args))
            if isinstance(a.ty,S.TArr) and argument_index in getattr(e,'borrowed_args',set()):
                view=self.record_argument_view(a,env,indexed_view)
                if view is not None:
                    vals.append(self.with_own(view,Val('0','i64')));continue
                if self.parameter_borrowed(callee,argument_index):
                    value,own=self.gen(a,env,par)
                    temporaries.append((self.with_own(value,own),a.ty))
                    vals.append(self.with_own(value,Val('0','i64')));continue
            if self.parameter_byref(callee,argument_index):
                parameter=callee.params[argument_index]
                if not (parameter.borrowed or not (callee.effect or parameter.owned)):
                    # Transfer into a private argument slot. The callee owns
                    # this value and may consume its fields; it must not mutate
                    # the caller's slot or borrow an unretained temporary.
                    value,_=self.gen(a,env,par)
                    pointer=fb.alloca(lty(a.ty));fb.store(value,pointer)
                    vals.append(Val(pointer,'ptr'));continue
                pointer=self.record_argument_pointer(a,env)
                if pointer is None:
                    view=self.record_argument_view(a,env,indexed_view)
                    if view is None:
                        view,_=self.gen(a,env,par)
                        temporaries.append((view,a.ty))
                    pointer=fb.alloca(lty(a.ty));fb.store(view,pointer)
                vals.append(Val(pointer,'ptr'))
                continue
            v, own = self.gen(a, env, par)
            if own is not None:
                # Flag 2 is a call-local proof, never a property propagated by
                # arbitrary returned values or other argument contracts.
                observed=argument_index in self.observed_parameters.get(callee.name if hasattr(callee,'name') else '',set())
                fresh=fresh_array_result(a) or isinstance(a,S.Call) and a.name in self.fn_map and not (self.fn_map[a.name].effect or self.fn_map[a.name].external or self.fn_map[a.name].exported or getattr(self.fn_map[a.name],'precompiled',False)) and not self.return_aliases[a.name]
                proof=2 if observed and fresh else 1
                owned=self.nz(own)
                normalized=fb.ins(f'zext i1 {owned.name if owned is not None else "false"} to i64','i64')
                if proof==2:normalized=fb.ins(f'mul i64 {normalized.name}, 2','i64')
                v=self.with_own(v,normalized)
            vals.append(v)
        mode = "par" if (par and self.mode == "par") else "seq"
        args = ", ".join(str(v) for v in vals)
        rty = return_type(e.ty)
        signature = f" ({', '.join([lty(p.ty) for p in callee.params] + ['...'])})" if callee.variadic else ""
        call = f"call {rty}{signature} {function if function is not None else self.fname(callee, mode)}({args})"
        if e.ty == S.UNIT:
            fb.emit(call)
            for value,ty in temporaries:self.drop_value(value,ty)
            return Val("0", "i8"), None
        r = fb.ins(call, rty)
        for value,ty in temporaries:self.drop_value(value,ty)
        if isinstance(e.ty, S.TArr):
            return r, fb.ins(f"extractvalue {r}, 2", "i64")
        return r, None

    # ------------------------------------------------------------ sum / arr
    def counted_loop(self, lo: Val, hi: Val, var: str, env, body_fn):
        fb = self.fb
        ip = fb.alloca("i64"); fb.store(lo, ip)
        cond, body, end = fb.label("for_cond"), fb.label("for_body"), fb.label("for_end")
        fb.br(cond); fb.block(cond)
        i = fb.load("i64", ip)
        c = fb.ins(f"icmp slt i64 {i.name}, {hi.name}", "i1")
        fb.cbr(c, body, end); fb.block(body)
        env2 = dict(env); env2[var] = Slot(ip, "i64", axty=S.I64)
        body_fn(env2, i)
        i2 = fb.ins(f"add nsw i64 {i.name}, 1", "i64"); fb.store(i2, ip)
        fb.br(cond); fb.block(end)

    def sum_bounded(self, e):
        """An i64 sum whose body lies in [b0, b1] over at most C iterations has
        every partial, chunk and combined sum in [min(0, b0*C), max(0, b1*C)],
        so its accumulation cannot overflow when that interval fits in i64.
        C <= hi - lo, which the comprehension has already checked fits in i64;
        the intervals are the whole-program ones of the ranges pass."""
        body = self.value_ranges.get(id(e.body))
        lo, hi = self.value_ranges.get(id(e.lo)), self.value_ranges.get(id(e.hi))
        if not body or not lo or not hi: return False
        count = max(0, min(Ranges.MAX, hi[1] - lo[0]))
        return Ranges.MIN <= min(0, body[0] * count) and max(0, body[1] * count) <= Ranges.MAX

    def comprehension(self, e, env, par):
        fb = self.fb
        is_sum = isinstance(e, S.Sum)
        # Child allocations after fork are not mapped in the parent. Managed
        # elements therefore stay sequential until a shared aggregate arena exists.
        if not is_sum and managed(e.ty.elem): par = False
        # Constant short ranges (empty placeholders, small fixed buffers) never
        # repay parallel dispatch; a plain loop also keeps outlined regions and
        # dispatcher calls out of every caller they are inlined into.
        if isinstance(e.lo, S.Num) and isinstance(e.hi, S.Num) and e.hi.value - e.lo.value <= 64: par = False
        # A constant fill (arr(i in 0..n) -1, u8(0), false) is a store loop that
        # LLVM vectorizes; dispatching it as a parallel region only adds calls.
        fill = e.body
        while isinstance(fill, S.Cast): fill = fill.expr
        if isinstance(fill, S.Un) and fill.op == '-': fill = fill.expr
        if not is_sum and isinstance(fill, (S.Num, S.BoolLit, S.Byte)): par = False
        lo, _ = self.gen(e.lo, env, par)
        hi, _ = self.gen(e.hi, env, par)
        if self.checked_integer():self.checked_operation('-',hi,lo,e)
        # The vectorized sum loop reads the same mark for its lane additions.
        if is_sum and e.ty == S.I64 and self.sum_bounded(e): e.arithmetic_proven = True
        ety = lty(e.ty)
        if is_sum:
            acc = fb.alloca(ety); fb.store(Val(zero(e.ty), ety), acc)
            out = None
        else:
            ln = fb.ins(f"sub i64 {hi.name}, {lo.name}", "i64")
            out = self.new_array(e.ty, ln)
        library_body = self.fn.name in self.library_names
        vec = is_sum and self.vectorize and e.ty in (S.I64, S.F64) and VZ.eligible(e.body, self.fn_map,allow_libraries=library_body)
        reads = []
        # NEON holds two i64 lanes and has no 64-bit vector multiply: forced
        # 4-lane i64 array bodies ran 2.8x slower than the scalar loop, which
        # LLVM's own cost model still vectorizes where it pays. f64 is kept.
        array_types = (S.F64,) if self.triple.startswith(('aarch64','arm64')) else (S.I64, S.F64)
        varr = not is_sum and self.vectorize and e.ty.elem in array_types and VZ.eligible(e.body,self.fn_map,array_var=e.var,reads=reads,allow_libraries=library_body)
        if vec: self.vector_sums.append({"fn": self.fn.name, "node": e.hash[:12], "pos": list(e.pos), "lanes": VZ.K})
        if varr: self.vector_arrays.append({"fn": self.fn.name, "node": e.hash[:12], "pos": list(e.pos), "lanes": VZ.ARRAY_LANES, 'reads':sorted(set(reads))})
        if not par:
            if vec:
                VZ.vector_sum_loop(self, fb, e, lo, hi, env, acc, self.fn_map)
                return fb.load(ety, acc), None
            if varr:
                VZ.vector_array_loop(self,fb,e,lo,hi,env,out,lo,reads)
                return out,fb.ins(f'extractvalue {out}, 2','i64')
            def body(env2, i):
                v, own = self.gen(e.body, env2, par=False)
                if not is_sum and isinstance(e.ty.elem, S.TArr): v = self.owning_value(v, own, e.ty.elem)
                if is_sum:
                    fb.store(self.add_vals(fb.load(ety, acc), v, e.ty, e), acc)
                else:
                    k = fb.ins(f"sub i64 {i.name}, {lo.name}", "i64")
                    self.store_elem(out, k, e.ty, v)
            # A short little-endian word-to-byte comprehension needs one store,
            # not a loop of variable shifts. Fresh buffers have at least 16
            # bytes of physical capacity; bytes beyond the logical length are
            # inaccessible. Keep the ordinary loop for lengths above eight.
            cast=e.body
            shift=cast.expr if isinstance(cast,S.Cast) and cast.to==S.U8 else None
            word=shift.args[0] if isinstance(shift,S.Call) and shift.name=='shift_right' and len(shift.args)==2 else None
            amount=shift.args[1] if word is not None else None
            packed=(not is_sum and e.ty.elem==S.U8 and isinstance(e.lo,S.Num) and e.lo.value==0
                    and isinstance(word,S.Var) and word.name!=e.var and word.ty==S.I64
                    and isinstance(amount,S.Bin) and amount.op=='*'
                    and isinstance(amount.left,S.Var) and amount.left.name==e.var
                    and isinstance(amount.right,S.Num) and amount.right.value==8
                    and self.triple.startswith(('x86_64','aarch64','arm64')))
            if packed:
                small,ordinary,ready=fb.label('word_bytes'),fb.label('byte_loop'),fb.label('bytes_ready')
                nonempty=fb.ins(f'icmp sgt i64 {hi.name}, 0','i1')
                short=fb.ins(f'icmp sle i64 {hi.name}, 8','i1')
                fb.cbr(self.and_(nonempty,short),small,ordinary)
                fb.block(small)
                value,_=self.gen(word,env,par=False)
                data=fb.ins(f'extractvalue {out}, 0','ptr')
                fb.emit(f'store i64 {value.name}, ptr {data.name}, align 1')
                fb.br(ready);fb.block(ordinary)
                self.counted_loop(lo,hi,e.var,env,body)
                fb.br(ready);fb.block(ready)
                return out,fb.ins(f'extractvalue {out}, 2','i64')
            self.counted_loop(lo, hi, e.var, env, body)
            return (fb.load(ety, acc), None) if is_sum else (out, fb.ins(f'extractvalue {out}, 2','i64'))

        # ---- parallel: outline the body into @<fn>__regionK(ptr ctx, i64 chunk)
        from .kernel_workers import allocation_free
        shared = 'linux' in self.triple and allocation_free(e.body,self.fn_map,allow_libraries=library_body)
        dispatcher = 'ax_par_for_shared' if shared else 'ax_par_for'
        self.par_regions.append({"fn": self.fn.name, "node": e.hash[:12], "pos": list(e.pos), "kind": "sum" if is_sum else "arr", 'dispatcher':dispatcher})
        d = fb.ins(f"sub i64 {hi.name}, {lo.name}", "i64")
        pos = fb.ins(f"icmp sgt i64 {hi.name}, {lo.name}", "i1")
        n = fb.ins(f"select i1 {pos.name}, i64 {d.name}, i64 0", "i64")
        cost=VZ.work_cost(e.body) if shared else None
        self.par_regions[-1]['work_cost']=cost
        nchunks = fb.ins(f"call i64 @ax_chunks_work(i64 {n.name}, i64 {cost})" if cost is not None else f"call i64 @ax_chunks(i64 {n.name})", "i64")
        esz = 8 if not isinstance(e.ty, S.TRec) else sum(scalar_size(ft) for _, ft in e.ty.fields)
        if is_sum:
            pby = fb.ins(f"mul i64 {nchunks.name}, {max(esz, 8)}", "i64")
            target = fb.ins(f"call ptr @ax_alloc(i64 {pby.name})", "ptr")
        else:
            target = out
        captured = [(name, slot) for name, slot in env.items()]
        cty = "{ i64, i64, i64, " + ("ptr" if is_sum else ARR) + "".join(f", {s.ty}" for _, s in captured) + " }"
        ctx = fb.alloca(cty)
        fields = [lo, n, nchunks, target] + [fb.load(s.ty, s.ptr) for _, s in captured]
        for k, v in enumerate(fields):
            p = fb.ins(f"getelementptr inbounds {cty}, ptr {ctx}, i32 0, i32 {k}", "ptr")
            fb.store(v, p.name)
        self.region_k += 1
        if self.library_names:
            self.region_k=self.region_counters.get(self.fn.name,0)+1
            self.region_counters[self.fn.name]=self.region_k
        rname = f"@ax_{self.fn.name}__region{self.region_k}"
        fb.emit(f"call void @{dispatcher}(i64 {nchunks.name}, ptr {rname}, ptr {ctx})")
        saved = self.fb
        rb = FuncBuilder(f"define internal void {rname}(ptr %ctx, i64 %chunk)")
        self.fb = rb
        def fld(k, ty):
            p = rb.ins(f"getelementptr inbounds {cty}, ptr %ctx, i32 0, i32 {k}", "ptr")
            return rb.load(ty, p.name)
        rlo, rn, rch = fld(0, "i64"), fld(1, "i64"), fld(2, "i64")
        rtgt = fld(3, "ptr" if is_sum else ARR)
        renv: Dict[str, Slot] = {}
        for k, (name, s) in enumerate(captured):
            v = fld(4 + k, s.ty); ptr = rb.alloca(s.ty); rb.store(v, ptr)
            renv[name] = Slot(ptr, s.ty, axty=s.axty)                 # arrays are borrowed inside regions
            if s.ty == ARR and isinstance(s.axty, S.TArr): self.assume_array(v, s.axty)
        a = rb.ins(f"mul i64 {rn.name}, %chunk", "i64")
        clo = rb.ins(f"sdiv i64 {a.name}, {rch.name}", "i64"); clo = rb.ins(f"add i64 {clo.name}, {rlo.name}", "i64")
        c1 = rb.ins("add i64 %chunk, 1", "i64"); b = rb.ins(f"mul i64 {rn.name}, {c1.name}", "i64")
        chi = rb.ins(f"sdiv i64 {b.name}, {rch.name}", "i64"); chi = rb.ins(f"add i64 {chi.name}, {rlo.name}", "i64")
        racc = rb.alloca(ety) if is_sum else None
        if is_sum: rb.store(Val(zero(e.ty), ety), racc)
        def rbody(env2, i):
            v, _ = self.gen(e.body, env2, par=False)
            if is_sum:
                rb.store(self.add_vals(rb.load(ety, racc), v, e.ty, e), racc)
            else:
                k = rb.ins(f"sub i64 {i.name}, {rlo.name}", "i64")
                self.store_elem(rtgt, k, e.ty, v)
        if vec: VZ.vector_sum_loop(self, rb, e, clo, chi, renv, racc, self.fn_map)
        elif varr: VZ.vector_array_loop(self,rb,e,clo,chi,renv,rtgt,rlo,reads)
        else: self.counted_loop(clo, chi, e.var, renv, rbody)
        if is_sum:
            p = rb.ins(f"getelementptr inbounds {ety}, ptr {rtgt.name}, i64 %chunk", "ptr")
            rb.store(rb.load(ety, racc), p.name)
        rb.emit("ret void")
        self.funcs.append(rb.render())
        self.fb = fb = saved
        if is_sum:
            def red(env2, c):
                p = fb.ins(f"getelementptr inbounds {ety}, ptr {target.name}, i64 {c.name}", "ptr")
                fb.store(self.add_vals(fb.load(ety, acc), fb.load(ety, p.name), e.ty, e), acc)
            self.counted_loop(Val("0", "i64"), nchunks, "%chunk", env, red)
            fb.emit(f"call void @ax_free(ptr {target.name}, i64 {pby.name})")
            return fb.load(ety, acc), None
        return out, fb.ins(f'extractvalue {out}, 2','i64')

    # ------------------------------------------------------------ loop
    def loop(self, e: S.Loop, env, par):
        fb = self.fb
        slots: List[Slot] = []
        env2 = dict(env)
        def plans(name, t):
            # Successors observe this iteration's fields; yield observes the
            # replacement state on loop exit. They are distinct lifetimes.
            consume = consume_plan(list(e.nexts), name) | consume_plan([e.yld], name)
            body_fields=field_consume_plan(list(e.nexts),name,t)
            exit_fields=field_consume_plan([e.yld],name,t)
            fields = {field:ids | exit_fields.get(field,set()) for field,ids in body_fields.items()}
            linear = flag_linear([e.cond, *e.nexts, e.yld], name, t, consume, fields) if self.unique_flags and managed(t) else \
                (frozenset() if isinstance(t, S.TRec) else False)
            return consume, fields, linear
        states = [plans(name, t) for name, t in zip(e.names, e.state_tys)]
        for name, init, t, (consume, fields, linear) in zip(e.names, e.inits, e.state_tys, states):
            v, own = self.gen(init, env, par)
            if isinstance(t,S.TArr):
                v=self.owning_value(v,own,t);own=fb.ins(f'extractvalue {v}, 2','i64')
                if linear is not True: own=self.plain_own(own)
            elif managed(t): v=self.plain_value(v,t,linear)
            ptr = fb.alloca(v.ty); fb.store(v, ptr)
            s = Slot(ptr, v.ty, axty=t)
            if v.ty == ARR:
                s.own_ptr = fb.alloca("i64"); fb.store(own, s.own_ptr)
                s.consume, s.field_consume, s.linear = consume, fields, linear
                self.assume_array(v, t)
            elif managed(t):
                s.own_ptr = fb.alloca('i64'); fb.store(Val('1','i64'),s.own_ptr)
                s.consume, s.field_consume, s.linear = consume, fields, linear
            slots.append(s); env2[name] = s
        # After every initializer took its references, so none can share it later.
        for k, (s, t) in enumerate(zip(slots, e.state_tys)):
            if s.ty == ARR and s.own_ptr and set_only_state(e, k):
                self.ensure_unique(s, t); s.always_unique = True
        cond, body, exit_ = fb.label("loop_cond"), fb.label("loop_body"), fb.label("loop_exit")
        fb.br(cond); fb.block(cond)
        c, _ = self.gen(e.cond, env2, par)
        fb.cbr(c, body, exit_); fb.block(body)
        nexts = [self.gen(nx, env2, par) for nx in e.nexts]
        # Each successor owns an independent reference before the old state is
        # released. An empty/borrowed successor must not suppress cleanup of
        # unrelated loop buffers (the pre-sharing ownership scheme did so).
        secured=[]
        for (v,own),t in zip(nexts,e.state_tys):
            if isinstance(t,S.TArr):
                v=self.owning_value(v,own,t);own=fb.ins(f'extractvalue {v}, 2','i64')
            secured.append((v,own))
        nexts=secured
        for s,t in zip(slots,e.state_tys):
            if isinstance(t,S.TRec) and managed(t):self.drop_record_slot(s)
            if isinstance(t,S.TArr) and s.own_ptr:
                self.maybe_free(fb.load(ARR,s.ptr),self.nz(fb.load('i64',s.own_ptr)),t)
        for s, (v, own), t in zip(slots, nexts, e.state_tys):
            if isinstance(t,S.TArr) and s.linear is not True: own=self.plain_own(own)
            elif managed(t) and not isinstance(t,S.TArr): v=self.plain_value(v,t,s.linear)
            fb.store(v, s.ptr)
            if s.own_ptr:
                fb.store(own if isinstance(t,S.TArr) else Val('1','i64'), s.own_ptr)
                if isinstance(t,S.TArr): self.assume_array(v, t)
        fb.br(cond); fb.block(exit_)
        # Uniqueness was only established for the condition and successors;
        # the yield may share the final state before writing it.
        for s in slots: s.always_unique = False
        yv, yown = self.gen(e.yld, env2, par)
        if isinstance(e.yld.ty,S.TArr):
            yv=self.owning_value(yv,yown,e.yld.ty);yown=fb.ins(f'extractvalue {yv}, 2','i64')
        self.free_scope(slots,None)
        return yv, yown
