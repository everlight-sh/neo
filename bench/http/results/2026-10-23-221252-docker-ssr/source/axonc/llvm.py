"""LLVM IR backend: Axon graph -> LLVM IR -> native code (the rustc pipeline).

Lowering uses allocas for every binder and lets LLVM's mem2reg/SROA promote
them to SSA registers, as clang and rustc do. Parallel `sum`/`arr` regions are
outlined into separate functions with an explicit context struct (closure
conversion) and dispatched by the runtime's thread pool.

Memory: arrays are { ptr, len, owned }. Ownership moves along a uniqueness
discipline decided per scope by `consume_plan`: an array variable whose every
control-flow path uses it at most once as a whole (passed to a call, updated
with `set`, returned, stored into a loop state) is *moved* at that use, and
`set` then updates in place. Whatever still owns a buffer at scope exit frees
it. Arrays of records are laid out struct-of-arrays inside one buffer, fields
ordered by size; the program never sees the layout.

Proven facts reach LLVM as `llvm.assume` (index ranges, dereferenceable
buffers), so the optimizer can speculate and vectorize what the checker proved.
"""
from __future__ import annotations
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from . import syntax as S
from . import vectorize as VZ
from . import ranges as Ranges

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

def lty(t) -> str:
    if t == S.I64: return "i64"
    if t == S.F64: return "double"
    if t == S.BOOL: return "i1"
    if t == S.U8: return "i8"
    if t == S.I32: return "i32"
    if t == S.PTR: return "ptr"
    if t == S.UNIT: return "i8"  # unit values have no payload; function ABI returns void
    if isinstance(t, S.TArr): return ARR
    if isinstance(t, S.TRec): return "{ " + ", ".join(lty(ft) for _, ft in t.fields) + " }"
    raise TypeError(t)

def scalar_size(t) -> int:
    if t == S.I32: return 4
    return 1 if t in (S.BOOL, S.U8) else 8

def return_type(t): return "void" if t == S.UNIT else lty(t)

def elem_size(t: S.TArr) -> int:
    if isinstance(t.elem, S.TRec): return sum(scalar_size(ft) for _, ft in t.elem.fields)
    return scalar_size(t.elem)

def rec_layout(rt: S.TRec) -> List[Tuple[int, str, int, int]]:
    """(field index, llvm type, size, prefix bytes per element) in layout order: big fields first."""
    order = sorted(range(len(rt.fields)), key=lambda k: -scalar_size(rt.fields[k][1]))
    out, prefix = [], 0
    for k in order:
        ft = rt.fields[k][1]
        out.append((k, lty(ft), scalar_size(ft), prefix))
        prefix += scalar_size(ft)
    return out

def zero(t) -> str:
    if t == S.F64: return "0.0"
    if isinstance(t, S.TRec): return "{ " + ", ".join(f"{lty(ft)} {zero(ft)}" for _, ft in t.fields) + " }"
    return "0"

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

def seq(a: List[Summary], b: List[Summary]) -> List[Summary]:
    out = {}
    for x in a:
        for y in b:
            s = Summary(x.c + y.c, x.r or y.r, x.bad or y.bad or (x.c > 0 and (y.r or y.c > 0)), x.ids | y.ids)
            key = (s.c, s.r, s.bad)
            out[key] = Summary(s.c, s.r, s.bad, out[key].ids | s.ids) if key in out else s
    return list(out.values())

EMPTY = [Summary(0, False, False, frozenset())]
def READ(): return [Summary(0, True, False, frozenset())]
def downgrade(a: List[Summary]) -> List[Summary]:
    return [Summary(0, x.r or x.c > 0, x.bad, frozenset()) for x in a]

