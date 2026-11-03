"""Type checker with refinement obligations.

Every indexing, division, range, call precondition, loop invariant and return
refinement produces a proof obligation. The checker discharges it from the
facts in scope (parameter refinements, range bounds, branch conditions,
`check` nodes, let-definitions, loop invariants) plus *ambient facts*: what is
known about the result of each call, loop or branch expression from the
callee's return refinement or the loop's invariant. What it cannot prove is
reported as structured data, never silently turned into a runtime check.

Ambient facts hold only where their expression has been evaluated. Each one
records the path conditions of the environment it was produced in: the
conjuncts added by `with_fact` (branch conditions, a short-circuit's left
operand, loop and comprehension guards, `check` conditions). A goal may use an
ambient fact only when the goal's path conditions include all of the fact's.
Conditions are pure expressions over immutable bindings, so if they hold at
the goal they held when the earlier expression ran; and only facts produced
before the goal exist when it is proved. A fact from one branch therefore
never proves a goal in another, nor one where the branch's condition is unknown.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import itertools
from typing import Dict, List, Optional, Set, Tuple
from . import syntax as S
from .linear import Lin, Formula, and_, or_, cmp, neg, UNK, entails, formula_str

class CheckError(Exception):
    def __init__(self, errors): super().__init__("type errors"); self.errors = errors

@dataclass
class Binding:
    ty: object
    lin: Optional[Lin] = None      # meaning of an i64 variable, if linear
    formula: Optional[tuple] = None    # meaning of a let-bound bool, as a formula

_UNKNOWN = itertools.count(1)

def conjunct_keys(f: Formula) -> frozenset:
    """The conjuncts of a formula, flattened, as comparable keys. A condition the
    prover cannot express (a bool variable, a call) gets a key of its own that
    matches no other condition, not even its own negation."""
    if f[0] == "and": return frozenset().union(*[conjunct_keys(g) for g in f[1]])
    if f == ("true",): return frozenset()
    if f == UNK: return frozenset([("unknown", next(_UNKNOWN))])
    return frozenset([formula_str(f)])

@dataclass
class Env:
    vars: Dict[str, Binding]
    facts: Formula
    fn: S.Fn
    conds: frozenset = frozenset()     # path conditions (see the module docstring)
    def bind(self, name, ty, lin=None) -> "Env":
        v = dict(self.vars); v[name] = Binding(ty, lin)
        facts=self.facts
        if ty==S.I64:
            value=lin if lin is not None else Lin.var(name)
            facts=and_(facts,cmp('>=',value,Lin.num(-(1<<63))),cmp('<=',value,Lin.num((1<<63)-1)))
        elif isinstance(ty,S.TArr) and isinstance(ty.size,Lin):
            facts=and_(facts,cmp('>=',ty.size,Lin.num(0)),cmp('<=',ty.size,Lin.num((1<<63)-1)))
        return replace(self, vars=v, facts=facts)
    def with_fact(self, f: Formula) -> "Env":
        return replace(self, facts=and_(self.facts, f), conds=self.conds | conjunct_keys(f))
    def holds(self, f: Formula) -> "Env":
        """A fact true wherever this environment is (a refinement, a length's
        sign), as opposed to a branch condition: it adds no path condition."""
        return replace(self, facts=and_(self.facts, f))

def subst_lin(l: Lin, m: Dict[str, Lin]) -> Lin:
    out = Lin.num(l.const)
    for v, c in l.terms.items():
        out = out + (m[v].scale(c) if v in m else Lin({v: c}))
    return out

def free_vars(e: S.Node) -> Set[str]:
    out: Set[str] = set()
    def go(n):
        if isinstance(n, S.Var): out.add(n.name)
        for c in S.children(n): go(c)
    go(e); return out

BUILTINS = {"byte_read_le","byte_equal","count_trailing_zeros","byte_copy","byte_write_le","byte_slice","adopt","borrow_ref","ref_live","ref_release","ref_null","function", "function_null","set", "push", "sqrt", "serve", "serve_effect", "concat", 'wrapping_add','wrapping_sub','wrapping_mul','bit_and','bit_or','bit_xor','byte_swap64','mul_high','shift_left','shift_right','arithmetic_shift_right','allocation_stats_enabled'}

# Raw memory/FFI operations form the trusted systems boundary. They are only
# available in effect functions, never in refinements or parallel comprehensions.
SYSTEMS = {
    'atomic_load_i64':([S.PTR,S.I64],S.I64),
    'atomic_store_i64':([S.PTR,S.I64,S.I64],S.UNIT),
    'atomic_compare_exchange_i64':([S.PTR,S.I64,S.I64,S.I64],S.I64),
    # 32-bit ring indices shared with the kernel (io_uring head/tail words).
    'atomic_load_i32':([S.PTR,S.I64],S.I32),
    'atomic_store_i32':([S.PTR,S.I64,S.I32],S.UNIT),
    'counter_ticks':([],S.I64),
    'counter_frequency':([],S.I64),
    "syscall6": ([S.I64] * 7, S.I64),
    "fork_syscall": ([], S.I64),
    "spawn_thread": ([S.PTR, S.PTR], S.I64),
    "runtime_state": ([], S.PTR),
    "stack_alloc": ([S.I64], S.PTR),
    # An owned byte array of the given length whose contents are unspecified
    # until the caller has written every byte through data().
    "byte_uninit": ([S.I64], S.TArr(S.U8, "_")),
    "ptr_to_i64": ([S.PTR], S.I64),
    "ptr_from_i64": ([S.I64], S.PTR),
    "float_bits": ([S.F64], S.I64),
    "bits_float": ([S.I64], S.F64),
    "volatile_load_u8": ([S.PTR, S.I64], S.U8),
    "volatile_load_i64": ([S.PTR, S.I64], S.I64),
    "volatile_store_u8": ([S.PTR, S.I64, S.U8], S.UNIT),
    "volatile_store_i64": ([S.PTR, S.I64, S.I64], S.UNIT),
    "ptr_add": ([S.PTR, S.I64], S.PTR),
    **{f"load_{n}": ([S.PTR, S.I64], t) for n, t in
       (("u8", S.U8), ("i32", S.I32), ("i64", S.I64), ("ptr", S.PTR))},
    **{f"store_{n}": ([S.PTR, S.I64, t], S.UNIT) for n, t in
       (("u8", S.U8), ("i32", S.I32), ("i64", S.I64), ("ptr", S.PTR))},
    # x86-64 AES-NI and PCLMULQDQ. A 128-bit block is two i64 halves, low
    # (bytes 0-7) and high (bytes 8-15), little-endian. aes_hardware() says
    # whether this CPU has them; the others are valid only when it is true.
    # block_xor_low/high is the xor of two blocks, kept in a vector register.
    "aes_hardware": ([], S.BOOL),
    **{name: ([S.I64] * 4, S.I64) for name in ("aes_round_low", "aes_round_high", "aes_final_round_low", "aes_final_round_high", "block_xor_low", "block_xor_high")},
    **{name: ([S.I64, S.I64], S.I64) for name in ("carryless_mul_low", "carryless_mul_high")},
    "invoke_region": ([S.PTR, S.PTR, S.I64], S.UNIT),
    "invoke_finalizer": ([S.PTR,S.PTR],S.UNIT),
    "handler_call": ([S.PTR, S.PTR, S.I64], S.TArr(S.U8, "_")),
}

class Checker:
    def __init__(self, prog: S.Program, require_main=True, precompiled=None):
        from .elaborate import prepare
        prepare(prog)
        self.prog = prog
        self.require_main=require_main
        self.types: Dict[str, S.TRec] = {}
        self.fns = {f.name: f for f in prog.fns}
        self.order = prog.fns
        self.obligations: List[dict] = []
        self.errors: List[dict] = []
        self.runtime_checks = 0
        self.function_runtime_checks = {}
        self.ambient: List[Tuple[Formula, frozenset]] = []
        self._k = 0
        self.pure_context = 0
        self.field_sizes = {}
        self.field_symbols = {}
        # Bindings named by id() in field_sizes/field_symbols stay alive, so a
        # later binding can never reuse an address and inherit their symbols.
        self.pinned_bindings = {}
        self.precompiled = precompiled or {}
        for fn in self.order:fn.precompiled = fn.name in self.precompiled

    def require_effect(self, e, env, capabilities=()):
        if not env.fn.effect or self.pure_context:
            self.err(f"{e.name} requires an effect function and cannot run in a refinement or comprehension", e, env.fn)
        self.require_capabilities(capabilities, e, env)

    def require_capabilities(self, needed, node, env):
        from .trust import within, RUNTIME, STDLIB
        source = getattr(env.fn, 'source', '')
        # Shipped runtime/library implementations form the audited syscall boundary.
        trusted = within(source, RUNTIME) or within(source, STDLIB)
        declared = env.fn.capabilities
        if declared is not None and not trusted and not set(needed) <= set(declared):
            self.err('missing effect capabilities: '+', '.join(sorted(set(needed)-set(declared))), node, env.fn)

    def predicate(self, e, env):
        self.pure_context += 1
        try: return self.infer(e, env)
        finally: self.pure_context -= 1

    def plain_predicate(self, e) -> bool:
        """Comparisons over variables, lengths, fields and proven +, -, constant *."""
        if isinstance(e, (S.BoolLit, S.Num, S.Var)): return True
        if isinstance(e, S.Len): return self.plain_predicate(e.expr) if isinstance(e.expr, (S.Var, S.Field)) else False
        if isinstance(e, S.Field): return isinstance(e.expr, (S.Var, S.Field)) and self.plain_predicate(e.expr)
        if isinstance(e, S.Un):
            return (e.op == '!' or e.op == '-' and getattr(e, 'arithmetic_proven', False)) and self.plain_predicate(e.expr)
        if isinstance(e, S.Bin):
            if e.op in ('+', '-', '*') and not getattr(e, 'arithmetic_proven', False): return False
            if e.op not in ('+', '-', '*', '&&', '||', '<', '<=', '>', '>=', '==', '!='): return False
            return self.plain_predicate(e.left) and self.plain_predicate(e.right)
        return False

    # ------------------------------------------------------------ helpers
    def sym(self, kind: str) -> str:
        self._k += 1; return f"⟨{kind}#{self._k}⟩"

    def err(self, msg, node, fn):
        self.errors.append({"kind": "type", "fn": getattr(fn,'display_name',fn.name) if fn else "-", "file": getattr(fn, "source", None), "pos": list(getattr(node, "pos", (0, 0))), "msg": msg})

    def resolve(self, t, node, fn):
        if isinstance(t,S.TRef):
            if not isinstance(t.resource,S.TRec) or t.resource.name not in {td.name for td in self.prog.types if td.resource_drop}:self.err('Ref requires a resource type',node,fn);return None
            return S.TRef(S.TRec(t.resource.name,()))
        if isinstance(t,S.TFn):
            if any(isinstance(p,S.TArr) and p.size!='_' for p in t.params):self.err('function-value signatures use independent existential array sizes _',node,fn)
            if t.capabilities is not None and not set(t.capabilities)<={'fs','net','env','time','process','unsafe'}:self.err('unknown function-value effect capability',node,fn)
            return S.TFn(tuple(self.resolve(p,node,fn) for p in t.params),self.resolve(t.ret,node,fn),t.capabilities)
        if isinstance(t, S.TRec):
            if t.name not in self.types: self.err(f"unknown type {t.name}", node, fn); return None
            return self.types[t.name]
        if isinstance(t, S.TArr):
            el = self.resolve(t.elem, node, fn)
            return None if el is None else S.TArr(el, t.size)
        return t

    def prove(self, env: Env, goal: Formula, diagnostics=False):
        # A counterexample search is costly and most first attempts that fail
        # are then proven with ambient facts; search only for goals that stay
        # unproven, from the facts whose attempt the counterexample describes.
        status, _ = entails(env.facts, goal, diagnostics=False)
        visible = [f for f, conds in self.ambient if conds <= env.conds] if status != "proven" else []
        described = env.facts
        if visible:
            st2, _ = entails(and_(env.facts, *visible), goal, diagnostics=False)
            if st2 == "proven": return st2, None
            if st2 == "unproven": described = and_(env.facts, *visible)
        cex = entails(described, goal, diagnostics=True)[1] if diagnostics and status != "proven" else None
        return status, cex

    def oblige(self, env: Env, kind: str, goal: Formula, node: S.Node, source: str, fixes: List[str]):
        status, cex = self.prove(env, goal, diagnostics=True)
        rec = {"id": len(self.obligations) + 1, "fn": env.fn.name, "node": node.hash[:12],
               "pos": list(node.pos), "kind": kind, "goal": source, "normalised": formula_str(goal),
               "status": status}
        if status != "proven":
            rec["counterexample"] = cex
            rec["fixes"] = fixes
        self.obligations.append(rec)

    def same(self, a, b, env: Env) -> bool:
        if isinstance(a,S.TRef) and isinstance(b,S.TRef):return a.resource.name==b.resource.name
        if isinstance(a,S.TFn) and isinstance(b,S.TFn):
            return a.capabilities==b.capabilities and len(a.params)==len(b.params) and all(self.same(x,y,env) for x,y in zip(a.params,b.params)) and self.same(a.ret,b.ret,env)
        if isinstance(a, S.TArr) and isinstance(b, S.TArr):
            if not self.same(a.elem, b.elem, env): return False
            if a.size == "_" or b.size == "_": return True
            if a.size == b.size: return True
            st, _ = self.prove(env, cmp("==", a.size, b.size))
            return st == "proven"
        if isinstance(a, S.TRec) and isinstance(b, S.TRec): return a.name == b.name
        return type(a) is type(b) and not isinstance(a, (S.TArr, S.TRec))

    def numeric_record(self, t) -> bool:
        return isinstance(t, S.TRec) and all(ft in (S.I64, S.F64) for _, ft in t.fields)

    # ------------------------------------------------------------ linear views
    def to_lin(self, e: S.Node, env: Env) -> Lin:
        if isinstance(e, S.Num): return Lin.num(e.value)
        if isinstance(e, S.Var):
            b = env.vars.get(e.name)
            if b and b.lin is not None: return b.lin
            return Lin.var(e.name)
        if isinstance(e, S.Bin) and e.op in ("+", "-"):
            a, b = self.to_lin(e.left, env), self.to_lin(e.right, env)
            return a + b if e.op == "+" else a - b
        if isinstance(e, S.Bin) and e.op == "*":
            a, b = self.to_lin(e.left, env), self.to_lin(e.right, env)
            if a.is_const(): return b.scale(a.const)
            if b.is_const(): return a.scale(b.const)
        if isinstance(e, S.Un) and e.op == "-": return self.to_lin(e.expr, env).scale(-1)
        if isinstance(e, S.Len):
            t = e.expr.ty
            if isinstance(t, S.TArr) and isinstance(t.size, Lin): return t.size
            if isinstance(t, S.TArr):
                if not getattr(e, "lin_sym", None): e.lin_sym = self.sym("len")
                return Lin.var(e.lin_sym)
        if isinstance(e, S.Let):
            return self.to_lin(e.body, env.bind(e.name, e.value.ty, self.to_lin(e.value, env) if e.value.ty == S.I64 else None))
        sym = getattr(e, "lin_sym", None)
        if sym: return Lin.var(sym)
        return Lin.var("⟨" + S.show(e) + "⟩")        # opaque term keyed by its text

    def to_formula(self, e: S.Node, env: Env) -> Formula:
        if isinstance(e, S.BoolLit): return ("true",) if e.value else ("false",)
        if isinstance(e, S.Var):
            b = env.vars.get(e.name)
            if b is not None and b.formula is not None: return b.formula
        if isinstance(e, S.Bin):
            if e.op == "&&": return and_(self.to_formula(e.left, env), self.to_formula(e.right, env))
            if e.op == "||": return or_(self.to_formula(e.left, env), self.to_formula(e.right, env))
            if e.op in ("<", "<=", ">", ">=", "==", "!=") and e.left.ty == S.I64:
                return cmp(e.op, self.to_lin(e.left, env), self.to_lin(e.right, env))
        if isinstance(e, S.Un) and e.op == "!": return neg(self.to_formula(e.expr, env))
        return UNK

    def result_facts(self, e: S.Node, sym: Lin, env: Env) -> Formula:
        """What is known about the i64 value of `e`, named `sym`."""
        if isinstance(e, S.Bin) and e.op == "*" and getattr(e, "lin_sym", None):
            a, b = self.to_lin(e.left, env), self.to_lin(e.right, env)
            facts = []
            if self.prove(env, cmp(">=", a, Lin.num(0)))[0] == "proven" and self.prove(env, cmp(">=", b, Lin.num(0)))[0] == "proven":
                facts.append(cmp(">=", sym, Lin.num(0)))
                if self.prove(env, cmp(">=", a, Lin.num(1)))[0] == "proven": facts.append(cmp(">=", sym, b))
                if self.prove(env, cmp(">=", b, Lin.num(1)))[0] == "proven": facts.append(cmp(">=", sym, a))
            return and_(*facts)
        if isinstance(e, S.Bin) and e.op in ("/", "%") and getattr(e, "lin_sym", None):
            # truncating division by a positive constant b:  b*q <= a < b*q + b  when a >= 0, and q >= 0;
            # remainder:  0 <= r < b  when a >= 0.  (General a: |r| < b and q has a's sign.)
            a = self.to_lin(e.left, env)
            if not isinstance(e.right, S.Num) or e.right.value <= 0: return ("true",)
            b = e.right.value
            a_nonneg = self.prove(env, cmp(">=", a, Lin.num(0)))[0] == "proven"
            if e.op == "/":
                facts = [cmp("<=", sym.scale(b), a), cmp("<", a, sym.scale(b) + Lin.num(b))] if a_nonneg else []
                if a_nonneg: facts.append(cmp(">=", sym, Lin.num(0)))
                return and_(*facts)
            facts = [cmp("<", sym, Lin.num(b)), cmp(">", sym, Lin.num(-b))]
            if a_nonneg: facts.append(cmp(">=", sym, Lin.num(0)))
            return and_(*facts)
        if isinstance(e, S.Sum) and e.ty == S.I64 and getattr(e, "body_env", None) is not None:
            bl = self.to_lin(e.body, e.body_env)
            span = self.to_lin(e.hi, env) - self.to_lin(e.lo, env)
            facts = []
            for c in (0, 1, 2, 3, 4, 5, 6, 8, 10, 16):
                if self.prove(e.body_env, cmp(">=", bl, Lin.num(c)))[0] == "proven": facts.append(cmp(">=", sym, span.scale(c)))
                else: break
            for c in (0, 1, 2, 3, 4, 5, 6, 8, 10, 16, 100, 1000):
                if self.prove(e.body_env, cmp("<=", bl, Lin.num(c)))[0] == "proven": facts.append(cmp("<=", sym, span.scale(c))); break
            if facts and self.prove(env, cmp(">=", span, Lin.num(0)))[0] != "proven": facts = []
            return and_(*facts)
        if isinstance(e, (S.Num, S.Var, S.Bin, S.Un, S.Len)):
            l = self.to_lin(e, env)
            return ("true",) if l == sym else cmp("==", sym, l)
        if isinstance(e, S.Loop):
            if isinstance(e.yld, S.Var) and e.yld.name in e.names and e.annots:
                k = e.names.index(e.yld.name); ann = e.annots[k]
                if ann is not None:
                    others = set(e.names) - {e.yld.name}
                    sub = env.bind(e.yld.name, S.I64, sym)
                    return and_(*[self.to_formula(q, sub) for q in ann[1] if not (free_vars(q) & others)])
            return ("true",)
        if isinstance(e, S.If):
            c = self.to_formula(e.cond, env)
            a, b = self.result_facts(e.then, sym, env), self.result_facts(e.els, sym, env)
            ta, tb = getattr(e, "then_facts", []), getattr(e, "els_facts", [])
            if a == ("true",) and b == ("true",) and not ta and not tb: return ("true",)
            return or_(and_(c, a, *ta), and_(neg(c), b, *tb))
        if isinstance(e, S.Let):
            return self.result_facts(e.body, sym, env.bind(e.name, e.value.ty, self.to_lin(e.value, env) if e.value.ty == S.I64 else None))
        if isinstance(e, S.Check):
            return self.result_facts(e.body, sym, env)
        if isinstance(e, S.Call) and getattr(e, "builtin", None) == "bit_and" and len(e.args) == 2:
            # x & c for a constant c >= 0 keeps only bits of c: 0 <= x & c <= c,
            # whatever x is. The fact names only this node's own value.
            masks = [a.value for a in e.args if isinstance(a, S.Num) and a.value >= 0]
            if not masks: return ("true",)
            return and_(cmp(">=", sym, Lin.num(0)), cmp("<=", sym, Lin.num(min(masks))))
        if isinstance(e, S.Call) and e.name in self.fns:
            callee = self.fns[e.name]
            if not callee.ret_preds or callee.ret != S.I64: return ("true",)
            sub, _ = self.call_subst(callee, e.args, env)
            sub = sub.bind("result", S.I64, sym)
            return and_(*[self.to_formula(q, sub) for q in callee.ret_preds])
        return ("true",)

    # ------------------------------------------------------------ program
    def run(self):
        allowed = {'fs','net','env','time','process','unsafe'}
        for function in self.order:
            if function.capabilities is not None and not set(function.capabilities) <= allowed:
                self.err('unknown effect capabilities: '+', '.join(sorted(set(function.capabilities)-allowed)), function, function)
        self.required_caps = {fn.name: ({'unsafe'} if fn.external else set(fn.capabilities or ())) for fn in self.order}
        self.required_caps.update({name:set(caps) for name,caps in self.precompiled.items()})
        def summary(node, fixed, names):
            """A body's capabilities are its own plus those required by the
            functions it names; collect both once, then iterate on names."""
            if isinstance(node, S.Call):
                if node.name in SYSTEMS and node.name not in ('float_bits','bits_float','aes_hardware') or node.name in ('addr','data','view'): fixed.add('unsafe')
                signature=getattr(node,'indirect_signature',None)
                if signature is not None:fixed |= set(signature.capabilities or ())
                else:names.append(node.name)
                if node.name == 'serve_effect' and len(node.args)==2 and isinstance(node.args[1], S.Var):
                    names.append(node.args[1].name); fixed.add('net')
            for child in S.children(node): summary(child, fixed, names)
            return fixed, names
        summaries = {}
        def effects(node):
            # Indirect-call signatures appear during checking: summaries are
            # taken per phase (cleared below once bodies are checked).
            if id(node) not in summaries: summaries[id(node)] = summary(node, set(), [])
            fixed, names = summaries[id(node)]
            out = set(fixed)
            for name in names: out |= self.required_caps.get(name,set())
            return out
        for _ in range(len(self.order)+1):
            changed = False
            for function in self.order:
                if function.precompiled:continue
                if function.capabilities is not None: continue
                found = effects(function.body)
                if not found <= self.required_caps[function.name]:
                    self.required_caps[function.name] |= found; changed = True
            if not changed: break
        names = set()
        for f in self.order:
            if f.name in names: self.err(f"duplicate function {f.name}", f, f)
            names.add(f.name)
            if f.name == "main" and (f.external or f.exported):
                self.err("main must be a Neo entry point without extern/export", f, f)
            if f.name in BUILTINS or f.name in SYSTEMS or f.name in ("null", "noop", "addr", "data", "view"):
                self.err(f"reserved builtin name {f.name}", f, f)
        declarations = {}
        for td in self.prog.types:
            if td.name in declarations: self.err(f"duplicate type {td.name}", td, None)
            declarations[td.name] = td
        self.sealed_owners = {td.name: getattr(td, 'source', None) for td in self.prog.types if td.sealed}
        self.type_display={td.name:getattr(td,'display_name',td.name) for td in self.prog.types}
        self.enum_types = {td.name for td in self.prog.types if hasattr(td,'variant_layout')}
        resolving = set()
        def field_type(t, owner):
            if isinstance(t,S.TRef):return self.resolve(t,owner,None)
            if isinstance(t,S.TFn):
                if t.capabilities is not None and not set(t.capabilities)<={'fs','net','env','time','process','unsafe'}:self.err('unknown function-value effect capability',owner,None)
                return S.TFn(tuple(field_type(x,owner) for x in t.params),field_type(t.ret,owner),t.capabilities)
            if isinstance(t, S.TRec): return record(t.name, owner)
            if isinstance(t, S.TArr):
                if t.size != '_': self.err('record array fields use existential size _', owner, None)
                return S.TArr(field_type(t.elem, owner), '_')
            return t
        def record(name, owner):
            if name in self.types: return self.types[name]
            if name in resolving:
                self.err(f'recursive value type {name} is not finite', owner, None); return S.I64
            td = declarations.get(name)
            if td is None: self.err(f'unknown type {name}', owner, None); return S.I64
            resolving.add(name)
            if len(dict(td.fields)) != len(td.fields): self.err(f'duplicate fields in {name}', td, None)
            result = S.TRec(name, tuple((n, field_type(t, td)) for n,t in td.fields))
            resolving.remove(name); self.types[name] = result
            return result
        for td in self.prog.types: record(td.name, td)
        if self.require_main and "main" not in self.fns:
            self.errors.append({"kind": "type", "fn": "-", "pos": [0, 0], "msg": "no `main` function"})
        for f in self.order:
            f._env = self.fn_env(f)
        if self.errors: raise CheckError(self.errors)
        # Type signatures before bodies, so a forward call sees the same return
        # refinement facts as a call to an earlier declaration.
        for f in self.order:
            self.ambient = []
            for p in f.params:
                for q in p.preds:
                    if self.predicate(q, f._env) != S.BOOL: self.err("refinement must be bool", q, f)
            renv = f._env.bind("result", f.ret, Lin.var("result") if f.ret == S.I64 else None)
            for q in f.ret_preds:
                if self.predicate(q, renv) != S.BOOL: self.err("return refinement must be bool", q, f)
        if self.errors: raise CheckError(self.errors)
        # Dependency bodies were checked when their content-addressed native
        # artifact was produced. Signatures and all application bodies are
        # still checked here; changed sources invalidate that artifact.
        self.order = [f for f in self.order if not f.precompiled]
        for f in self.order:
            before_checks=self.runtime_checks
            self.check_fn(f)
            self.function_runtime_checks[f.name]=self.runtime_checks-before_checks
        # Infer indirect-call effects after expression types are known, then
        # recheck callers so unannotated helpers cannot hide callback effects.
        summaries.clear()
        for _ in range(len(self.order)+1):
            changed=False
            for function in self.order:
                if function.capabilities is not None:continue
                found=effects(function.body)
                if not found<=self.required_caps[function.name]:self.required_caps[function.name]|=found;changed=True
            if not changed:break
        for function in self.order:
            self.require_capabilities(effects(function.body),function.body,function._env)
        if not self.errors:
            from .resources import validate
            validate(self)
        if self.errors: raise CheckError(self.errors)

    def fn_env(self, f: S.Fn) -> Env:
        env = Env({}, ("true",), f)
        f.size_binders = []          # (size var, array param that carries it): implicit i64 params
        for p in f.params:
            p.ty = self.resolve(p.ty, p, f)
            if p.ty is None: continue
            if isinstance(p.ty, S.TArr): continue
            env = env.bind(p.name, p.ty, Lin.var(p.name) if p.ty == S.I64 else None)
        for p in f.params:
            if not isinstance(p.ty, S.TArr): continue
            s = p.ty.size
            if not isinstance(s, str): self.err("array parameter sizes must be variables", p, f); continue
            if s=='_':s=self.sym('size')
            if s in env.vars:
                if env.vars[s].ty != S.I64: self.err(f"size variable {s} must be i64", p, f)
                size = env.vars[s].lin
            else:
                size = Lin.var(s)
                env = env.bind(s, S.I64, size).holds(cmp(">=", size, Lin.num(0)))
                f.size_binders.append((s, p.name))
            p.ty = S.TArr(p.ty.elem, size)
            env = env.bind(p.name, p.ty)
        f.ret = self.resolve(f.ret, f, f)
        if isinstance(f.ret, S.TArr):
            s = f.ret.size
            if s == "_":
                pass                                   # existential: each call site gets a fresh size
            elif isinstance(s, str):
                if s not in env.vars or env.vars[s].ty != S.I64:
                    self.err(f"return size variable {s} is not bound by a parameter", f, f)
                else:
                    f.ret = S.TArr(f.ret.elem, env.vars[s].lin)
            else:                                      # size expression over the parameters
                if self.infer(s, env) != S.I64: self.err("return size expression must be i64", s, f)
                l = self.to_lin(s, env)
                if any(v.startswith("⟨") for v in l.vars()): self.err("return size expression must be linear in the parameters", s, f)
                f.ret = S.TArr(f.ret.elem, l)
        return env

    def check_fn(self, f: S.Fn):
        env = f._env
        self.ambient = []
        for p in f.params:
            if p.borrowed and (not isinstance(p.ty,(S.TArr,S.TRec)) or f.external or f.exported):
                self.err('borrow parameters require an internal array or record type',p,f)
        if f.external:
            allowed = (S.I64, S.I32, S.F64, S.PTR, S.UNIT)
            if f.ret not in allowed or any(p.ty not in allowed[:-1] or p.preds for p in f.params) or f.ret_preds:
                self.err("extern signatures support unrefined i64, i32, f64, ptr and unit returns", f, f)
            return
        if f.exported and (f.ret not in (S.I64, S.I32, S.F64, S.PTR, S.UNIT) or
                           any(p.ty not in (S.I64, S.I32, S.F64, S.PTR) for p in f.params)):
            self.err("export signatures must use ABI scalar types", f, f)
        for p in f.params:
            for q in p.preds:
                t = self.predicate(q, env)
                if t != S.BOOL: self.err("refinement must be bool", q, f)
                env = env.holds(self.to_formula(q, env))
        if f.name == "main":
            for p in f.params:
                if p.ty != S.I64: self.err("main parameters must be i64 (parsed from argv)", p, f)
            if f.ret not in (S.I64, S.F64, S.UNIT) and not (isinstance(f.ret, S.TArr) and f.ret.elem == S.U8):
                self.err("main must return i64, f64 or Arr u8 (written to stdout)", f, f)
            for p in f.params:
                for q in p.preds:
                    self.obligations.append({"id": len(self.obligations) + 1, "fn": "main", "node": q.hash[:12],
                        "pos": list(q.pos), "kind": "precondition", "goal": S.show(q),
                        "status": "checked", "note": "program boundary: verified at argv parse"})
                    self.runtime_checks += 1
        t = self.infer(f.body, env)
        if t is not None and not self.same(t, f.ret, env):
            self.err(f"body has type {t}, declared {f.ret}", f.body, f)
        if f.ret_preds and t is not None:
            renv = env.bind("result", f.ret, self.to_lin(f.body, env) if f.ret == S.I64 else None)
            for q in f.ret_preds:
                if self.predicate(q, renv) != S.BOOL: self.err("return refinement must be bool", q, f); continue
                self.oblige(env, "postcondition", self.to_formula(q, renv), q, S.show(q),
                            ["make the body's shape expose the fact (loop invariant on the yielded state, if/else, let)",
                             "weaken the return refinement", "insert `check … in` before returning"])

    # ------------------------------------------------------------ expressions
    def infer(self, e: S.Node, env: Env):
        t = self._infer(e, env)
        e.ty = t
        arithmetic=isinstance(e,S.Bin) and (e.op in ('+','-') or e.op=='*' and (isinstance(e.left,S.Num) or isinstance(e.right,S.Num))) or isinstance(e,S.Un) and e.op=='-'
        if t==S.I64 and arithmetic:
            value=self.to_lin(e,env)
            goal=and_(cmp('>=',value,Lin.num(-(1<<63))),cmp('<=',value,Lin.num((1<<63)-1)))
            # Only lexical facts are valid on every path reaching this operation.
            # Ambient results can originate in a different conditional branch.
            e.arithmetic_proven=entails(env.facts,goal,diagnostics=False)[0]=='proven'
            # Code generation retries with interval bounds of the operands,
            # which hold for every evaluation of those exact nodes.
            if not e.arithmetic_proven:
                operands=[e.expr] if isinstance(e,S.Un) else [e.left,e.right]
                e.arithmetic_context=(env.facts,goal,[(x,self.to_lin(x,env)) for x in operands if x.ty==S.I64])
        is_prod = isinstance(e, S.Bin) and e.op == "*" and not (isinstance(e.left, S.Num) or isinstance(e.right, S.Num))
        is_divmod = isinstance(e, S.Bin) and e.op in ("/", "%") and t == S.I64
        if t == S.I64 and (is_prod or is_divmod or isinstance(e, (S.Call, S.Loop, S.If, S.Index, S.Cast, S.Sum, S.Field, S.Check))):
            key = self.field_key(e, env) if isinstance(e, S.Field) else None
            if key is not None:
                # Every read of one field of one immutable binding is the same
                # value, like a variable: a guard on r.pos proves r.pos indexes.
                if key not in self.field_symbols: self.field_symbols[key] = self.sym("field")
                e.lin_sym = self.field_symbols[key]
                return t
            e.lin_sym = self.sym("mul" if is_prod else ("div" if is_divmod else type(e).__name__.lower()))
            f = self.result_facts(e, Lin.var(e.lin_sym), env)
            if f != ("true",): self.ambient.append((f, env.conds))
        return t

    def field_key(self, e: S.Field, env: Env):
        """(binding, field path) of r.a.b over a lexical binding r, else None."""
        path = []; base = e
        while isinstance(base, S.Field): path.append(base.name); base = base.expr
        binding = env.vars.get(base.name) if isinstance(base, S.Var) else None
        if binding is None: return None
        self.pinned_bindings[id(binding)] = binding
        return (id(binding), tuple(reversed(path)))

    def call_subst(self, callee: S.Fn, args: List[S.Node], env: Env) -> Tuple[Env, Dict[str, Lin]]:
        """Environment mapping the callee's parameters and size variables to the caller's terms."""
        sizes: Dict[str, Lin] = {}
        sub = Env({}, env.facts, env.fn, env.conds)
        for p, a in zip(callee.params, args):
            if p.ty == S.I64: sizes[p.name] = self.to_lin(a, env)
        for p, a in zip(callee.params, args):
            at = a.ty
            if isinstance(p.ty, S.TArr) and isinstance(at, S.TArr):
                s = str(p.ty.size)
                if s not in sizes: sizes[s] = self.size_lin(at)
                sub = sub.bind(p.name, S.TArr(at.elem, self.size_lin(at)))
            else:
                sub = sub.bind(p.name, at, sizes.get(p.name))
        for s, l in sizes.items():
            if s not in sub.vars: sub = sub.bind(s, S.I64, l)
        return sub, sizes

    def _infer(self, e: S.Node, env: Env):
        f = env.fn
        if isinstance(e, S.Num):
            if not -(1<<63)<=e.value<(1<<63): self.err('integer literal outside i64',e,f);return None
            return S.I64
        if isinstance(e, S.Flt): return S.F64
        if isinstance(e, S.BoolLit): return S.BOOL
        if isinstance(e, S.Str): return S.TArr(S.U8, Lin.num(len(e.value)))
        if isinstance(e, S.Byte): return S.U8
        if isinstance(e, S.Var):
            b = env.vars.get(e.name)
            if b is None: self.err(f"unbound variable {e.name}", e, f); return None
            return b.ty
        if isinstance(e, S.Bin):
            lt = self.infer(e.left, env)
            if e.op in ("&&", "||") and lt == S.BOOL:
                lf = self.to_formula(e.left, env)
                rt = self.infer(e.right, env.with_fact(lf if e.op == "&&" else neg(lf)))
            else:
                rt = self.infer(e.right, env)
            if lt is None or rt is None: return None
            if e.op in ("+", "-", "*", "/", "%"):
                if lt != rt or lt not in (S.I64, S.F64) or (e.op == "%" and lt != S.I64):
                    self.err(f"operator {e.op} on {lt} and {rt}", e, f); return None
                if e.op in ("/", "%") and lt == S.I64:
                    d = self.to_lin(e.right, env)
                    self.oblige(env, "division", cmp("!=", d, Lin.num(0)), e, f"{S.show(e.right)} != 0",
                                [f"check {S.show(e.right)} != 0 in …", "refine the divisor's parameter"])
                return lt
            if e.op in ("<", "<=", ">", ">="):
                if lt != rt or lt not in (S.I64, S.I32, S.F64, S.U8, S.U16): self.err(f"comparison {e.op} on {lt} and {rt}", e, f); return None
                return S.BOOL
            if e.op in ("==", "!="):
                if lt != rt or isinstance(lt, (S.TArr, S.TRec)): self.err(f"equality on {lt} and {rt}", e, f); return None
                return S.BOOL
            if e.op in ("&&", "||"):
                if lt != S.BOOL or rt != S.BOOL: self.err(f"{e.op} needs bool operands", e, f); return None
                return S.BOOL
        if isinstance(e, S.Un):
            if e.op == '-' and isinstance(e.expr,S.Num) and e.expr.value == 1<<63:
                e.expr.ty=S.I64;return S.I64
            t = self.infer(e.expr, env)
            if e.op == "-" and t in (S.I64, S.F64): return t
            if e.op == "!" and t == S.BOOL: return S.BOOL
            if t is not None: self.err(f"unary {e.op} on {t}", e, f)
            return None
        if isinstance(e, S.Index):
            at, it = self.infer(e.arr, env), self.infer(e.idx, env)
            if not isinstance(at, S.TArr): self.err("indexing a non-array", e, f); return None
            if it != S.I64: self.err("index must be i64", e.idx, f); return None
            self.bounds(env, e, e.arr, e.idx, at)
            return at.elem
        if isinstance(e, S.Len):
            t = self.infer(e.expr, env)
            if not isinstance(t, S.TArr): self.err("len of a non-array", e, f); return None
            return S.I64
        if isinstance(e, S.Cast):
            t = self.infer(e.expr, env)
            if (e.to, t) not in ((S.I64, S.F64), (S.F64, S.I64), (S.U8, S.I64), (S.I64, S.U8), (S.U16, S.I64), (S.I64, S.U16), (S.I32, S.I64), (S.I64, S.I32)):
                self.err(f"cannot cast {t} to {e.to}", e, f); return None
            return e.to
        if isinstance(e, S.RecLit):
            if e.tname in self.enum_types and not getattr(e,'compiler_generated',False):
                self.err('enum storage is private; use its alternative constructors',e,f)
            if e.tname in self.sealed_owners and self.sealed_owners[e.tname] != getattr(f, 'source', None) and not getattr(e,'compiler_generated',False):
                self.err(f'sealed type {self.type_display[e.tname]} can only be constructed in its declaring module', e, f)
                return None
            rt = self.types.get(e.tname)
            if rt is None: self.err(f"unknown type {e.tname}", e, f); return None
            given = dict(e.fields)
            if len(given) != len(e.fields) or set(given) != {n for n, _ in rt.fields}:
                self.err(f"{e.tname} literal must set exactly the fields {[n for n, _ in rt.fields]}", e, f); return None
            ok = True
            for fname, fty in rt.fields:
                t = self.infer(given[fname], env)
                if t is not None and not self.same(t, fty, env): self.err(f"field {fname} has type {t}, expected {fty}", given[fname], f); ok = False
            return rt if ok else None
        if isinstance(e, S.Field):
            t = self.infer(e.expr, env)
            if not isinstance(t, S.TRec): self.err(f"field access on {t}", e, f); return None
            if t.name in self.enum_types and not getattr(e,'compiler_generated',False):
                self.err('enum storage is private; use exhaustive match',e,f);return None
            for n, ft in t.fields:
                if n == e.name:
                    if isinstance(ft, S.TArr):
                        base = e.expr
                        while isinstance(base, S.Field): base = base.expr
                        holder = env.vars.get(base.name) if isinstance(base, S.Var) else None
                        if holder is not None: self.pinned_bindings[id(holder)] = holder
                        key = (id(holder) if isinstance(base, S.Var) else id(e), S.show(e))
                        if key not in self.field_sizes: self.field_sizes[key] = Lin.var(self.sym('fieldlen'))
                        size = self.field_sizes[key]
                        # An array length is never negative: true on every path.
                        self.ambient.append((cmp('>=', size, Lin.num(0)), frozenset()))
                        return S.TArr(ft.elem, size)
                    return ft
            self.err(f"{t.name} has no field {e.name}", e, f); return None
        if isinstance(e, S.With):
            t = self.infer(e.expr, env)
            if not isinstance(t, S.TRec): self.err(f"`with` on {t}", e, f); return None
            if t.name in self.enum_types:
                self.err('enum storage is private; construct an alternative',e,f);return None
            if t.name in self.sealed_owners and self.sealed_owners[t.name] != getattr(f, 'source', None):
                self.err(f'sealed type {self.type_display[t.name]} can only be updated in its declaring module', e, f)
                return None
            fmap = dict(t.fields); ok = True
            for fname, fe in e.fields:
                if fname not in fmap: self.err(f"{t.name} has no field {fname}", fe, f); ok = False; continue
                ft = self.infer(fe, env)
                if ft is not None and not self.same(ft, fmap[fname], env): self.err(f"field {fname} has type {ft}, expected {fmap[fname]}", fe, f); ok = False
            return t if ok else None
        if isinstance(e, S.Let):
            vt = self.infer(e.value, env)
            if vt is None: return None
            lin = self.to_lin(e.value, env) if vt == S.I64 else None
            if isinstance(vt, S.TArr) and not isinstance(vt.size, Lin):
                vt = S.TArr(vt.elem, Lin.var(self.sym("len")))      # a widened size gets a name once bound
            benv = env.bind(e.name, vt, lin)
            if isinstance(vt, S.TArr) and isinstance(vt.size, Lin):
                benv = benv.holds(cmp(">=", vt.size, Lin.num(0)))
            # A bool keeps its condition, so `let direct = i <= n - 8 in if direct`
            # refines like the comparison itself. Bindings never rename symbols.
            if vt == S.BOOL: benv.vars[e.name] = replace(benv.vars[e.name], formula=self.to_formula(e.value, env))
            return self.infer(e.body, benv)
        if isinstance(e, S.If):
            ct = self.infer(e.cond, env)
            if ct != S.BOOL: self.err("if condition must be bool", e.cond, f); return None
            c = self.to_formula(e.cond, env)
            # Facts produced at the top of each branch hold once the if has
            # completed, but only under that branch's condition: result_facts
            # carries them guarded, since they are not visible outside the branch.
            then_env, else_env = env.with_fact(c), env.with_fact(neg(c))
            mark = len(self.ambient)
            tt = self.infer(e.then, then_env)
            e.then_facts = [g for g, conds in self.ambient[mark:] if conds <= then_env.conds]
            mark = len(self.ambient)
            et = self.infer(e.els, else_env)
            e.els_facts = [g for g, conds in self.ambient[mark:] if conds <= else_env.conds]
            if tt is None or et is None: return None
            if not self.same(tt, et, env):
                if isinstance(tt, S.TArr) and isinstance(et, S.TArr) and self.same(tt.elem, et.elem, env):
                    return S.TArr(tt.elem, Lin.var(self.sym("if")))     # size unknown after the join
                self.err(f"branches differ: {tt} vs {et}", e, f); return None
            return tt
        if isinstance(e, (S.Sum, S.ArrC)):
            lt, ht = self.infer(e.lo, env), self.infer(e.hi, env)
            if lt != S.I64 or ht != S.I64: self.err("range bounds must be i64", e, f); return None
            lo, hi = self.to_lin(e.lo, env), self.to_lin(e.hi, env)
            i = Lin.var(e.var) if e.var not in env.vars else Lin.var(f"{e.var}'{self.sym('i')}")
            benv = env.bind(e.var, S.I64, i).with_fact(and_(cmp("<=", lo, i), cmp("<", i, hi)))
            self.pure_context += 1
            try: bt = self.infer(e.body, benv)
            finally: self.pure_context -= 1
            e.body_env = benv
            if bt is None: return None
            if isinstance(e, S.Sum):
                if bt not in (S.I64, S.F64) and not self.numeric_record(bt):
                    self.err(f"sum body must be numeric or a numeric record, got {bt}", e.body, f); return None
                return bt
            self.oblige(env, "range", cmp("<=", lo, hi), e, f"{S.show(e.lo)} <= {S.show(e.hi)}",
                        [f"check {S.show(e.lo)} <= {S.show(e.hi)} in …", "refine the bound's parameter"])
            return S.TArr(bt, hi - lo)
        if isinstance(e, S.Loop):
            return self.loop(e, env)
        if isinstance(e, S.Check):
            if self.predicate(e.pred, env) != S.BOOL: self.err("check predicate must be bool", e.pred, f); return None
            # A predicate the lexical facts already entail needs no runtime test.
            # Only call-free predicates whose arithmetic is proven qualify, so
            # skipping their evaluation cannot skip a trap or an effect.
            e.statically_proven=self.plain_predicate(e.pred) and entails(env.facts,self.to_formula(e.pred,env),diagnostics=False)[0]=='proven'
            if not e.statically_proven: self.runtime_checks += 1
            self.obligations.append({"id": len(self.obligations) + 1, "fn": f.name, "node": e.hash[:12],
                                     "pos": list(e.pos), "kind": "check", "goal": S.show(e.pred),
                                     "status": "proven" if e.statically_proven else "checked"})
            return self.infer(e.body, env.with_fact(self.to_formula(e.pred, env)))
        if isinstance(e, S.Call):
            return self.call(e, env)
        self.err(f"cannot type {type(e).__name__}", e, f); return None

    def size_lin(self, t: S.TArr) -> Lin:
        return t.size if isinstance(t.size, Lin) else Lin.var(self.sym("len"))

    def bounds(self, env, node, arr_e, idx_e, at):
        i = self.to_lin(idx_e, env)
        goal = and_(cmp("<=", Lin.num(0), i), cmp("<", i, self.size_lin(at)))
        src = f"0 <= {S.show(idx_e)} && {S.show(idx_e)} < len({S.show(arr_e)})"
        self.oblige(env, "bounds", goal, node, src,
                    [f"guard: if {src} then … else …", f"check {src} in …",
                     "refine the index parameter, e.g. i : i64{0 <= i, i < n}"])

    def loop(self, e: S.Loop, env: Env):
        f = env.fn
        its = [self.infer(x, env) for x in e.inits]
        if any(t is None for t in its): return None
        annots = e.annots or [None] * len(e.names)
        e.annots = annots
        # Loop states are new bindings, even when they shadow a parameter or an
        # enclosing loop. Reusing its symbol would import unrelated refinements.
        if not hasattr(e, 'state_symbols'):
            e.state_symbols = {n: Lin.var(self.sym('state')) for n in e.names}
        if not hasattr(e, 'state_size_symbols'):
            e.state_size_symbols = {n: Lin.var(self.sym('looplen')) for n in e.names}
        def bind_state(in_env, n, t):
            # A widened length is arbitrary at each iteration, but every read
            # of that iteration's state must refer to the same length. Keeping
            # '_' here made len(a), a[i] and set(a,i,x) invent unrelated sizes,
            # so even a direct bounds guard could never discharge the access.
            bound = S.TArr(t.elem, e.state_size_symbols[n]) if isinstance(t, S.TArr) and t.size == '_' else t
            return in_env.bind(n, bound, e.state_symbols[n] if t == S.I64 else None)
        benv = env
        for n, t, ann in zip(e.names, its, annots):
            if ann is not None:
                aty = self.resolve(ann[0], e, f)
                if aty is None or not self.same(t, aty, env):
                    self.err(f"loop state {n} initialised with {t}, declared {ann[0]}", e, f); return None
            benv = bind_state(benv, n, t)
        e.state_tys = its
        def inv_goal(ann, values, in_env):
            sub = in_env
            for n2, v2, t2 in zip(e.names, values, its):
                sub = sub.bind(n2, t2, self.to_lin(v2, in_env) if t2 == S.I64 else None)
            return and_(*[self.to_formula(q, sub) for q in ann[1]])
        for n, ann, init in zip(e.names, annots, e.inits):
            if ann is None or not ann[1]: continue
            for q in ann[1]:
                if self.predicate(q, benv) != S.BOOL: self.err("invariant must be bool", q, f); return None
            self.oblige(env, "invariant", inv_goal(ann, e.inits, env), init,
                        f"{' && '.join(S.show(q) for q in ann[1])} initially ({n} := {S.show(init)})",
                        ["choose an initial value satisfying the invariant", "weaken the invariant"])
            benv = benv.with_fact(and_(*[self.to_formula(q, benv) for q in ann[1]]))
        if self.infer(e.cond, benv) != S.BOOL: self.err("loop condition must be bool", e.cond, f); return None
        # first pass with the initial sizes; array states whose successor has another size become existential
        mark_o, mark_a, mark_r = len(self.obligations), len(self.ambient), self.runtime_checks
        cf = self.to_formula(e.cond, benv)
        nenv = benv.with_fact(cf)
        widen = []
        for x, t, n in zip(e.nexts, its, e.names):
            nt = self.infer(x, nenv)
            if nt is not None and isinstance(t, S.TArr) and isinstance(nt, S.TArr) and self.same(t.elem, nt.elem, nenv) \
               and not self.same(nt, t, nenv):
                widen.append(n)
        if widen:
            del self.obligations[mark_o:]; del self.ambient[mark_a:]; self.runtime_checks = mark_r
            its = [S.TArr(t.elem, "_") if (n in widen) else t for n, t in zip(e.names, its)]
            e.state_tys = its
            benv = env
            for n, t in zip(e.names, its):
                benv = bind_state(benv, n, t)
            for n, ann in zip(e.names, annots):
                if ann is not None and ann[1]: benv = benv.with_fact(and_(*[self.to_formula(q, benv) for q in ann[1]]))
            if self.infer(e.cond, benv) != S.BOOL: return None
            cf = self.to_formula(e.cond, benv)
            nenv = benv.with_fact(cf)
        else:
            del self.obligations[mark_o:]; del self.ambient[mark_a:]; self.runtime_checks = mark_r
        for x, t, n, ann in zip(e.nexts, its, e.names, annots):
            nt = self.infer(x, nenv)
            if nt is not None and not self.same(nt, t, nenv):
                self.err(f"loop state changes type: {t} -> {nt}", x, f)
            if ann is not None and ann[1] and nt is not None:
                self.oblige(nenv, "invariant", inv_goal(ann, e.nexts, nenv), x,
                            f"{' && '.join(S.show(q) for q in ann[1])} preserved ({n} := {S.show(x)})",
                            ["strengthen the loop condition", "weaken the invariant", "check … in the next expression"])
        return self.infer(e.yld, benv.with_fact(neg(cf)))

    def call(self, e: S.Call, env: Env):
        f = env.fn
        if e.name=='ref_null':
            if not getattr(e,'compiler_generated',False):self.err('ref_null is compiler-internal inactive storage',e,f);return None
            e.builtin='ref_null';return self.resolve(e.ref_null_type,e,f)
        if e.name=='adopt':
            self.require_effect(e,env,{'process'})
            if len(e.args)!=2:self.err('adopt takes (resource, arena)',e,f);return None
            value=self.infer(e.args[0],env);arena=self.infer(e.args[1],env)
            resources={td.name:td for td in self.prog.types if td.resource_drop}
            if not isinstance(value,S.TRec) or value.name not in resources or not isinstance(e.args[0],S.Var) or not isinstance(arena,S.TRec) or arena.name!='Arena':self.err('adopt requires a named resource owner and an Arena',e,f);return None
            drop=self.fns[resources[value.name].resource_drop]
            if not self.required_caps[drop.name]<={'fs','net','process'}:self.err('arena finalizers support fs/net/process capabilities',e,f);return None
            if 'rt_arena_register' not in self.fns:self.err('import std:arena before adopting resources',e,f);return None
            e.resource_target=value;e.resource_drop=drop;e.builtin='adopt';return S.TRef(S.TRec(value.name,()))
        if e.name in ('borrow_ref','ref_live','ref_release'):
            self.require_effect(e,env,{'process'} if e.name!='ref_release' else {'fs','net','process'})
            if len(e.args)!=1:self.err(e.name+' takes one typed Ref',e,f);return None
            reference=self.infer(e.args[0],env)
            if not isinstance(reference,S.TRef):self.err(e.name+' requires Ref<T>',e,f);return None
            if 'rt_arena_lookup' not in self.fns:self.err('import std:arena before accessing references',e,f);return None
            e.builtin=e.name
            if e.name=='borrow_ref':return self.types[reference.resource.name]
            return S.BOOL if e.name=='ref_live' else S.UNIT
        if e.name=='function_null':
            if not getattr(e,'compiler_generated',False):self.err('function_null is compiler-internal inactive storage',e,f);return None
            e.builtin='function_null';return self.resolve(e.function_null_type,e,f)
        if e.name=='function':
            target=self.fns.get(e.args[0].name) if len(e.args)==1 and isinstance(e.args[0],S.Var) else None
            if target is None or e.args[0].name in env.vars or target.external or target.exported or target.variadic or any(p.owned or p.borrowed or p.preds for p in target.params) or target.ret_preds:
                self.err('function requires an internal function without owned parameters or refinements',e,f);return None
            if target.effect and target.capabilities is None:self.err('effect function values require explicit capabilities',e,f);return None
            def shape(t):
                if isinstance(t,S.TArr):return S.TArr(shape(t.elem),'_')
                return t
            # Erasing repeated dependent length binders would lose obligations.
            sizes=[str(p.ty.size) for p in target.params if isinstance(p.ty,S.TArr)]
            if len(set(sizes))!=len(sizes) or any(isinstance(p.ty,S.TArr) and not isinstance(p.ty.size,str) and (len(p.ty.size.vars())!=1 or p.ty.size.const!=0 or any(c!=1 for c in p.ty.size.terms.values()) or set(p.ty.size.vars()) & {q.name for q in target.params if q.ty==S.I64}) for p in target.params):self.err('function values require independent array lengths',e,f);return None
            e.target=target;e.builtin='function';e.args[0].ty=None
            return S.TFn(tuple(shape(p.ty) for p in target.params),shape(target.ret),target.capabilities if target.effect else None)
        binding=env.vars.get(e.name)
        if binding is not None and isinstance(binding.ty,S.TFn):
            signature=binding.ty
            if signature.capabilities is not None:self.require_effect(e,env,signature.capabilities)
            if len(e.args)!=len(signature.params):self.err('function-value argument arity mismatch',e,f);return None
            actual=[self.infer(a,env) for a in e.args]
            if any(t is None for t in actual):return None
            for a,t,wanted in zip(e.args,actual,signature.params):
                if not self.same(t,wanted,env):self.err('function-value argument type mismatch: expected '+str(wanted),a,f)
            e.indirect_signature=signature
            def owned_value(t):return isinstance(t,S.TArr) or isinstance(t,S.TRec) and any(owned_value(x) for _,x in t.fields)
            e.borrowed_args={i for i,t in enumerate(actual) if signature.capabilities is None and (isinstance(t,S.TRec) and owned_value(t) or isinstance(t,S.TArr) and not owned_value(signature.ret))}
            ret=signature.ret
            return S.TArr(ret.elem,Lin.var(self.sym('indirect'))) if isinstance(ret,S.TArr) else ret
        if e.name=='allocation_stats_enabled':
            if e.args:self.err('allocation_stats_enabled takes no arguments',e,f);return None
            e.builtin=e.name;return S.BOOL
        if e.name=='byte_equal':
            actual=[self.infer(a,env) for a in e.args]
            if len(actual)!=2 or any(not isinstance(t,S.TArr) or t.elem!=S.U8 for t in actual):
                self.err('byte_equal requires two byte arrays',e,f);return None
            e.builtin=e.name;e.borrowed_args={0,1};return S.BOOL
        if e.name in ('wrapping_add','wrapping_sub','wrapping_mul','mul_high','bit_and','bit_or','bit_xor','shift_left','shift_right','arithmetic_shift_right'):
            if len(e.args)!=2 or any(self.infer(a,env)!=S.I64 for a in e.args):
                self.err(e.name+' requires two i64 arguments',e,f);return None
            e.builtin=e.name;return S.I64
        if e.name in ('byte_swap64','count_trailing_zeros'):
            if len(e.args)!=1 or self.infer(e.args[0],env)!=S.I64:
                self.err(e.name+' requires one i64 argument',e,f);return None
            e.builtin=e.name;return S.I64
        if e.name in ("null", "noop"):
            if e.args: self.err(f"{e.name} takes no arguments", e, f); return None
            e.builtin = e.name; return S.PTR if e.name == "null" else S.UNIT
        if e.name == "addr":
            self.require_effect(e, env, {'unsafe'})
            if len(e.args) != 1 or not isinstance(e.args[0], S.Var) or e.args[0].name not in self.fns:
                self.err("addr takes a function name", e, f); return None
            e.target = self.fns[e.args[0].name]; e.builtin = "addr"; return S.PTR
        if e.name == "data":
            self.require_effect(e, env, {'unsafe'})
            if len(e.args) != 1 or not isinstance(e.args[0], (S.Var, S.Str)) or not isinstance(self.infer(e.args[0], env), S.TArr) or e.args[0].ty.elem != S.U8:
                self.err("data takes a byte array; its pointer borrows the array's storage", e, f); return None
            e.builtin = "data"; return S.PTR
        if e.name == "view":
            self.require_effect(e, env, {'unsafe'})
            if len(e.args) != 2 or self.infer(e.args[0], env) != S.PTR or self.infer(e.args[1], env) != S.I64:
                self.err("view takes (ptr, byte length)", e, f); return None
            self.oblige(env, "size", cmp(">=", self.to_lin(e.args[1], env), Lin.num(0)), e, "view length >= 0", ["check length >= 0 in …"])
            e.builtin = "view"; return S.TArr(S.U8, self.to_lin(e.args[1], env))
        if e.name == "byte_uninit":
            self.require_effect(e, env, {'unsafe'})
            if len(e.args) != 1 or self.infer(e.args[0], env) != S.I64:
                self.err("byte_uninit takes (byte length)", e, f); return None
            self.oblige(env, "size", cmp(">=", self.to_lin(e.args[0], env), Lin.num(0)), e, "byte_uninit length >= 0", ["check length >= 0 in …"])
            e.builtin = "byte_uninit"; return S.TArr(S.U8, self.to_lin(e.args[0], env))
        if e.name in SYSTEMS:
            if e.name not in ('float_bits','bits_float'): self.require_effect(e, env, set() if e.name=='aes_hardware' else {'unsafe'})
            pts, ret = SYSTEMS[e.name]
            if len(e.args) != len(pts) or any(self.infer(a, env) != t for a, t in zip(e.args, pts)):
                self.err(f"{e.name} expects ({', '.join(map(str, pts))})", e, f); return None
            e.builtin = e.name
            return S.TArr(S.U8, Lin.var(self.sym("response"))) if e.name == "handler_call" else ret
        if e.name in ("serve", 'serve_effect'):
            self.require_effect(e, env, {'net'})
            # serve(port, handler): the runtime owns sockets, framing and per-connection
            # parallelism; `handler : Arr u8 n -> Arr u8 _` is a pure request -> response function.
            if len(e.args) != 2 or not isinstance(e.args[1], S.Var):
                self.err("serve takes (port : i64, handler : function name)", e, f); return None
            if self.infer(e.args[0], env) != S.I64: self.err("serve: port must be i64", e.args[0], f); return None
            h = self.fns.get(e.args[1].name)
            ok = h is not None and len(h.params) == 1 and isinstance(h.params[0].ty, S.TArr) and h.params[0].ty.elem == S.U8 \
                 and isinstance(h.ret, S.TArr) and h.ret.elem == S.U8 and not h.params[0].preds and (not h.effect or e.name == 'serve_effect') and not h.ret_preds
            if not ok: self.err(f"serve: handler must be `fn {e.args[1].name} (req : Arr u8 n) -> Arr u8 _` without preconditions", e, f); return None
            if h.effect: self.require_capabilities(self.required_caps[h.name], e, env)
            e.handler = h; e.builtin = "serve"
            e.args[1].ty = None
            return S.I64
        if e.name == "sqrt":
            if len(e.args) != 1 or self.infer(e.args[0], env) != S.F64: self.err("sqrt takes one f64", e, f); return None
            e.builtin = "sqrt"; return S.F64
        if e.name=='byte_read_le':
            if len(e.args)!=3:self.err('byte_read_le takes (bytes, offset, width)',e,f);return None
            types=[self.infer(a,env) for a in e.args]
            if not isinstance(types[0],S.TArr) or types[0].elem!=S.U8 or types[1:]!=[S.I64,S.I64]:
                self.err('byte_read_le requires a byte array and integer offset/width',e,f);return None
            # A constant width read the lexical facts keep inside the array
            # needs no runtime width or bounds test (e.g. under i <= n - 8).
            width=e.args[2]
            if isinstance(width,S.Num) and width.value in (1,2,4,8):
                offset=self.to_lin(e.args[1],env)
                goal=and_(cmp('>=',offset,Lin.num(0)),cmp('<=',offset+Lin.num(width.value),self.size_lin(types[0])))
                e.bounds_proven=entails(env.facts,goal,diagnostics=False)[0]=='proven'
            e.builtin='byte_read_le';e.borrowed_args={0};return S.I64
        if e.name in ('byte_copy','byte_write_le'):
            count=3 if e.name=='byte_copy' else 4
            if len(e.args)!=count:self.err(f'{e.name} takes {count} arguments',e,f);return None
            types=[self.infer(a,env) for a in e.args]
            if not isinstance(types[0],S.TArr) or types[0].elem!=S.U8 or types[1]!=S.I64:
                self.err(f'{e.name} requires a byte array and integer offset',e,f);return None
            if e.name=='byte_copy':
                if not isinstance(types[2],S.TArr) or types[2].elem!=S.U8:
                    self.err('byte_copy source must be a byte array',e,f);return None
                e.borrowed_args={2}
            elif types[2:]!=[S.I64,S.I64]:
                self.err('byte_write_le value and width must be integers',e,f);return None
            else:
                # As for byte_read_le: a constant width the lexical facts keep inside the array.
                width=e.args[3]
                if isinstance(width,S.Num) and width.value in (1,2,4,8):
                    offset=self.to_lin(e.args[1],env)
                    goal=and_(cmp('>=',offset,Lin.num(0)),cmp('<=',offset+Lin.num(width.value),self.size_lin(types[0])))
                    e.bounds_proven=entails(env.facts,goal,diagnostics=False)[0]=='proven'
            e.builtin=e.name;return types[0]
        if e.name == 'byte_slice':
            if len(e.args)!=3:self.err('byte_slice takes (bytes, start, end)',e,f);return None
            at,lo,hi=[self.infer(a,env) for a in e.args]
            if not isinstance(at,S.TArr) or at.elem!=S.U8 or lo!=S.I64 or hi!=S.I64:
                self.err('byte_slice requires a byte array and two integer offsets',e,f);return None
            low,high=self.to_lin(e.args[1],env),self.to_lin(e.args[2],env)
            goal=and_(cmp('>=',low,Lin.num(0)),cmp('<=',low,high),cmp('<=',high,self.size_lin(at)))
            e.bounds_proven=entails(env.facts,goal,diagnostics=False)[0]=='proven'
            e.builtin='byte_slice';e.borrowed_args={0};return S.TArr(S.U8,'_')
        if e.name == "concat":
            # concat(a, b, ...): one allocation, the parts copied in order; size is the exact sum.
            # Byte arrays, or UTF-16 code-unit arrays (every part the same element type).
            if len(e.args) < 2: self.err("concat takes at least two byte arrays", e, f); return None
            total = Lin.num(0); elem = None
            for a in e.args:
                t = self.infer(a, env)
                if not isinstance(t, S.TArr) or t.elem not in (S.U8, S.U16) or elem not in (None, t.elem):
                    self.err(f"concat: argument {S.show(a)} must be Arr u8" + ("" if elem in (None, S.U8) else " or Arr u16 like the first part"), a, f); return None
                elem = t.elem
                total = total + self.size_lin(t)
            e.builtin = "concat"; return S.TArr(elem, total)
        if e.name == 'push':
            if len(e.args)!=2:self.err('push takes (array, value)',e,f);return None
            at,vt=[self.infer(a,env) for a in e.args]
            if not isinstance(at,S.TArr):self.err('push requires an array',e,f);return None
            if vt is None or not self.same(vt,at.elem,env):self.err('push value does not match array element type',e,f);return None
            e.builtin='push';return S.TArr(at.elem,self.size_lin(at)+Lin.num(1))
        if e.name == "set":
            # set(a, i, v): a copy of `a` with a[i] = v. Updated in place when `a` is uniquely owned.
            if len(e.args) != 3: self.err("set takes (array, index, value)", e, f); return None
            at, it, vt = (self.infer(a, env) for a in e.args)
            if not isinstance(at, S.TArr): self.err("set: first argument must be an array", e, f); return None
            if it != S.I64: self.err("set: index must be i64", e.args[1], f); return None
            if vt is None or not self.same(vt, at.elem, env): self.err(f"set: value has type {vt}, expected {at.elem}", e.args[2], f); return None
            self.bounds(env, e, e.args[0], e.args[1], at)
            e.builtin = "set"; return at
        callee = self.fns.get(e.name)
        if callee is None: self.err(f"unknown function {e.name}", e, f); return None
        if callee.effect: self.require_effect(e, env, self.required_caps[callee.name])
        if len(e.args) < len(callee.params) or (not callee.variadic and len(e.args) != len(callee.params)):
            self.err(f"{e.name} takes {len(callee.params)} args", e, f); return None
        ats = [self.infer(a, env) for a in e.args]
        if any(t is None for t in ats): return None
        def contains_owned(t):
            return isinstance(t,S.TArr) or isinstance(t,S.TRec) and any(contains_owned(ft) for _,ft in t.fields)
        e.borrowed_args={i for i,(p,t) in enumerate(zip(callee.params,ats))
                         if p.borrowed or ((isinstance(t,S.TRec) and contains_owned(t) or isinstance(t,S.TArr) and not contains_owned(callee.ret)) and
                         not (callee.effect or callee.exported or callee.external or p.owned))}
        if callee.variadic and any(t not in (S.I64, S.I32, S.F64, S.PTR) for t in ats[len(callee.params):]):
            self.err("variadic arguments must use ABI scalar types (promote small integers to i32)", e, f); return None
        for p, a, at in zip(callee.params, e.args, ats):
            if isinstance(p.ty, S.TArr):
                if not isinstance(at, S.TArr) or not self.same(p.ty.elem, at.elem, env):
                    self.err(f"argument {S.show(a)} has type {at}, expected {p.ty}", a, f); return None
            elif not self.same(at, p.ty, env):
                self.err(f"argument {S.show(a)} has type {at}, expected {p.ty}", a, f); return None
        sub, sizes = self.call_subst(callee, e.args, env)
        # a size variable shared by two array parameters must agree
        seen: Dict[str, S.Node] = {}
        for p, a, at in zip(callee.params, e.args, ats):
            if isinstance(p.ty, S.TArr):
                s = str(p.ty.size)
                if s in seen or (s in sizes and any(q.ty == S.I64 and q.name == s for q in callee.params)):
                    if sizes[s] != self.size_lin(at):
                        self.oblige(env, "size", cmp("==", self.size_lin(at), sizes[s]), a, f"len({S.show(a)}) == {s}",
                                    [f"check len({S.show(a)}) == … in …"])
                seen[s] = a
        for p, a in zip(callee.params, e.args):
            for q in p.preds:
                goal = self.to_formula(q, sub)
                src = S.show(q).replace(p.name, S.show(a)) if len(e.args) == 1 else f"{S.show(q)} with {p.name} := {S.show(a)}"
                self.oblige(env, "precondition", goal, a, src,
                            [f"guard the call: if {src} then … else …", f"check {src} in …",
                             "propagate the refinement to the caller's parameter"])
        r = callee.ret
        if isinstance(r, S.TArr):
            if r.size == "_": return S.TArr(r.elem, Lin.var(self.sym(e.name)))
            return S.TArr(r.elem, subst_lin(r.size, sizes))
        return r
