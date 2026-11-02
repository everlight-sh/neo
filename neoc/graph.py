"""Content-addressed graph: every node is named by the hash of its structure.

Variables are hashed by binder distance (de Bruijn), record fields by
position, record types by their field types, so renaming anything leaves
every hash unchanged. Functions are referenced by hash, so a library is just
a set of hashes and only changed subgraphs recompile.
"""
from __future__ import annotations
import hashlib, json
from typing import Dict, List
from . import syntax as S

def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

class Hasher:
    def __init__(self, fn_hashes: Dict[str, str], types: Dict[str, S.TypeDecl]):
        self.fn_hashes = fn_hashes
        self.types = types
        self.nodes: Dict[str, dict] = {}     # hash -> node record (for the graph dump)

    def ty(self, t, scope) -> object:
        if isinstance(t,S.TRef):return {'ref':t.resource.name if isinstance(t.resource,S.TRec) else self.ty(t.resource,scope)}
        if isinstance(t,S.TFn):return {"function":[self.ty(p,scope) for p in t.params],"return":self.ty(t.ret,scope),"effects":t.capabilities}
        if isinstance(t, S.TArr):
            size = t.size
            if isinstance(size, S.Node): s = self.expr(size, scope)
            elif size == "_": s = "_"
            else: s = var_index(scope, size)
            return {"arr": self.ty(t.elem, scope), "size": s}
        if isinstance(t, S.TRec):
            td = self.types.get(t.name)
            if not td: return {"rec": t.name}
            active = getattr(self, '_active_types', set())
            if t.name in active: return {'recursive': t.name}  # checker rejects recursive value types
            self._active_types = active | {t.name}
            result = {"rec": [self.ty(ft, scope) for _, ft in td.fields]}
            if getattr(td, 'sealed', False): result['sealed'] = True
            if getattr(td, 'resource_drop', None):result['resource_drop']=td.resource_drop
            self._active_types = active
            return result
        return str(t)

    def field_index(self, tname_hint, fname: str, e) -> object:
        # the record type is known after checking; before that, fall back to the
        # unique declaration containing that field name
        cands = [td for td in self.types.values() if any(f == fname for f, _ in td.fields)]
        if len(cands) == 1:
            return [f for f, _ in cands[0].fields].index(fname)
        return fname

    def record(self, node: S.Node, rec: dict) -> str:
        h = _h(rec)
        node.hash = h
        self.nodes.setdefault(h, rec)
        return h

    def expr(self, e: S.Node, scope: List[str]) -> str:
        if isinstance(e, S.Num):      return self.record(e, {"op": "i64", "v": e.value})
        if isinstance(e, S.Flt):      return self.record(e, {"op": "f64", "v": repr(e.value)})
        if isinstance(e, S.BoolLit):  return self.record(e, {"op": "bool", "v": e.value})
        if isinstance(e, S.Str):      return self.record(e, {"op": "bytes", "v": e.value.hex()})
        if isinstance(e, S.Byte):     return self.record(e, {"op": "u8", "v": e.value})
        if isinstance(e, S.Var):      return self.record(e, {"op": "var", "d": var_index(scope, e.name)})
        if isinstance(e, S.Bin):
            return self.record(e, {"op": e.op, "in": [self.expr(e.left, scope), self.expr(e.right, scope)]})
        if isinstance(e, S.Un):       return self.record(e, {"op": "u" + e.op, "in": [self.expr(e.expr, scope)]})
        if isinstance(e, S.Index):
            return self.record(e, {"op": "index", "in": [self.expr(e.arr, scope), self.expr(e.idx, scope)]})
        if isinstance(e, S.Len):      return self.record(e, {"op": "len", "in": [self.expr(e.expr, scope)]})
        if isinstance(e, S.Cast):     return self.record(e, {"op": "cast", "to": str(e.to), "in": [self.expr(e.expr, scope)]})
        if isinstance(e, S.Field):
            return self.record(e, {"op": "field", "k": self.field_index(None, e.name, e), "in": [self.expr(e.expr, scope)]})
        if isinstance(e, S.RecLit):
            td = self.types.get(e.tname)
            order = [f for f, _ in td.fields] if td else sorted(dict(e.fields))
            given = dict(e.fields)
            return self.record(e, {"op": "rec", "ty": self.ty(S.TRec(e.tname, ()), scope),
                                   "in": [self.expr(given[f], scope) for f in order if f in given]})
        if isinstance(e, S.With):
            base = self.expr(e.expr, scope)
            fs = sorted(((self.field_index(None, f, e), self.expr(v, scope)) for f, v in e.fields), key=lambda x: str(x[0]))
            return self.record(e, {"op": "with", "in": [base], "set": fs})
        if isinstance(e, S.Call):
            if e.name in ("addr","function") and len(e.args) == 1 and isinstance(e.args[0], S.Var):
                return self.record(e, {"op": e.name, "fn": self.fn_hashes.get(e.args[0].name, f"rec:{e.args[0].name}")})
            if e.name in ("serve", 'serve_effect') and len(e.args) == 2 and isinstance(e.args[1], S.Var):
                h = self.fn_hashes.get(e.args[1].name, f"rec:{e.args[1].name}")
                return self.record(e, {"op": e.name, "handler": h, "in": [self.expr(e.args[0], scope)]})
            if e.name in ("set", "sqrt", "concat"):
                return self.record(e, {"op": e.name, "in": [self.expr(a, scope) for a in e.args]})
            if e.name in scope:return self.record(e,{"op":"indirect","target":var_index(scope,e.name),"in":[self.expr(a,scope) for a in e.args]})
            callee = self.fn_hashes.get(e.name, f"rec:{e.name}")
            return self.record(e, {"op": "call", "fn": callee, "in": [self.expr(a, scope) for a in e.args]})
        if isinstance(e, S.Let):
            v = self.expr(e.value, scope)
            b = self.expr(e.body, scope + [e.name])
            return self.record(e, {"op": "let", "in": [v, b]})
        if isinstance(e, S.If):
            return self.record(e, {"op": "if", "in": [self.expr(e.cond, scope), self.expr(e.then, scope), self.expr(e.els, scope)]})
        if isinstance(e, (S.Sum, S.ArrC)):
            lo, hi = self.expr(e.lo, scope), self.expr(e.hi, scope)
            body = self.expr(e.body, scope + [e.var])
            return self.record(e, {"op": "sum" if isinstance(e, S.Sum) else "arr", "in": [lo, hi, body]})
        if isinstance(e, S.Check):
            return self.record(e, {"op": "check", "in": [self.expr(e.pred, scope), self.expr(e.body, scope)]})
        if isinstance(e, S.Loop):
            inits = [self.expr(x, scope) for x in e.inits]
            inner = scope + e.names
            cond = self.expr(e.cond, inner)
            nexts = [self.expr(x, inner) for x in e.nexts]
            yld = self.expr(e.yld, inner)
            inv = [None if a is None else {"ty": self.ty(a[0], inner), "pre": [self.expr(q, inner) for q in a[1]]} for a in (e.annots or [])]
            return self.record(e, {"op": "loop", "n": len(e.names), "init": inits, "cond": cond, "next": nexts, "yield": yld, "inv": inv})
        raise TypeError(type(e))

    def fn(self, f: S.Fn) -> str:
        scope = [p.name for p in f.params]
        for p in f.params:
            if isinstance(p.ty, S.TArr) and isinstance(p.ty.size, str) and p.ty.size not in scope and p.ty.size != "_":
                scope.append(p.ty.size)
        params = [{"ty": self.ty(p.ty, scope), "pre": [self.expr(q, scope) for q in p.preds]} for p in f.params]
        for param,p in zip(params,f.params):
            if p.owned:param['move']=True
            if p.borrowed:param['borrow']=True
        body = self.expr(f.body, scope)
        ret_preds = [self.expr(q, scope + ["result"]) for q in f.ret_preds]
        rec = {"op": "fn", "params": params, "ret": self.ty(f.ret, scope), "post": ret_preds, "body": body}
        if f.effect: rec["effect"] = True
        if getattr(f, 'cold', False): rec["cold"] = True
        if getattr(f, 'inline', False): rec["inline"] = True
        if f.capabilities is not None: rec['capabilities'] = sorted(f.capabilities)
        if f.external: rec.update(extern=f.name, variadic=f.variadic)
        if f.exported: rec["export"] = f.name
        h = _h(rec); f.hash = h; self.nodes[h] = rec
        return h