def paths(e: S.Node, name: str, as_read: bool = False) -> List[Summary]:
    if isinstance(e, S.Var):
        if e.name != name: return EMPTY
        return READ() if as_read else [Summary(1, False, False, frozenset([id(e)]))]
    if isinstance(e, (S.Num, S.Flt, S.BoolLit, S.Str, S.Byte)): return EMPTY
    if isinstance(e, S.Bin):
        l, r = paths(e.left, name), paths(e.right, name)
        return seq(l, r) + l if e.op in ("&&", "||") else seq(l, r)
    if isinstance(e, S.Un): return paths(e.expr, name)
    if isinstance(e, S.Cast): return paths(e.expr, name)
    if isinstance(e, S.Len): return paths(e.expr, name, as_read=True)
    if isinstance(e, S.Index): return seq(paths(e.arr, name, as_read=True), paths(e.idx, name))
    if isinstance(e, S.Field): return paths(e.expr, name, as_read=True)
    if isinstance(e, S.RecLit):
        out = EMPTY
        for _, v in e.fields: out = seq(out, paths(v, name))
        return out
    if isinstance(e, S.With):
        out = paths(e.expr, name)
        for _, v in e.fields: out = seq(out, paths(v, name))
        return out
    if isinstance(e, S.Call):
        if getattr(e, "builtin", None) == "data": return paths(e.args[0], name, as_read=True)
        if getattr(e, "builtin", None) == "addr": return EMPTY
        if getattr(e, "builtin", None) == "set":
            a, i, v = e.args
            out = seq(paths(i, name), paths(v, name))
            return seq(out, paths(a, name))                  # the array is consumed last, after index and value
        if getattr(e, "builtin", None) == "serve": return EMPTY
        # concat and user calls consume whole-array arguments after all arguments are evaluated
        out, deferred = EMPTY, EMPTY
        for a in e.args:
            if isinstance(a, S.Var) and a.name == name: deferred = seq(deferred, paths(a, name))
            else: out = seq(out, paths(a, name))
        return seq(out, deferred)                            # whole-array arguments are consumed by the call
    if isinstance(e, S.Let): return seq(paths(e.value, name), paths(e.body, name))
    if isinstance(e, S.If): return seq(paths(e.cond, name), paths(e.then, name) + paths(e.els, name))
    if isinstance(e, (S.Sum, S.ArrC)):
        return seq(seq(paths(e.lo, name), paths(e.hi, name)), downgrade(paths(e.body, name)))
    if isinstance(e, S.Check): return seq(paths(e.pred, name), paths(e.body, name))
    if isinstance(e, S.Loop):
        out = EMPTY
        for x in e.inits: out = seq(out, paths(x, name))
        inner = paths(e.cond, name)
        for x in e.nexts: inner = seq(inner, paths(x, name))
        inner = seq(inner, paths(e.yld, name))
        return seq(out, downgrade(inner))
    raise TypeError(type(e))

