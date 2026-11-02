"""Conservative returned-reference summaries for pure, checked Neo functions.

Sets contain parameter indexes whose backing storage may be reachable from the
result. Scalar computations carry no reference identity. Start at the greatest
fixed point so recursion and opaque calls remain conservative.
"""
from . import syntax as S

def managed(t):
    return isinstance(t,S.TArr) or isinstance(t,S.TRec) and any(managed(ft) for _,ft in t.fields)

def summaries(functions):
    known={f.name:f for f in functions}
    opaque={f.name for f in functions if f.external or f.exported or f.effect or getattr(f,'precompiled',False)}
    def calls(e):
        if not isinstance(e,S.Node):return set()
        out={e.name} if isinstance(e,S.Call) and not getattr(e,'builtin',None) else set()
        return out|set().union(*(calls(c) for c in S.children(e)))
    dependencies={f.name:calls(f.body) if f.name not in opaque else set() for f in functions}
    while True:
        updated=opaque|{name for name,targets in dependencies.items() if any(t not in known or t in opaque for t in targets)}
        if updated==opaque:break
        opaque=updated
    result={f.name:{i for i,p in enumerate(f.params) if managed(p.ty)}|({-1} if f.name in opaque else set()) for f in functions}
    def aliases(e,env):
        if getattr(e,'ty',None) is None:return {-1}|set().union(*env.values())
        if not managed(e.ty):return set()
        if isinstance(e,S.Var):return env.get(e.name,set())
        if isinstance(e,S.Str):return set()
        if isinstance(e,S.Check):return aliases(e.body,env)
        if isinstance(e,S.Let):return aliases(e.body,{**env,e.name:aliases(e.value,env)})
        if isinstance(e,S.If):return aliases(e.then,env)|aliases(e.els,env)
        if isinstance(e,S.Field):return aliases(e.expr,env)
        if isinstance(e,S.Index):return aliases(e.arr,env)
        if isinstance(e,S.RecLit):return set().union(*(aliases(v,env) for _,v in e.fields))
        if isinstance(e,S.With):return aliases(e.expr,env)|set().union(*(aliases(v,env) for _,v in e.fields))
        if isinstance(e,S.ArrC):
            return aliases(e.body,{**env,e.var:set()}) if managed(e.ty.elem) else set()
        if isinstance(e,S.Loop):
            state={n:aliases(v,env) for n,v in zip(e.names,e.inits)}
            while True:
                scope={**env,**state};updated={n:state[n]|aliases(v,scope) for n,v in zip(e.names,e.nexts)}
                if updated==state:break
                state=updated
            return aliases(e.yld,{**env,**state})
        if isinstance(e,S.Call):
            builtin=getattr(e,'builtin',None)
            if builtin=='set':return aliases(e.args[0],env)|aliases(e.args[2],env)
            if builtin in {'byte_copy','byte_write_le','byte_slice','concat'}:
                return aliases(e.args[0],env)
            if builtin=='push':return set().union(*(aliases(v,env) for v in e.args))
            target=known.get(e.name)
            indexes=result[target.name] if target is not None else range(len(e.args))
            return ({-1} if -1 in indexes else set())|set().union(*(aliases(e.args[i],env) for i in indexes if 0<=i<len(e.args)))
        return set().union(*(aliases(child,env) for child in S.children(e)))
    while True:
        updated={}
        for f in functions:
            if f.name in opaque:updated[f.name]=result[f.name];continue
            scope={p.name:{i} if managed(p.ty) else set() for i,p in enumerate(f.params)}
            updated[f.name]=aliases(f.body,scope)
        if updated==result:return result
        result=updated
