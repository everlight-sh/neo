"""Cross-iteration vectorization of `sum` bodies.

A `sum(i in lo..hi) body` whose body is scalar arithmetic, possibly with a
data-dependent `loop` (Mandelbrot's escape iteration) and calls to small
scalar functions, is evaluated K iterations at a time: every scalar becomes a
<K x T> vector, `if` becomes `select`, and a `loop` runs while any lane is
still active, freezing finished lanes with masks. LLVM cannot do this itself
because each iteration's trip count is data dependent; the Axon graph has no
false dependencies between iterations, so the compiler may.

Eligibility is conservative: no arrays, records, checks, nested
comprehensions, integer division by a non-constant, or recursion.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from . import syntax as S

K = 16

def _scalar(t) -> bool:
    return t in (S.I64, S.F64, S.BOOL)

def eligible(body: S.Node, fns: Dict[str, S.Fn], depth: int = 0) -> bool:
    if depth > 4: return False
    def ok(e: S.Node) -> bool:
        if not _scalar(e.ty): return False
        if isinstance(e, (S.Num, S.Flt, S.BoolLit, S.Var)): return True
        if isinstance(e, S.Bin):
            if e.op in ("/", "%") and e.ty == S.I64 and not (isinstance(e.right, S.Num) and e.right.value != 0): return False
            return ok(e.left) and ok(e.right)
        if isinstance(e, S.Un): return ok(e.expr)
        if isinstance(e, S.Cast): return e.to in (S.I64, S.F64) and e.expr.ty in (S.I64, S.F64) and ok(e.expr)
        if isinstance(e, S.Let): return ok(e.value) and ok(e.body)
        if isinstance(e, S.If): return ok(e.cond) and ok(e.then) and ok(e.els)
        if isinstance(e, S.Loop):
            return all(_scalar(t) for t in e.state_tys) and all(ok(x) for x in e.inits) and ok(e.cond) \
                and all(ok(x) for x in e.nexts) and ok(e.yld)
        if isinstance(e, S.Call):
            if getattr(e, "builtin", None) == "sqrt": return ok(e.args[0])
            if getattr(e, "builtin", None): return False
            f = fns.get(e.name)
            if f is None or not _scalar(f.ret) or any(not _scalar(p.ty) for p in f.params): return False
            return all(ok(a) for a in e.args) and eligible(f.body, fns, depth + 1)
        return False
    return ok(body)

class VecGen:
    """Emits <K x T> code for a body; `lanes` is the <K x i64> vector of comprehension indices."""
    def __init__(self, gen, fb, fns: Dict[str, S.Fn]):
        self.gen = gen; self.fb = fb; self.fns = fns

    @staticmethod
    def vty(t) -> str:
        return {S.I64: f"<{K} x i64>", S.F64: f"<{K} x double>", S.BOOL: f"<{K} x i1>"}[t]

    def splat(self, scalar: str, ty: str, t) -> str:
        fb = self.fb
        a = fb.ins(f"insertelement {self.vty(t)} poison, {ty} {scalar}, i64 0", self.vty(t))
        return fb.ins(f"shufflevector {a}, {self.vty(t)} poison, <{K} x i32> zeroinitializer", self.vty(t)).name

    def const(self, val: str, t) -> str:
        ty = {S.I64: "i64", S.F64: "double", S.BOOL: "i1"}[t]
        return "<" + ", ".join(f"{ty} {val}" for _ in range(K)) + ">"

    def gen_vec(self, e: S.Node, venv: Dict[str, str], senv) -> str:
        """venv: name -> vector SSA name; senv: scalar env (Slots) for captured outer variables."""
        fb = self.fb
        vt = self.vty(e.ty)
        if isinstance(e, S.Num): return self.const(str(e.value), S.I64)
        if isinstance(e, S.Flt):
            from .llvm import fconst
            return self.const(fconst(e.value), S.F64)
        if isinstance(e, S.BoolLit): return self.const("true" if e.value else "false", S.BOOL)
        if isinstance(e, S.Var):
            if e.name in venv: return venv[e.name]
            s = senv[e.name]
            v = fb.load(s.ty, s.ptr)
            return self.splat(v.name, s.ty, e.ty)
        if isinstance(e, S.Bin):
            a = self.gen_vec(e.left, venv, senv); b = self.gen_vec(e.right, venv, senv)
            lt = e.left.ty; lvt = self.vty(lt)
            if e.op in ("&&", "||"):
                return fb.ins(f"{'and' if e.op == '&&' else 'or'} {lvt} {a}, {b}", vt).name
            fl = lt == S.F64
            if e.op in ("+", "-", "*", "/", "%"):
                op = {"+": "fadd" if fl else "add", "-": "fsub" if fl else "sub", "*": "fmul" if fl else "mul",
                      "/": "fdiv" if fl else "sdiv", "%": "srem"}[e.op]
                return fb.ins(f"{op} {lvt} {a}, {b}", vt).name
            if fl:
                op = {"<": "olt", "<=": "ole", ">": "ogt", ">=": "oge", "==": "oeq", "!=": "une"}[e.op]
                return fb.ins(f"fcmp {op} {lvt} {a}, {b}", vt).name
            op = {"<": "slt", "<=": "sle", ">": "sgt", ">=": "sge", "==": "eq", "!=": "ne"}[e.op]
            return fb.ins(f"icmp {op} {lvt} {a}, {b}", vt).name
        if isinstance(e, S.Un):
            a = self.gen_vec(e.expr, venv, senv)
            if e.op == "!": return fb.ins(f"xor {vt} {a}, {self.const('true', S.BOOL)}", vt).name
            if e.ty == S.F64: return fb.ins(f"fneg {vt} {a}", vt).name
            return fb.ins(f"sub {vt} zeroinitializer, {a}", vt).name
        if isinstance(e, S.Cast):
            a = self.gen_vec(e.expr, venv, senv)
            if e.to == S.F64: return fb.ins(f"sitofp <{K} x i64> {a} to <{K} x double>", vt).name
            return fb.ins(f"fptosi <{K} x double> {a} to <{K} x i64>", vt).name
        if isinstance(e, S.Let):
            v = self.gen_vec(e.value, venv, senv)
            v2 = dict(venv); v2[e.name] = v
            return self.gen_vec(e.body, v2, senv)
        if isinstance(e, S.If):
            c = self.gen_vec(e.cond, venv, senv)
            a = self.gen_vec(e.then, venv, senv); b = self.gen_vec(e.els, venv, senv)
            return fb.ins(f"select <{K} x i1> {c}, {vt} {a}, {vt} {b}", vt).name
        if isinstance(e, S.Call):
            if getattr(e, "builtin", None) == "sqrt":
                a = self.gen_vec(e.args[0], venv, senv)
                return fb.ins(f"call <{K} x double> @llvm.sqrt.v{K}f64(<{K} x double> {a})", vt).name
            f = self.fns[e.name]
            v2 = dict(venv)
            for p, a in zip(f.params, e.args):
                v2[p.name] = self.gen_vec(a, venv, senv)         # inline: parameters become lane vectors
            return self.gen_vec(f.body, v2, senv)
        if isinstance(e, S.Loop):
            return self.gen_loop(e, venv, senv)
        raise TypeError(type(e))

    def gen_loop(self, e: S.Loop, venv, senv) -> str:
        """Masked loop: run while any lane's condition holds; finished lanes keep their state."""
        fb = self.fb
        tys = [self.vty(t) for t in e.state_tys]
        ptrs = []
        for x, ty in zip(e.inits, tys):
            p = fb.alloca(ty); fb.store(_V(self.gen_vec(x, venv, senv), ty), p); ptrs.append(p)
        mask_p = fb.alloca(f"<{K} x i1>"); fb.store(_V(self.const("true", S.BOOL), f"<{K} x i1>"), mask_p)
        head, body, exit_ = fb.label("vloop_head"), fb.label("vloop_body"), fb.label("vloop_exit")
        fb.br(head); fb.block(head)
        v2 = dict(venv)
        for n, p, ty in zip(e.names, ptrs, tys): v2[n] = fb.load(ty, p).name
        c = self.gen_vec(e.cond, v2, senv)
        m = fb.load(f"<{K} x i1>", mask_p)
        m2 = fb.ins(f"and <{K} x i1> {m.name}, {c}", f"<{K} x i1>")
        fb.store(m2, mask_p)
        any_ = fb.ins(f"call i1 @llvm.vector.reduce.or.v{K}i1(<{K} x i1> {m2.name})", "i1")
        fb.cbr(any_, body, exit_); fb.block(body)
        nexts = [self.gen_vec(x, v2, senv) for x in e.nexts]
        for n, p, ty, nx in zip(e.names, ptrs, tys, nexts):
            sel = fb.ins(f"select <{K} x i1> {m2.name}, {ty} {nx}, {ty} {v2[n]}", ty)
            fb.store(sel, p)
        fb.br(head); fb.block(exit_)
        v3 = dict(venv)
        for n, p, ty in zip(e.names, ptrs, tys): v3[n] = fb.load(ty, p).name
        return self.gen_vec(e.yld, v3, senv)

