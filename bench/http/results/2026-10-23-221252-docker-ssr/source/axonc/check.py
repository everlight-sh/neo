"""Type checker with refinement obligations.

Every indexing, division, range, call precondition, loop invariant and return
refinement produces a proof obligation. The checker discharges it from the
facts in scope (parameter refinements, range bounds, branch conditions,
`check` nodes, let-definitions, loop invariants) plus *ambient facts*: what is
known about the result of each call, loop or branch expression from the
callee's return refinement or the loop's invariant. What it cannot prove is
reported as structured data, never silently turned into a runtime check.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Set, Tuple
from . import syntax as S
from .linear import Lin, Formula, and_, or_, cmp, neg, UNK, entails, formula_str

class CheckError(Exception):
    def __init__(self, errors): super().__init__("type errors"); self.errors = errors

@dataclass
class Binding:
    ty: object
    lin: Optional[Lin] = None      # meaning of an i64 variable, if linear

@dataclass
class Env:
    vars: Dict[str, Binding]
    facts: Formula
    fn: S.Fn
    def bind(self, name, ty, lin=None) -> "Env":
        v = dict(self.vars); v[name] = Binding(ty, lin)
        return replace(self, vars=v)
    def with_fact(self, f: Formula) -> "Env":
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

BUILTINS = {"set", "sqrt", "serve", "concat"}

# Raw memory/FFI operations form the trusted systems boundary. They are only
# available in effect functions, never in refinements or parallel comprehensions.
SYSTEMS = {
    "syscall6": ([S.I64] * 7, S.I64),
    "fork_syscall": ([], S.I64),
    "runtime_state": ([], S.PTR),
    "stack_alloc": ([S.I64], S.PTR),
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
    "invoke_region": ([S.PTR, S.PTR, S.I64], S.UNIT),
    "handler_call": ([S.PTR, S.PTR, S.I64], S.TArr(S.U8, "_")),
}

class Checker:
    def __init__(self, prog: S.Program):
        self.prog = prog
        self.types: Dict[str, S.TRec] = {}
        self.fns = {f.name: f for f in prog.fns}
        self.order = prog.fns
        self.obligations: List[dict] = []
        self.errors: List[dict] = []
        self.runtime_checks = 0
        self.ambient: List[Formula] = []
        self._k = 0
        self.pure_context = 0

    def require_effect(self, e, env):
        if not env.fn.effect or self.pure_context:
            self.err(f"{e.name} requires an effect function and cannot run in a refinement or comprehension", e, env.fn)

    def predicate(self, e, env):
        self.pure_context += 1
        try: return self.infer(e, env)
        finally: self.pure_context -= 1

    # ------------------------------------------------------------ helpers
    def sym(self, kind: str) -> str:
        self._k += 1; return f"⟨{kind}#{self._k}⟩"

    def err(self, msg, node, fn):
        self.errors.append({"kind": "type", "fn": fn.name if fn else "-", "file": getattr(fn, "source", None), "pos": list(getattr(node, "pos", (0, 0))), "msg": msg})

    def resolve(self, t, node, fn):
        if isinstance(t, S.TRec):
            if t.name not in self.types: self.err(f"unknown type {t.name}", node, fn); return None
            return self.types[t.name]
        if isinstance(t, S.TArr):
            el = self.resolve(t.elem, node, fn)
            return None if el is None else S.TArr(el, t.size)
        return t

    def prove(self, env: Env, goal: Formula):
        status, cex = entails(env.facts, goal)
        if status != "proven" and self.ambient:
            st2, cex2 = entails(and_(env.facts, *self.ambient), goal)
            if st2 == "proven": return st2, None
            if st2 == "unproven": cex = cex2
        return status, cex

    def oblige(self, env: Env, kind: str, goal: Formula, node: S.Node, source: str, fixes: List[str]):
        status, cex = self.prove(env, goal)
        rec = {"id": len(self.obligations) + 1, "fn": env.fn.name, "node": node.hash[:12],
               "pos": list(node.pos), "kind": kind, "goal": source, "normalised": formula_str(goal),
               "status": status}
        if status != "proven":
            rec["counterexample"] = cex
            rec["fixes"] = fixes
        self.obligations.append(rec)

    def same(self, a, b, env: Env) -> bool:
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
            if a == ("true",) and b == ("true",): return ("true",)
            return or_(and_(c, a), and_(neg(c), b))
        if isinstance(e, S.Let):
            return self.result_facts(e.body, sym, env.bind(e.name, e.value.ty, self.to_lin(e.value, env) if e.value.ty == S.I64 else None))
        if isinstance(e, S.Check):
            return self.result_facts(e.body, sym, env)
        if isinstance(e, S.Call) and e.name in self.fns:
            callee = self.fns[e.name]
            if not callee.ret_preds or callee.ret != S.I64: return ("true",)
            sub, _ = self.call_subst(callee, e.args, env)
            sub = sub.bind("result", S.I64, sym)
            return and_(*[self.to_formula(q, sub) for q in callee.ret_preds])
        return ("true",)

    # ------------------------------------------------------------ program
    def run(self):
        names = set()
        for f in self.order:
            if f.name in names: self.err(f"duplicate function {f.name}", f, f)
            names.add(f.name)
            if f.name == "main" and (f.external or f.exported):
                self.err("main must be an Axon entry point without extern/export", f, f)
            if f.name in BUILTINS or f.name in SYSTEMS or f.name in ("null", "noop", "addr", "data", "view"):
                self.err(f"reserved builtin name {f.name}", f, f)
        for td in self.prog.types:
            if td.name in self.types: self.err(f"duplicate type {td.name}", td, None); continue
            fields = []
            for fname, fty in td.fields:
                if fty not in S.SCALARS: self.err(f"record field {fname} must be scalar", td, None)
                fields.append((fname, fty))
            self.types[td.name] = S.TRec(td.name, tuple(fields))
        if "main" not in self.fns:
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
        for f in self.order:
            self.check_fn(f)
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
            if s in env.vars:
                if env.vars[s].ty != S.I64: self.err(f"size variable {s} must be i64", p, f)
                size = env.vars[s].lin
            else:
                size = Lin.var(s)
                env = env.bind(s, S.I64, size).with_fact(cmp(">=", size, Lin.num(0)))
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
                env = env.with_fact(self.to_formula(q, env))
        if f.name == "main":
            for p in f.params:
                if p.ty != S.I64: self.err("main parameters must be i64 (parsed from argv)", p, f)
            if f.ret not in (S.I64, S.F64) and not (isinstance(f.ret, S.TArr) and f.ret.elem == S.U8):
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
        is_prod = isinstance(e, S.Bin) and e.op == "*" and not (isinstance(e.left, S.Num) or isinstance(e.right, S.Num))
        is_divmod = isinstance(e, S.Bin) and e.op in ("/", "%") and t == S.I64
        if t == S.I64 and (is_prod or is_divmod or isinstance(e, (S.Call, S.Loop, S.If, S.Index, S.Cast, S.Sum, S.Field, S.Check))):
            e.lin_sym = self.sym("mul" if is_prod else ("div" if is_divmod else type(e).__name__.lower()))
            f = self.result_facts(e, Lin.var(e.lin_sym), env)
            if f != ("true",): self.ambient.append(f)
        return t

    def call_subst(self, callee: S.Fn, args: List[S.Node], env: Env) -> Tuple[Env, Dict[str, Lin]]:
        """Environment mapping the callee's parameters and size variables to the caller's terms."""
        sizes: Dict[str, Lin] = {}
        sub = Env({}, env.facts, env.fn)
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
        if isinstance(e, S.Num): return S.I64
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
                if lt != rt or lt not in (S.I64, S.I32, S.F64, S.U8): self.err(f"comparison {e.op} on {lt} and {rt}", e, f); return None
                return S.BOOL
            if e.op in ("==", "!="):
                if lt != rt or isinstance(lt, (S.TArr, S.TRec)): self.err(f"equality on {lt} and {rt}", e, f); return None
                return S.BOOL
            if e.op in ("&&", "||"):
                if lt != S.BOOL or rt != S.BOOL: self.err(f"{e.op} needs bool operands", e, f); return None
                return S.BOOL
        if isinstance(e, S.Un):
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
            if (e.to, t) not in ((S.I64, S.F64), (S.F64, S.I64), (S.U8, S.I64), (S.I64, S.U8), (S.I32, S.I64), (S.I64, S.I32)):
                self.err(f"cannot cast {t} to {e.to}", e, f); return None
            return e.to
        if isinstance(e, S.RecLit):
            rt = self.types.get(e.tname)
            if rt is None: self.err(f"unknown type {e.tname}", e, f); return None
            given = dict(e.fields)
            if len(given) != len(e.fields) or set(given) != {n for n, _ in rt.fields}:
                self.err(f"{e.tname} literal must set exactly the fields {[n for n, _ in rt.fields]}", e, f); return None
            ok = True
            for fname, fty in rt.fields:
                t = self.infer(given[fname], env)
                if t is not None and t != fty: self.err(f"field {fname} has type {t}, expected {fty}", given[fname], f); ok = False
            return rt if ok else None
        if isinstance(e, S.Field):
            t = self.infer(e.expr, env)
            if not isinstance(t, S.TRec): self.err(f"field access on {t}", e, f); return None
            for n, ft in t.fields:
                if n == e.name: return ft
            self.err(f"{t.name} has no field {e.name}", e, f); return None
        if isinstance(e, S.With):
            t = self.infer(e.expr, env)
            if not isinstance(t, S.TRec): self.err(f"`with` on {t}", e, f); return None
            fmap = dict(t.fields); ok = True
            for fname, fe in e.fields:
                if fname not in fmap: self.err(f"{t.name} has no field {fname}", fe, f); ok = False; continue
                ft = self.infer(fe, env)
                if ft is not None and ft != fmap[fname]: self.err(f"field {fname} has type {ft}, expected {fmap[fname]}", fe, f); ok = False
            return t if ok else None
        if isinstance(e, S.Let):
            vt = self.infer(e.value, env)
            if vt is None: return None
            lin = self.to_lin(e.value, env) if vt == S.I64 else None
            if isinstance(vt, S.TArr) and not isinstance(vt.size, Lin):
                vt = S.TArr(vt.elem, Lin.var(self.sym("len")))      # a widened size gets a name once bound
            benv = env.bind(e.name, vt, lin)
            if isinstance(vt, S.TArr) and isinstance(vt.size, Lin):
                benv = benv.with_fact(cmp(">=", vt.size, Lin.num(0)))
            return self.infer(e.body, benv)
        if isinstance(e, S.If):
            ct = self.infer(e.cond, env)
            if ct != S.BOOL: self.err("if condition must be bool", e.cond, f); return None
            c = self.to_formula(e.cond, env)
            tt = self.infer(e.then, env.with_fact(c))
            et = self.infer(e.els, env.with_fact(neg(c)))
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
            if isinstance(bt, S.TArr): self.err("nested arrays are not supported yet", e.body, f); return None
            self.oblige(env, "range", cmp("<=", lo, hi), e, f"{S.show(e.lo)} <= {S.show(e.hi)}",
                        [f"check {S.show(e.lo)} <= {S.show(e.hi)} in …", "refine the bound's parameter"])
            return S.TArr(bt, hi - lo)
        if isinstance(e, S.Loop):
            return self.loop(e, env)
        if isinstance(e, S.Check):
            if self.predicate(e.pred, env) != S.BOOL: self.err("check predicate must be bool", e.pred, f); return None
            self.runtime_checks += 1
            self.obligations.append({"id": len(self.obligations) + 1, "fn": f.name, "node": e.hash[:12],
                                     "pos": list(e.pos), "kind": "check", "goal": S.show(e.pred), "status": "checked"})
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
        benv = env
        for n, t, ann in zip(e.names, its, annots):
            if ann is not None:
                aty = self.resolve(ann[0], e, f)
                if aty is None or not self.same(t, aty, env):
                    self.err(f"loop state {n} initialised with {t}, declared {ann[0]}", e, f); return None
            benv = benv.bind(n, t, Lin.var(n) if t == S.I64 else None)
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
                benv = benv.bind(n, t, Lin.var(n) if t == S.I64 else None)
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
        if e.name in ("null", "noop"):
            if e.args: self.err(f"{e.name} takes no arguments", e, f); return None
            e.builtin = e.name; return S.PTR if e.name == "null" else S.UNIT
        if e.name == "addr":
            self.require_effect(e, env)
            if len(e.args) != 1 or not isinstance(e.args[0], S.Var) or e.args[0].name not in self.fns:
                self.err("addr takes a function name", e, f); return None
            e.target = self.fns[e.args[0].name]; e.builtin = "addr"; return S.PTR
        if e.name == "data":
            self.require_effect(e, env)
            if len(e.args) != 1 or not isinstance(e.args[0], (S.Var, S.Str)) or not isinstance(self.infer(e.args[0], env), S.TArr) or e.args[0].ty.elem != S.U8:
                self.err("data takes a byte array; its pointer borrows the array's storage", e, f); return None
            e.builtin = "data"; return S.PTR
        if e.name == "view":
            self.require_effect(e, env)
            if len(e.args) != 2 or self.infer(e.args[0], env) != S.PTR or self.infer(e.args[1], env) != S.I64:
                self.err("view takes (ptr, byte length)", e, f); return None
            self.oblige(env, "size", cmp(">=", self.to_lin(e.args[1], env), Lin.num(0)), e, "view length >= 0", ["check length >= 0 in …"])
            e.builtin = "view"; return S.TArr(S.U8, self.to_lin(e.args[1], env))
        if e.name in SYSTEMS:
            self.require_effect(e, env)
            pts, ret = SYSTEMS[e.name]
            if len(e.args) != len(pts) or any(self.infer(a, env) != t for a, t in zip(e.args, pts)):
                self.err(f"{e.name} expects ({', '.join(map(str, pts))})", e, f); return None
            e.builtin = e.name
            return S.TArr(S.U8, Lin.var(self.sym("response"))) if e.name == "handler_call" else ret
        if e.name == "serve":
            self.require_effect(e, env)
            # serve(port, handler): the runtime owns sockets, framing and per-connection
            # parallelism; `handler : Arr u8 n -> Arr u8 _` is a pure request -> response function.
            if len(e.args) != 2 or not isinstance(e.args[1], S.Var):
                self.err("serve takes (port : i64, handler : function name)", e, f); return None
            if self.infer(e.args[0], env) != S.I64: self.err("serve: port must be i64", e.args[0], f); return None
            h = self.fns.get(e.args[1].name)
            ok = h is not None and len(h.params) == 1 and isinstance(h.params[0].ty, S.TArr) and h.params[0].ty.elem == S.U8 \
                 and isinstance(h.ret, S.TArr) and h.ret.elem == S.U8 and not h.params[0].preds and not h.effect and not h.ret_preds
            if not ok: self.err(f"serve: handler must be `fn {e.args[1].name} (req : Arr u8 n) -> Arr u8 _` without preconditions", e, f); return None
            e.handler = h; e.builtin = "serve"
            e.args[1].ty = None
            return S.I64
        if e.name == "sqrt":
            if len(e.args) != 1 or self.infer(e.args[0], env) != S.F64: self.err("sqrt takes one f64", e, f); return None
            e.builtin = "sqrt"; return S.F64
        if e.name == "concat":
            # concat(a, b, ...): one allocation, the parts copied in order; size is the exact sum
            if len(e.args) < 2: self.err("concat takes at least two byte arrays", e, f); return None
            total = Lin.num(0)
            for a in e.args:
                t = self.infer(a, env)
                if not isinstance(t, S.TArr) or t.elem != S.U8: self.err(f"concat: argument {S.show(a)} must be Arr u8", a, f); return None
                total = total + self.size_lin(t)
            e.builtin = "concat"; return S.TArr(S.U8, total)
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
        if callee.effect: self.require_effect(e, env)
        if len(e.args) < len(callee.params) or (not callee.variadic and len(e.args) != len(callee.params)):
            self.err(f"{e.name} takes {len(callee.params)} args", e, f); return None
        ats = [self.infer(a, env) for a in e.args]
        if any(t is None for t in ats): return None
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
