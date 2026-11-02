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
        if f.effect or f.external or getattr(f,'precompiled',False) or getattr(f,'native_library',False): continue
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
        if not getattr(f,'precompiled',False):f.body = visit(f.body)
    return done[0]


ENTITIES = {38: b"&amp;", 60: b"&lt;", 62: b"&gt;", 34: b"&quot;", 39: b"&#x27;"}

def escape_bytes(value: bytes) -> bytes:
    return b"".join(ENTITIES.get(c, bytes([c])) for c in value)

def is_concat(e: S.Node) -> bool:
    return isinstance(e, S.Call) and getattr(e, "builtin", None) == "concat"

def is_escape(e: S.Node) -> bool:
    # Only the standard library's html_escape has the bare name; module functions are mangled.
    return isinstance(e, S.Call) and e.name == "html_escape" and not getattr(e, "builtin", None) and len(e.args) == 1

def var_names(e: S.Node, out: Set[str]) -> Set[str]:
    if isinstance(e, S.Var): out.add(e.name)
    for c in S.children(e): var_names(c, out)
    return out

def uses(e: S.Node, name: str) -> int:
    return (isinstance(e, S.Var) and e.name == name) + sum(uses(c, name) for c in S.children(e))

def push_html_escapes(fns: List[S.Fn]) -> int:
    """Escape the pieces of concat arguments instead of a joined temporary.

    html_escape(concat(a, b)) is concat(html_escape(a), html_escape(b)), so an
    escaped argument of a concat is split into its pieces: no joined buffer is
    allocated. A single-use `let x = concat(…)` escaped in the concat that ends
    its let chain is substituted first. A piece that is a literal is escaped
    here; one that can only evaluate to literals (through ifs, lets and small
    pure calls) needs no escaping when none of them contain & < > " ', and an
    if/let tree of literals gets its literals escaped. Everything else is
    escaped at runtime, as before.
    """
    by_name = {f.name: f for f in fns}
    done = [0]

    def literals(e: S.Node, depth: int = 0, calls: bool = True):
        if isinstance(e, S.Str): return {e.value}
        if isinstance(e, S.If):
            a = literals(e.then, depth, calls); b = literals(e.els, depth, calls) if a is not None else None
            return a | b if b is not None else None
        if isinstance(e, (S.Let, S.Check)): return literals(e.body, depth, calls)
        if calls and isinstance(e, S.Call) and not getattr(e, "builtin", None) and depth < 3:
            f = by_name.get(e.name)
            if f is not None and not (f.effect or f.external) and getattr(f, "body", None) is not None:
                return literals(f.body, depth + 1)
        return None

    def escaped_tree(e: S.Node, ty) -> S.Node:
        if isinstance(e, S.Str): return S.Str(escape_bytes(e.value), pos=e.pos, ty=ty)
        e = copy.copy(e)
        if isinstance(e, S.If): e.then = escaped_tree(e.then, ty); e.els = escaped_tree(e.els, ty)
        else: e.body = escaped_tree(e.body, ty)
        return e

    def pieces(x: S.Node, call: S.Call) -> List[S.Node]:
        if isinstance(x, S.Str): done[0] += 1; return [S.Str(escape_bytes(x.value), pos=x.pos, ty=call.ty)]
        if isinstance(x, S.Call) and x.name == "int_text" and not getattr(x, "builtin", None): return [x]
        if is_concat(x): done[0] += 1; return [p for a in x.args for p in pieces(a, call)]
        found = literals(x)
        if found is not None and all(escape_bytes(v) == v for v in found): done[0] += 1; return [x]
        if found is not None and literals(x, calls=False) is not None: done[0] += 1; return [escaped_tree(x, call.ty)]
        out = copy.copy(call); out.args = [x]
        return [out]

    def expand(e: S.Call) -> S.Call:
        e.args = [p for a in e.args for p in (pieces(a.args[0], a) if is_escape(a) else [a])]
        return e

    def sink(e: S.Let, pure: bool) -> S.Node:
        lets, tail = peel_lets(e)
        if not pure or not is_concat(tail): return e
        kept, changed = [], False
        for k, l in enumerate(lets):
            later = {m.name for m in lets[k + 1:]}
            spot = next((j for j, a in enumerate(tail.args) if is_escape(a) and isinstance(a.args[0], S.Var) and a.args[0].name == l.name), None)
            if spot is None or not is_concat(l.value) or l.name in later or later & var_names(l.value, set()) \
               or sum(uses(m.value, l.name) for m in lets[k + 1:]) + uses(tail, l.name) != 1:
                kept.append(l); continue
            esc = copy.copy(tail.args[spot]); esc.args = [l.value]; tail.args[spot] = esc; changed = True
        if not changed: return e
        out: S.Node = expand(tail)
        for l in reversed(kept):
            l = copy.copy(l); l.body = out; out = l
        return out

    def visit(e: S.Node, pure: bool) -> S.Node:
        for fld in list(e.__dataclass_fields__):
            if fld in ("pos", "ty", "hash", "annots"): continue
            v = getattr(e, fld)
            if isinstance(v, S.Node): setattr(e, fld, visit(v, pure))
            elif isinstance(v, list):
                setattr(e, fld, [visit(x, pure) if isinstance(x, S.Node) else ((x[0], visit(x[1], pure)) if isinstance(x, tuple) and isinstance(x[1], S.Node) else x) for x in v])
        if is_concat(e): return expand(e)
        if isinstance(e, S.Let): return sink(e, pure)
        return e

    # Sinking a let moves its evaluation; effect functions keep their order.
    for f in fns:
        if not getattr(f, 'precompiled', False): f.body = visit(f.body, not f.effect)
    return done[0]