class _V:
    """Minimal stand-in for llvm.Val (name, ty) to reuse FuncBuilder.store."""
    def __init__(self, name, ty): self.name = name; self.ty = ty
    def __str__(self): return f"{self.ty} {self.name}"

def vector_sum_loop(gen, fb, e: S.Sum, lo, hi, env, acc_ptr: str, fns: Dict[str, S.Fn]):
    """Accumulate sum(body) over [lo, hi) into *acc_ptr, K lanes at a time."""
    vg = VecGen(gen, fb, fns)
    t = e.ty; vt = vg.vty(t)
    vacc = fb.alloca(vt); fb.store(_V("zeroinitializer", vt), vacc)
    ip = fb.alloca("i64"); fb.store(_V(lo.name, "i64"), ip)
    cond, body, end = fb.label("vsum_cond"), fb.label("vsum_body"), fb.label("vsum_end")
    fb.br(cond); fb.block(cond)
    i = fb.load("i64", ip)
    c = fb.ins(f"icmp slt i64 {i.name}, {hi.name}", "i1")
    fb.cbr(c, body, end); fb.block(body)
    base = vg.splat(i.name, "i64", S.I64)
    lanes = fb.ins(f"add <{K} x i64> {base}, <{', '.join(f'i64 {k}' for k in range(K))}>", f"<{K} x i64>")
    hiv = vg.splat(hi.name, "i64", S.I64)
    active = fb.ins(f"icmp slt <{K} x i64> {lanes.name}, {hiv}", f"<{K} x i1>")
    last = fb.ins(f"sub i64 {hi.name}, 1", "i64")
    lastv = vg.splat(last.name, "i64", S.I64)
    idx = fb.ins(f"select <{K} x i1> {active.name}, <{K} x i64> {lanes.name}, <{K} x i64> {lastv}", f"<{K} x i64>")
    venv = {e.var: idx.name}                      # inactive lanes recompute the last valid index and are masked out
    val = vg.gen_vec(e.body, venv, env)
    masked = fb.ins(f"select <{K} x i1> {active.name}, {vt} {val}, {vt} zeroinitializer", vt)
    old = fb.load(vt, vacc)
    op = "fadd reassoc" if t == S.F64 else "add"
    fb.store(fb.ins(f"{op} {vt} {old.name}, {masked.name}", vt), vacc)
    i2 = fb.ins(f"add i64 {i.name}, {K}", "i64"); fb.store(i2, ip)
    fb.br(cond); fb.block(end)
    v = fb.load(vt, vacc)
    if t == S.F64:
        red = fb.ins(f"call reassoc double @llvm.vector.reduce.fadd.v{K}f64(double 0.0, <{K} x double> {v.name})", "double")
        old = fb.load("double", acc_ptr); fb.store(fb.ins(f"fadd reassoc double {old.name}, {red.name}", "double"), acc_ptr)
    else:
        red = fb.ins(f"call i64 @llvm.vector.reduce.add.v{K}i64(<{K} x i64> {v.name})", "i64")
        old = fb.load("i64", acc_ptr); fb.store(fb.ins(f"add i64 {old.name}, {red.name}", "i64"), acc_ptr)