def var_index(scope, name):
    for d, n in enumerate(reversed(scope)):
        if n == name: return d
    return f"free:{name}"

def hash_program(prog: S.Program) -> Dict[str, str]:
    """Hash functions in dependency order; returns name -> hash. Also fills node.hash."""
    from .elaborate import prepare
    prepare(prog)
    fn_hashes: Dict[str, str] = {}
    types = {td.name: td for td in prog.types}
    hasher = Hasher(fn_hashes, types)
    by_name = {f.name: f for f in prog.fns}
    def deps(e, out):
        if isinstance(e, S.Call):
            out.add(e.name)
            if e.name in ("serve", 'serve_effect') and len(e.args) == 2 and isinstance(e.args[1], S.Var): out.add(e.args[1].name)
            if e.name in ("addr","function") and len(e.args) == 1 and isinstance(e.args[0], S.Var): out.add(e.args[0].name)
        for c in S.children(e): deps(c, out)
    done, visiting = set(), set()
    def visit(f: S.Fn):
        if f.name in done: return
        if f.name in visiting: return          # recursion: callee hashed by name
        visiting.add(f.name)
        d = set(); deps(f.body, d)
        for p in f.params:
            for q in p.preds: deps(q, d)
        for q in f.ret_preds: deps(q, d)
        for name in sorted(d):
            if name in by_name: visit(by_name[name])
        fn_hashes[f.name] = hasher.fn(f)
        done.add(f.name); visiting.discard(f.name)
    for f in prog.fns: visit(f)
    hash_program.last_nodes = hasher.nodes     # type: ignore[attr-defined]
    return fn_hashes

def program_hash(fn_hashes: Dict[str, str]) -> str:
    return _h(sorted(fn_hashes.values()))
