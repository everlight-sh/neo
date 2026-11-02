"""Compile-time evaluation of pure calls with literal arguments.

Every Axon function is pure, so a call whose arguments are all literals
(`escape("Ben & Jerry's …")`) can be run by the compiler and replaced by its
result. The evaluator is a small interpreter over the typed AST with a step
budget; anything it cannot finish (too many steps, a failing `check`, a
non-literal result type) is left for runtime.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional
from . import syntax as S

class Budget(Exception): pass
class Unfoldable(Exception): pass

class Interp:
    def __init__(self, fns: Dict[str, S.Fn], budget: int = 200_000):
        self.fns = fns; self.steps = budget

    def tick(self):
        self.steps -= 1
        if self.steps <= 0: raise Budget()

    def ev(self, e: S.Node, env: dict):
        self.tick()
        if isinstance(e, S.Num): return e.value
        if isinstance(e, S.Flt): return e.value
        if isinstance(e, S.BoolLit): return e.value
        if isinstance(e, S.Str): return list(e.value)
        if isinstance(e, S.Byte): return e.value
        if isinstance(e, S.Var): return env[e.name]
        if isinstance(e, S.Bin):
            if e.op == "&&": return self.ev(e.left, env) and self.ev(e.right, env)
            if e.op == "||": return self.ev(e.left, env) or self.ev(e.right, env)
            a, b = self.ev(e.left, env), self.ev(e.right, env)
            fl = e.left.ty == S.F64
            if e.op == "+": return a + b
            if e.op == "-": return a - b
            if e.op == "*": return wrap(a * b) if not fl else a * b
            if e.op == "/":
                if fl: return a / b if b != 0 else (math.inf if a > 0 else -math.inf if a < 0 else math.nan)
                if b == 0: raise Unfoldable()
                q = abs(a) // abs(b); return q if (a >= 0) == (b >= 0) else -q
            if e.op == "%":
                if b == 0: raise Unfoldable()
                q = abs(a) // abs(b); q = q if (a >= 0) == (b >= 0) else -q
                return a - b * q
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "==": a == b, "!=": a != b}[e.op]
        if isinstance(e, S.Un):
            v = self.ev(e.expr, env)
            return (not v) if e.op == "!" else -v
        if isinstance(e, S.Cast):
            v = self.ev(e.expr, env)
            if e.to == S.F64: return float(v)
            if e.to == S.U8: return v & 0xFF
            return int(v) if e.expr.ty == S.F64 else v
        if isinstance(e, S.Index):
            a, i = self.ev(e.arr, env), self.ev(e.idx, env)
            if not (0 <= i < len(a)): raise Unfoldable()
            return a[i]
        if isinstance(e, S.Len): return len(self.ev(e.expr, env))
        if isinstance(e, S.Let):
            v = self.ev(e.value, env); env2 = dict(env); env2[e.name] = v
            return self.ev(e.body, env2)
        if isinstance(e, S.If):
            return self.ev(e.then, env) if self.ev(e.cond, env) else self.ev(e.els, env)
        if isinstance(e, (S.Sum, S.ArrC)):
            lo, hi = self.ev(e.lo, env), self.ev(e.hi, env)
            out = [] if isinstance(e, S.ArrC) else (0.0 if e.ty == S.F64 else 0)
            for i in range(lo, hi):
                env2 = dict(env); env2[e.var] = i
                v = self.ev(e.body, env2)
                if isinstance(e, S.ArrC): out.append(v)
                elif isinstance(v, dict): out = v if out == 0 else {k: out[k] + v[k] for k in v}
                else: out += v
            return out
        if isinstance(e, S.Loop):
            state = [self.ev(x, env) for x in e.inits]
            while True:
                env2 = dict(env); env2.update(zip(e.names, state))
                if not self.ev(e.cond, env2): break
                state = [self.ev(x, env2) for x in e.nexts]
            env2 = dict(env); env2.update(zip(e.names, state))
            return self.ev(e.yld, env2)
        if isinstance(e, S.Check):
            if not self.ev(e.pred, env): raise Unfoldable()
            return self.ev(e.body, env)
        if isinstance(e, S.RecLit):
            return {k: self.ev(v, env) for k, v in e.fields}
        if isinstance(e, S.Field): return self.ev(e.expr, env)[e.name]
        if isinstance(e, S.With):
            r = dict(self.ev(e.expr, env))
            for k, v in e.fields: r[k] = self.ev(v, env)
            return r
        if isinstance(e, S.Call):
            b = getattr(e, "builtin", None)
            if b == "sqrt": return math.sqrt(self.ev(e.args[0], env))
            if b == "concat":
                out = []
                for a in e.args: out.extend(self.ev(a, env))
                return out
            if b == "set":
                a, i, v = (self.ev(x, env) for x in e.args)
                if not (0 <= i < len(a)): raise Unfoldable()
                a = list(a); a[i] = v; return a
            if b == "serve": raise Unfoldable()
            f = self.fns[e.name]
            if f.effect or f.external: raise Unfoldable()
            args = [self.ev(a, env) for a in e.args]
            fenv = dict(zip((p.name for p in f.params), args))
            for size_var, carrier in getattr(f, "size_binders", []):      # implicit size parameters
                fenv[size_var] = len(fenv[carrier])
            return self.ev(f.body, fenv)
        raise Unfoldable()

def wrap(v: int) -> int:
    v &= (1 << 64) - 1
    return v - (1 << 64) if v >= (1 << 63) else v

def literal_for(value, ty, pos):
    if ty == S.I64: return S.Num(int(value), pos=pos, ty=ty)
    if ty == S.F64: return S.Flt(float(value), pos=pos, ty=ty)
    if ty == S.BOOL: return S.BoolLit(bool(value), pos=pos, ty=ty)
    if isinstance(ty, S.TArr) and ty.elem == S.U8: return S.Str(bytes(value), pos=pos, ty=ty)
    return None

def is_literal(e: S.Node) -> bool:
    return isinstance(e, (S.Num, S.Flt, S.BoolLit, S.Str, S.Byte))

def fold_program(fns: List[S.Fn]) -> int:
    """Replace calls with all-literal arguments by their values. Returns the number of folds."""
    by_name = {f.name: f for f in fns}
    folded = 0
    def visit(e: S.Node) -> S.Node:
        nonlocal folded
        # rewrite children first
        for fld in list(e.__dataclass_fields__):
            if fld in ("pos", "ty", "hash", "annots"): continue
            v = getattr(e, fld)
            if isinstance(v, S.Node): setattr(e, fld, visit(v))
            elif isinstance(v, list):
                setattr(e, fld, [visit(x) if isinstance(x, S.Node) else ((x[0], visit(x[1])) if isinstance(x, tuple) and isinstance(x[1], S.Node) else x) for x in v])
        if isinstance(e, S.Call) and getattr(e, "builtin", None) != "serve" and e.args and all(is_literal(a) for a in e.args) \
           and (e.name in by_name or getattr(e, "builtin", None) in ("concat", "sqrt", "set")):
            try:
                val = Interp(by_name).ev(e, {})
            except (Budget, Unfoldable, RecursionError, KeyError, ZeroDivisionError, OverflowError, ValueError):
                return e
            lit = literal_for(val, e.ty, e.pos)
            if lit is not None:
                lit.hash = e.hash; folded += 1
                return lit
        return e
    for f in fns:
        if not f.external: f.body = visit(f.body)
    return folded
