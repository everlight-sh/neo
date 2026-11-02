"""Inline concat-producing calls and flatten nested concats.

`concat(acc, row(i))` allocates a row buffer and then copies it into `acc`.
When `row`'s body is a `concat` (under any number of `let`s), inlining the
call and hoisting its lets turns the expression into one `concat(acc, p1, …,
pn)`: the pieces are appended straight onto `acc`, with no intermediate
buffer. Only small, non-recursive callees whose body ends in a `concat` are
inlined; every binder in the inlined body gets a fresh name.
"""
from __future__ import annotations
import copy
from typing import Dict, List, Set
from . import syntax as S

MAX_NODES = 400
_counter = [0]

def fresh(name: str) -> str:
    _counter[0] += 1
    return f"{name}~{_counter[0]}"

def node_count(e: S.Node) -> int:
    return 1 + sum(node_count(c) for c in S.children(e))

def calls_in(e: S.Node, out: Set[str]):
    if isinstance(e, S.Call) and not getattr(e, "builtin", None): out.add(e.name)
    for c in S.children(e): calls_in(c, out)

def is_recursive(f: S.Fn, fns: Dict[str, S.Fn]) -> bool:
    seen, stack = set(), [f.name]
    while stack:
        n = stack.pop()
        if n in seen: continue
        seen.add(n)
        callee = fns.get(n)
        if not callee: continue
        cs: Set[str] = set(); calls_in(callee.body, cs)
        if f.name in cs: return True
        stack.extend(cs)
    return False

def peel_lets(e: S.Node):
    lets = []
    while isinstance(e, S.Let):
        lets.append(e); e = e.body
    return lets, e

def rename(e: S.Node, mapping: Dict[str, str]) -> S.Node:
    """Deep copy with every bound and free variable renamed per mapping (binders get fresh names)."""
    e = copy.copy(e)
    if isinstance(e, S.Var):
        e.name = mapping.get(e.name, e.name); return e
    if isinstance(e, S.Let):
        e.value = rename(e.value, mapping)
        m2 = dict(mapping); m2[e.name] = fresh(e.name); e.name = m2[e.name]
        e.body = rename(e.body, m2); return e
    if isinstance(e, (S.Sum, S.ArrC)):
        e.lo = rename(e.lo, mapping); e.hi = rename(e.hi, mapping)
        m2 = dict(mapping); m2[e.var] = fresh(e.var); e.var = m2[e.var]
        e.body = rename(e.body, m2); return e
    if isinstance(e, S.Loop):
        e.inits = [rename(x, mapping) for x in e.inits]
        m2 = dict(mapping)
        new_names = []
        for n in e.names: m2[n] = fresh(n); new_names.append(m2[n])
        e.names = new_names
        e.cond = rename(e.cond, m2); e.nexts = [rename(x, m2) for x in e.nexts]; e.yld = rename(e.yld, m2)
        e.annots = [None if a is None else (a[0], [rename(q, m2) for q in a[1]]) for a in (e.annots or [])]
        return e
    if isinstance(e, S.Call):
        e.args = [rename(a, mapping) for a in e.args]; return e
    if isinstance(e, (S.RecLit, S.With)):
        if isinstance(e, S.With): e.expr = rename(e.expr, mapping)
        e.fields = [(k, rename(v, mapping)) for k, v in e.fields]; return e
    for fld in list(e.__dataclass_fields__):
        if fld in ("pos", "ty", "hash", "annots", "name", "var", "names"): continue
        v = getattr(e, fld)
        if isinstance(v, S.Node): setattr(e, fld, rename(v, mapping))
        elif isinstance(v, list) and v and isinstance(v[0], S.Node): setattr(e, fld, [rename(x, mapping) for x in v])
    return e

def inline_concat_calls(fns: List[S.Fn]) -> int:
    by_name = {f.name: f for f in fns}
    candidates = {}
    for f in fns:
        if f.effect or f.external: continue
        _, tail = peel_lets(f.body)
        if isinstance(tail, S.Call) and getattr(tail, "builtin", None) == "concat" and node_count(f.body) <= MAX_NODES \
           and not is_recursive(f, by_name) and f.name != "main":
            candidates[f.name] = f
    done = [0]

    def inline_call(call: S.Call) -> S.Node:
        """Return `let p1 = a1 in … let n = len(p) in body'` for a candidate call."""
        f = candidates[call.name]
        mapping = {p.name: fresh(p.name) for p in f.params}
        for s, _ in f.size_binders: mapping[s] = fresh(s)
        body = rename(f.body, mapping)
        expr = body
        for s, carrier in reversed(f.size_binders):
            ln = S.Len(S.Var(mapping[carrier], ty=next(p.ty for p in f.params if p.name == carrier)), ty=S.I64)
            expr = S.Let(mapping[s], ln, expr, ty=expr.ty)
        for p, a in reversed(list(zip(f.params, call.args))):
            expr = S.Let(mapping[p.name], a, expr, ty=expr.ty)
        done[0] += 1
        return expr

    def flatten_concat(e: S.Call) -> S.Node:
        """concat(a, let x = v in concat(b…), c) -> let x = v in concat(a, b…, c)"""
        hoisted = []
        parts = []
        for a in e.args:
            lets, tail = peel_lets(a)
            if isinstance(tail, S.Call) and getattr(tail, "builtin", None) == "concat":
                hoisted.extend(lets); parts.extend(tail.args)
            else:
                parts.append(a)
        if not hoisted and len(parts) == len(e.args): return e
        e.args = parts
        out: S.Node = e
        for l in reversed(hoisted):
            l.body = out; out = l
            l.ty = e.ty
        return out

    def visit(e: S.Node) -> S.Node:
        for fld in list(e.__dataclass_fields__):
            if fld in ("pos", "ty", "hash", "annots"): continue
            v = getattr(e, fld)
            if isinstance(v, S.Node): setattr(e, fld, visit(v))
            elif isinstance(v, list):
                setattr(e, fld, [visit(x) if isinstance(x, S.Node) else ((x[0], visit(x[1])) if isinstance(x, tuple) and isinstance(x[1], S.Node) else x) for x in v])
        if isinstance(e, S.Call) and getattr(e, "builtin", None) == "concat":
            e.args = [inline_call(a) if isinstance(a, S.Call) and a.name in candidates and not getattr(a, "builtin", None) else a
                      for a in e.args]
            return flatten_concat(e)
        return e

    for f in fns:
        f.body = visit(f.body)
    return done[0]