def consume_plan(exprs: List[S.Node], name: str) -> Set[int]:
    """Node ids where `name` may be moved, or empty if the variable must stay borrowed everywhere."""
    out = EMPTY
    for e in exprs: out = seq(out, paths(e, name))
    if any(s.bad for s in out): return set()
    ids: Set[int] = set()
    for s in out: ids |= s.ids
    return ids

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
    def __init__(self, fns: List[S.Fn], fn_hashes: Dict[str, str], triple: str, assume: bool = True, vectorize: bool = True, ranges: bool = True):
        self.fns = fns; self.fn_hashes = fn_hashes; self.triple = triple
        self.assume = assume; self.vectorize = vectorize
        self.fn_map = {f.name: f for f in fns}
        self.vector_sums: List[dict] = []
        self.funcs: List[str] = []
        self.strings: Dict[str, str] = {}
        self.byte_consts: Dict[bytes, str] = {}
        self.par_regions: List[dict] = []
        self.fb: FuncBuilder = None
        self.mode = "par"; self.fn: S.Fn = None
        self.region_k = 0
        self.value_ranges = Ranges.analyze(fns) if ranges else {}
        self.bounded_remainders = []

    # ------------------------------------------------------------ module
    def string(self, s: str) -> str:
        if s not in self.strings: self.strings[s] = f"@.str.{len(self.strings) + 1}"
        return self.strings[s]
    def bytes_const(self, b: bytes) -> str:
        if b not in self.byte_consts: self.byte_consts[b] = f"@.bytes.{len(self.byte_consts) + 1}"
        return self.byte_consts[b]

    def program(self) -> str:
        for f in self.fns:
            if f.external: continue
            for mode in (("seq",) if f.effect or f.exported else ("par", "seq")):
                self.function(f, mode)
        self.main_wrapper()
        head = [f'target triple = "{self.triple}"', "",
                f"{ARR} = type {{ ptr, i64, i64 }}", "",
                "@ax_runtime_state = internal global [256 x i64] zeroinitializer, align 16",
                "declare double @llvm.sqrt.f64(double)", "declare void @llvm.assume(i1)",
                f"declare <{VZ.K} x double> @llvm.sqrt.v{VZ.K}f64(<{VZ.K} x double>)",
                f"declare i1 @llvm.vector.reduce.or.v{VZ.K}i1(<{VZ.K} x i1>)",
                f"declare i64 @llvm.vector.reduce.add.v{VZ.K}i64(<{VZ.K} x i64>)",
                f"declare double @llvm.vector.reduce.fadd.v{VZ.K}f64(double, <{VZ.K} x double>)",
                "declare void @llvm.memcpy.p0.p0.i64(ptr, ptr, i64, i1)", "declare i64 @llvm.ctlz.i64(i64, i1)", ""]
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
        return "\n".join(head) + "\n\n".join(self.funcs) + "\n"

    def fname(self, f: S.Fn, mode: str) -> str:
        if f.external or f.exported: return f"@{f.name}"
        if f.effect: mode = "seq"
        return f"@ax_{f.name}__{mode}"

    def function(self, f: S.Fn, mode: str):
        params = ", ".join(f"{lty(p.ty)} %p_{p.name}" for p in f.params)
        fb = FuncBuilder(f"; {f.name}  graph:{self.fn_hashes.get(f.name, '')[:16]}\n"
                         f"define {'internal ' if not f.exported else ''}{return_type(f.ret)} {self.fname(f, mode)}({params}) \"no-builtins\"")
        self.fb, self.mode, self.fn = fb, mode, f
        env: Dict[str, Slot] = {}
        for p in f.params:
            ty = lty(p.ty); ptr = fb.alloca(ty); v = Val(f"%p_{p.name}", ty); fb.store(v, ptr)
            s = Slot(ptr, ty, axty=p.ty)
            if isinstance(p.ty, S.TArr):
                s.own_ptr = fb.alloca("i64")
                fb.store(fb.ins(f"extractvalue {v}, 2", "i64"), s.own_ptr)   # the caller may have moved it to us
                s.consume = consume_plan([f.body], p.name)
                self.assume_array(v, p.ty)
            env[p.name] = s
        for s, carrier in f.size_binders:
            a = fb.load(ARR, env[carrier].ptr)
            n = fb.ins(f"extractvalue {a}, 1", "i64")
            ptr = fb.alloca("i64"); fb.store(n, ptr); env[s] = Slot(ptr, "i64", axty=S.I64)
        v, own = self.gen(f.body, env, par=(mode == "par"))
        self.free_scope([env[p.name] for p in f.params if isinstance(p.ty, S.TArr)], own if isinstance(f.ret, S.TArr) else None)
        if f.ret == S.UNIT: fb.emit("ret void")
        elif isinstance(f.ret, S.TArr):
            fb.emit(f"ret {self.with_own(v, own)}")
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
        fb.emit(f"call void @ax_runtime_init({envp})")
        n = len(m.params)
        ok = fb.ins(f"icmp eq i32 %argc, {n + 1}", "i1")
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
        r = fb.ins(f"call {lty(m.ret)} {self.fname(m, 'par')}({args})", lty(m.ret))
        if isinstance(m.ret, S.TArr):                      # main returned bytes: write them to stdout
            data = fb.ins(f"extractvalue {r}, 0", "ptr"); ln = fb.ins(f"extractvalue {r}, 1", "i64")
            fb.emit(f"call void @ax_print_bytes(ptr {data.name}, i64 {ln.name})")
            self.maybe_free(r, self.nz(fb.ins(f"extractvalue {r}, 2", "i64")), m.ret)
        else:
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

    def maybe_free(self, arr: Val, cond: Optional[Val], t: S.TArr):
        """Free arr's buffer if cond (i1) holds; cond None = never, 'true' = always."""
        fb = self.fb
        if cond is None: return
        if cond.name != "true":
            do, cont = fb.label("free"), fb.label("cont")
            fb.cbr(cond, do, cont); fb.block(do)
        data = fb.ins(f"extractvalue {arr}, 0", "ptr")
        ln = fb.ins(f"extractvalue {arr}, 1", "i64")
        by = fb.ins(f"mul i64 {ln.name}, {elem_size(t)}", "i64")
        fb.emit(f"call void @ax_free(ptr {data.name}, i64 {by.name})")
        if cond.name != "true":
            fb.br(cont); fb.block(cont)

    def free_scope(self, slots: List[Slot], result_own: Optional[Val]):
        """At scope exit free every array slot that still holds its buffer. If the scope's
        result is an array that might be a borrowed alias (own == 0), keep the buffers alive."""
        fb = self.fb
        guard = Val("true", "i1") if result_own is None else self.nz(result_own)
        for s in slots:
            if not s.own_ptr: continue
            flag = self.nz(fb.load("i64", s.own_ptr))
            self.maybe_free(fb.load(ARR, s.ptr), self.and_(flag, guard), s.axty)

    def new_array(self, t: S.TArr, length: Val) -> Val:
        fb = self.fb
        neg = fb.ins(f"icmp slt i64 {length.name}, 0", "i1")
        ln = fb.ins(f"select i1 {neg.name}, i64 0, i64 {length.name}", "i64")
        by = fb.ins(f"mul i64 {ln.name}, {elem_size(t)}", "i64")
        data = fb.ins(f"call ptr @ax_alloc(i64 {by.name})", "ptr")
        a = fb.ins(f"insertvalue {ARR} undef, ptr {data.name}, 0", ARR)
        a = fb.ins(f"insertvalue {a}, i64 {ln.name}, 1", ARR)
        a = fb.ins(f"insertvalue {a}, i64 1, 2", ARR)
        self.assume_array(a, t)
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
            return [(-1, lty(t.elem), fb.ins(f"getelementptr inbounds {lty(t.elem)}, ptr {data.name}, i64 {idx.name}", "ptr"))]
        out = []
        for k, fty, size, prefix in rec_layout(t.elem):
            if prefix:
                off = fb.ins(f"mul i64 {ln.name}, {prefix}", "i64")
                base = fb.ins(f"getelementptr inbounds i8, ptr {data.name}, i64 {off.name}", "ptr")
            else:
                base = data
            out.append((k, fty, fb.ins(f"getelementptr inbounds {fty}, ptr {base.name}, i64 {idx.name}", "ptr")))
        return out

    def load_elem(self, arr: Val, idx: Val, t: S.TArr, only_field: Optional[int] = None) -> Val:
        fb = self.fb
        ptrs = self.elem_ptrs(arr, idx, t)
        if not isinstance(t.elem, S.TRec): return fb.load(ptrs[0][1], ptrs[0][2].name)
        if only_field is not None:
            k, fty, p = next(x for x in ptrs if x[0] == only_field)
            return fb.load(fty, p.name)
        rec = Val("undef", lty(t.elem))
        for k, fty, p in ptrs:
            v = fb.load(fty, p.name)
            rec = fb.ins(f"insertvalue {rec}, {v}, {k}", lty(t.elem))
        return rec

    def store_elem(self, arr: Val, idx: Val, t: S.TArr, v: Val):
        fb = self.fb
        ptrs = self.elem_ptrs(arr, idx, t)
        if not isinstance(t.elem, S.TRec): fb.store(v, ptrs[0][2].name); return
        for k, fty, p in ptrs:
            fv = fb.ins(f"extractvalue {v}, {k}", fty)
            fb.store(fv, p.name)

    def add_vals(self, a: Val, b: Val, t) -> Val:
        fb = self.fb
        if t == S.F64: return fb.ins(f"fadd reassoc {a}, {b.name}", "double")   # Axon sums are order-free
        if t == S.I64: return fb.ins(f"add {a}, {b.name}", "i64")
        acc = a
        for k, (_, ft) in enumerate(t.fields):
            x = fb.ins(f"extractvalue {acc}, {k}", lty(ft)); y = fb.ins(f"extractvalue {b}, {k}", lty(ft))
            acc = fb.ins(f"insertvalue {acc}, {self.add_vals(x, y, ft)}, {k}", lty(t))
        return acc

    # ------------------------------------------------------------ expressions
    def bounded_remainder(self, e, a, b):
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
        ty = f"i{width}"
        if width == 32: value = fb.ins(f"trunc {a} to i32", ty)
        if lo < 0:
            negative = fb.ins(f"icmp slt {value}, 0", "i1")
            negated = fb.ins(f"sub {ty} 0, {value.name}", ty)
            value = fb.ins(f"select {negative}, {negated}, {value}", ty)
        for factor in (4, 2, 1):
            threshold = d * factor
            if limit < threshold: continue
            ge = fb.ins(f"icmp uge {value}, {threshold}", "i1")
            reduced = fb.ins(f"sub {value}, {threshold}", ty)
            value = fb.ins(f"select {ge}, {reduced}, {value}", ty)
        if negative is not None:
            negated = fb.ins(f"sub {ty} 0, {value.name}", ty)
            value = fb.ins(f"select {negative}, {negated}, {value}", ty)
        if width == 32: value = fb.ins(f"sext {value} to i64", "i64")
        self.bounded_remainders.append({'fn': self.fn.name, 'pos': list(e.pos), 'divisor': d, 'bounds': list(bounds), 'width': width})
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
            a = fb.ins(f"insertvalue {a}, i64 0, 2", ARR)           # static data: never owned
            return a, Val("0", "i64")
        if isinstance(e, S.Var):
            s = env[e.name]
            v = fb.load(s.ty, s.ptr)
            if s.ty != ARR: return v, None
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
                op = {"+": "fadd" if fl else "add", "-": "fsub" if fl else "sub", "*": "fmul" if fl else "mul",
                      "/": "fdiv" if fl else "sdiv", "%": "srem"}[e.op]
                return fb.ins(f"{op} {a}, {b.name}", a.ty), None
            if fl:
                op = {"<": "olt", "<=": "ole", ">": "ogt", ">=": "oge", "==": "oeq", "!=": "une"}[e.op]
                return fb.ins(f"fcmp {op} {a}, {b.name}", "i1"), None
            if a.ty == "i8":
                op = {"<": "ult", "<=": "ule", ">": "ugt", ">=": "uge", "==": "eq", "!=": "ne"}[e.op]
                return fb.ins(f"icmp {op} {a}, {b.name}", "i1"), None
            op = {"<": "slt", "<=": "sle", ">": "sgt", ">=": "sge", "==": "eq", "!=": "ne"}[e.op]
            return fb.ins(f"icmp {op} {a}, {b.name}", "i1"), None
        if isinstance(e, S.Un):
            a, _ = self.gen(e.expr, env, par)
            if e.op == "!": return fb.ins(f"xor i1 {a.name}, true", "i1"), None
            if a.ty == "double": return fb.ins(f"fneg {a}", "double"), None
            return fb.ins(f"sub i64 0, {a.name}", "i64"), None
        if isinstance(e, S.Field) and isinstance(e.expr, S.Index):
            a, own = self.gen(e.expr.arr, env, par)
            i, _ = self.gen(e.expr.idx, env, par)
            v = self.load_elem(a, i, e.expr.arr.ty, only_field=e.expr.arr.ty.elem.index(e.name))
            self.maybe_free(a, self.nz(own), e.expr.arr.ty)
            return v, None
        if isinstance(e, S.Index):
            a, own = self.gen(e.arr, env, par)
            i, _ = self.gen(e.idx, env, par)
            v = self.load_elem(a, i, e.arr.ty)
            self.maybe_free(a, self.nz(own), e.arr.ty)
            return v, None
        if isinstance(e, S.Len):
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
            if a.ty == "i8": return fb.ins(f"zext {a} to i64", "i64"), None
            return fb.ins(f"fptosi {a} to i64", "i64"), None
        if isinstance(e, S.RecLit):
            rt = e.ty; given = dict(e.fields)
            rec = Val("undef", lty(rt))
            for k, (fname, ft) in enumerate(rt.fields):
                v, _ = self.gen(given[fname], env, par)
                rec = fb.ins(f"insertvalue {rec}, {v}, {k}", lty(rt))
            return rec, None
        if isinstance(e, S.Field):
            r, _ = self.gen(e.expr, env, par)
            k = e.expr.ty.index(e.name)
            return fb.ins(f"extractvalue {r}, {k}", lty(e.ty)), None
        if isinstance(e, S.With):
            r, _ = self.gen(e.expr, env, par)
            rt = e.expr.ty
            for fname, fe in e.fields:
                v, _ = self.gen(fe, env, par)
                r = fb.ins(f"insertvalue {r}, {v}, {rt.index(fname)}", lty(rt))
            return r, None
        if isinstance(e, S.Call):
            return self.call(e, env, par)
        if isinstance(e, S.Let):
            v, own = self.gen(e.value, env, par)
            ptr = fb.alloca(v.ty); fb.store(v, ptr)
            slot = Slot(ptr, v.ty, axty=e.value.ty)
            if v.ty == ARR:
                slot.own_ptr = fb.alloca("i64"); fb.store(own, slot.own_ptr)
                slot.consume = consume_plan([e.body], e.name)
                self.assume_array(v, e.value.ty)
            env2 = dict(env); env2[e.name] = slot
            bv, bown = self.gen(e.body, env2, par)
            if v.ty == ARR:
                self.free_scope([slot], bown if isinstance(e.body.ty, S.TArr) else None)
            return bv, bown
        if isinstance(e, S.If):
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

    # ------------------------------------------------------------ calls and builtins
    def call(self, e: S.Call, env, par):
        fb = self.fb
        b = getattr(e, "builtin", None)
        if b == "null": return Val("null", "ptr"), None
        if b == "noop": return Val("0", "i8"), None
        if b == "runtime_state": return Val("@ax_runtime_state", "ptr"), None
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
        if b == "concat":
            parts = [self.gen(a, env, par) for a in e.args]
            lens = [Val(str(len(a.value)), "i64") if isinstance(a, S.Str) else fb.ins(f"extractvalue {v}, 1", "i64")
                    for (v, _), a in zip(parts, e.args)]
            total = lens[0]
            for l in lens[1:]: total = fb.ins(f"add i64 {total.name}, {l.name}", "i64")
            v0, own0 = parts[0]
            res = fb.alloca(ARR)
            # If we own the first buffer and its capacity class has room, append in place
            # (amortised O(appended bytes), like String::push_str); otherwise allocate and copy all.
            c0 = self.nz(own0)
            grow, fresh, join = fb.label("cat_grow"), fb.label("cat_fresh"), fb.label("cat_join")
            if c0 is None: fb.br(fresh)
            else:
                cap = self.capacity(lens[0])
                fits = fb.ins(f"icmp sle i64 {total.name}, {cap.name}", "i1")
                ok = self.and_(c0, fits)
                fb.cbr(ok, grow, fresh)
                fb.block(grow)
                dst = fb.ins(f"extractvalue {v0}, 0", "ptr")
                off = lens[0]
                for (v, own), l, a in list(zip(parts, lens, e.args))[1:]:
                    src = fb.ins(f"extractvalue {v}, 0", "ptr")
                    d = fb.ins(f"getelementptr inbounds i8, ptr {dst.name}, i64 {off.name}", "ptr")
                    fb.emit(f"call void @llvm.memcpy.p0.p0.i64(ptr {d.name}, ptr {src.name}, i64 {l.name}, i1 false)")
                    off = fb.ins(f"add i64 {off.name}, {l.name}", "i64")
                    self.maybe_free(v, self.nz(own), a.ty)
                grown = fb.ins(f"insertvalue {v0}, i64 {total.name}, 1", ARR)
                grown = fb.ins(f"insertvalue {grown}, i64 1, 2", ARR)
                fb.store(grown, res); fb.br(join)
            fb.block(fresh)
            out = self.new_array(e.ty, total)
            dst = fb.ins(f"extractvalue {out}, 0", "ptr")
            off = Val("0", "i64")
            for (v, own), l, a in zip(parts, lens, e.args):
                src = fb.ins(f"extractvalue {v}, 0", "ptr")
                d = fb.ins(f"getelementptr inbounds i8, ptr {dst.name}, i64 {off.name}", "ptr")
                fb.emit(f"call void @llvm.memcpy.p0.p0.i64(ptr {d.name}, ptr {src.name}, i64 {l.name}, i1 false)")
                off = fb.ins(f"add i64 {off.name}, {l.name}", "i64")
                self.maybe_free(v, self.nz(own), a.ty)
            fb.store(out, res); fb.br(join)
            fb.block(join)
            return fb.load(ARR, res), Val("1", "i64")
        if b == "set":
            t = e.args[0].ty
            a, own = self.gen(e.args[0], env, par)
            i, _ = self.gen(e.args[1], env, par)
            v, _ = self.gen(e.args[2], env, par)
            # in place when we own the buffer, else copy-on-write
            res = fb.alloca(ARR)
            c = self.nz(own)
            if c is None or c.name != "true":
                inplace, copy, join = fb.label("set_inplace"), fb.label("set_copy"), fb.label("set_join")
                if c is None: fb.br(copy)
                else: fb.cbr(c, inplace, copy)
                fb.block(copy)
                ln = fb.ins(f"extractvalue {a}, 1", "i64")
                fresh = self.new_array(t, ln)
                by = fb.ins(f"mul i64 {ln.name}, {elem_size(t)}", "i64")
                src = fb.ins(f"extractvalue {a}, 0", "ptr"); dst = fb.ins(f"extractvalue {fresh}, 0", "ptr")
                fb.emit(f"call void @llvm.memcpy.p0.p0.i64(ptr {dst.name}, ptr {src.name}, i64 {by.name}, i1 false)")
                self.store_elem(fresh, i, t, v)
                fb.store(fresh, res); fb.br(join)
                if c is not None:
                    fb.block(inplace)
                    self.store_elem(a, i, t, v)
                    fb.store(a, res); fb.br(join)
                fb.block(join)
            else:
                self.store_elem(a, i, t, v)
                fb.store(a, res)
            return fb.load(ARR, res), Val("1", "i64")
        callee = next(f for f in self.fns if f.name == e.name)
        vals = []
        for a in e.args:
            v, own = self.gen(a, env, par)
            if own is not None: v = self.with_own(v, own)          # the callee owns what arrives flagged
            vals.append(v)
        mode = "par" if (par and self.mode == "par") else "seq"
        args = ", ".join(str(v) for v in vals)
        rty = return_type(e.ty)
        signature = f" ({', '.join([lty(p.ty) for p in callee.params] + ['...'])})" if callee.variadic else ""
        call = f"call {rty}{signature} {self.fname(callee, mode)}({args})"
        if e.ty == S.UNIT:
            fb.emit(call); return Val("0", "i8"), None
        r = fb.ins(call, rty)
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
        i2 = fb.ins(f"add i64 {i.name}, 1", "i64"); fb.store(i2, ip)
        fb.br(cond); fb.block(end)

    def comprehension(self, e, env, par):
        fb = self.fb
        is_sum = isinstance(e, S.Sum)
        lo, _ = self.gen(e.lo, env, par)
        hi, _ = self.gen(e.hi, env, par)
        ety = lty(e.ty)
        if is_sum:
            acc = fb.alloca(ety); fb.store(Val(zero(e.ty), ety), acc)
            out = None
        else:
            ln = fb.ins(f"sub i64 {hi.name}, {lo.name}", "i64")
            out = self.new_array(e.ty, ln)
        vec = is_sum and self.vectorize and e.ty in (S.I64, S.F64) and VZ.eligible(e.body, self.fn_map)
        if vec: self.vector_sums.append({"fn": self.fn.name, "node": e.hash[:12], "pos": list(e.pos), "lanes": VZ.K})
        if not par:
            if vec:
                VZ.vector_sum_loop(self, fb, e, lo, hi, env, acc, self.fn_map)
                return fb.load(ety, acc), None
            def body(env2, i):
                v, _ = self.gen(e.body, env2, par=False)
                if is_sum:
                    fb.store(self.add_vals(fb.load(ety, acc), v, e.ty), acc)
                else:
                    k = fb.ins(f"sub i64 {i.name}, {lo.name}", "i64")
                    self.store_elem(out, k, e.ty, v)
            self.counted_loop(lo, hi, e.var, env, body)
            return (fb.load(ety, acc), None) if is_sum else (out, Val("1", "i64"))

        # ---- parallel: outline the body into @<fn>__regionK(ptr ctx, i64 chunk)
        self.par_regions.append({"fn": self.fn.name, "node": e.hash[:12], "pos": list(e.pos), "kind": "sum" if is_sum else "arr"})
        d = fb.ins(f"sub i64 {hi.name}, {lo.name}", "i64")
        pos = fb.ins(f"icmp sgt i64 {hi.name}, {lo.name}", "i1")
        n = fb.ins(f"select i1 {pos.name}, i64 {d.name}, i64 0", "i64")
        nchunks = fb.ins(f"call i64 @ax_chunks(i64 {n.name})", "i64")
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
        rname = f"@ax_{self.fn.name}__region{self.region_k}"
        fb.emit(f"call void @ax_par_for(i64 {nchunks.name}, ptr {rname}, ptr {ctx})")
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
                rb.store(self.add_vals(rb.load(ety, racc), v, e.ty), racc)
            else:
                k = rb.ins(f"sub i64 {i.name}, {rlo.name}", "i64")
                self.store_elem(rtgt, k, e.ty, v)
        if vec: VZ.vector_sum_loop(self, rb, e, clo, chi, renv, racc, self.fn_map)
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
                fb.store(self.add_vals(fb.load(ety, acc), fb.load(ety, p.name), e.ty), acc)
            self.counted_loop(Val("0", "i64"), nchunks, "%chunk", env, red)
            fb.emit(f"call void @ax_free(ptr {target.name}, i64 {pby.name})")
            return fb.load(ety, acc), None
        return out, Val("1", "i64")

    # ------------------------------------------------------------ loop
    def loop(self, e: S.Loop, env, par):
        fb = self.fb
        slots: List[Slot] = []
        env2 = dict(env)
        for name, init, t in zip(e.names, e.inits, e.state_tys):
            v, own = self.gen(init, env, par)
            ptr = fb.alloca(v.ty); fb.store(v, ptr)
            s = Slot(ptr, v.ty, axty=t)
            if v.ty == ARR:
                s.own_ptr = fb.alloca("i64"); fb.store(own, s.own_ptr)
                s.consume = consume_plan(list(e.nexts), name) | consume_plan([e.yld], name)
                self.assume_array(v, t)
            slots.append(s); env2[name] = s
        cond, body, exit_ = fb.label("loop_cond"), fb.label("loop_body"), fb.label("loop_exit")
        fb.br(cond); fb.block(cond)
        c, _ = self.gen(e.cond, env2, par)
        fb.cbr(c, body, exit_); fb.block(body)
        nexts = [self.gen(nx, env2, par) for nx in e.nexts]
        # Old buffers may be freed only when every array successor is fresh or moved (own != 0),
        # since a borrowed successor (own == 0) may alias an old buffer.
        all_fresh: Optional[Val] = Val("true", "i1")
        for (v, own), t in zip(nexts, e.state_tys):
            if isinstance(t, S.TArr): all_fresh = self.and_(all_fresh, self.nz(own))
        for s, (v, own), t in zip(slots, nexts, e.state_tys):
            if s.own_ptr and all_fresh is not None:
                self.maybe_free(fb.load(ARR, s.ptr), self.and_(self.nz(fb.load("i64", s.own_ptr)), all_fresh), t)
        for s, (v, own), t in zip(slots, nexts, e.state_tys):
            fb.store(v, s.ptr)
            if s.own_ptr:
                fb.store(own, s.own_ptr)
                self.assume_array(v, t)
        fb.br(cond); fb.block(exit_)
        yv, yown = self.gen(e.yld, env2, par)
        self.free_scope(slots, yown if isinstance(e.yld.ty, S.TArr) else None)
        return yv, yown
