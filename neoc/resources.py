"""Affine scoped resources after ordinary type checking.

Resources can be borrowed by calls or transferred to a move parameter. They
cannot be copied into records/arrays, escape a using scope, or be used after a
possible move. Cleanup is already an ordinary effectful call in the graph.
Fatal traps terminate the process; the OS releases process handles on that path.
"""
from . import syntax as S


def validate(checker):
    resources={t.name:t for t in checker.prog.types if t.resource_drop}
    if not resources:return
    def is_resource(ty):return isinstance(ty,S.TRec) and ty.name in resources
    def contains(ty,seen=None):
        if is_resource(ty):return True
        if isinstance(ty,S.TArr):return contains(ty.elem,seen)
        if isinstance(ty,S.TRec):
            seen=set(seen or ())
            if ty.name in seen:return False
            seen.add(ty.name);return any(contains(t,seen) for _,t in checker.types[ty.name].fields)
        return False
    for td in checker.prog.types:
        for _,ty in checker.types[td.name].fields:
            if contains(ty):checker.err('resources cannot be stored in value records, enums or arrays',td,None)
        if td.resource_drop:
            destructor=checker.fns.get(td.resource_drop)
            if destructor is not None:destructor.resource_destructor_for=td.name
            if destructor is None or not destructor.effect or destructor.ret!=S.UNIT or len(destructor.params)!=1 or destructor.params[0].ty!=checker.types[td.name] or destructor.params[0].owned:
                checker.err('resource destructor must be an effect function borrowing one resource and returning unit',td,None)
    for fn in checker.order:
        for param in fn.params:
            if contains(param.ty) and not is_resource(param.ty):checker.err('resource parameters must be direct borrows or moves',param,fn)
        if contains(fn.ret) and not is_resource(fn.ret):checker.err('resources cannot escape inside a return value',fn,fn)
        if is_resource(fn.ret) and (getattr(fn,'source',None)!=getattr(resources[fn.ret.name],'source',None) or fn.exported or fn.name=='main'):
            checker.err('only the declaring module can define resource factories',fn,fn)
        initial={p.name:(True,p.owned) for p in fn.params if is_resource(p.ty)}
        factory_results=set()
        def error(message,node):checker.err(message,node,fn)
        def walk(node,state,context='value'):
            ty=getattr(node,'ty',None)
            if is_resource(ty) and context not in ('borrow','consume','factory'):
                error('resource value requires a using scope; it cannot escape or be copied',node)
            if isinstance(node,S.Var) and is_resource(ty):
                live,owned=state.get(node.name,(False,False))
                if not live:error('resource '+node.name+' used after move or outside its scope',node)
                if context=='consume':
                    if not owned:error('cannot move borrowed resource '+node.name,node)
                    state[node.name]=(False,owned)
                    node.resource_move=True
                elif context=='factory':
                    if node.name in factory_results and live and owned:
                        state[node.name]=(False,owned);node.resource_move=True
                    else:error('a resource factory must construct a new owner',node)
                return
            if isinstance(node,S.Let):
                scoped=getattr(node,'resource_scope',False)
                if is_resource(getattr(node.value,'ty',None)):
                    factory_result=getattr(node,'resource_factory_result',False) and context=='factory'
                    if not scoped and not factory_result:error('bind resource owners with using',node)
                    walk(node.value,state,'consume' if scoped and isinstance(node.value,S.Var) else 'factory')
                    inner=dict(state);inner[node.name]=(True,True)
                    if factory_result:factory_results.add(node.name)
                    walk(node.body,inner,context)
                    if factory_result:factory_results.remove(node.name)
                    for name in state:
                        if name!=node.name:state[name]=(state[name][0] and inner.get(name,state[name])[0],state[name][1])
                    return
                walk(node.value,state);inner=dict(state)
                # Shadowing a resource is rejected: it otherwise hides ownership.
                if node.name in state:error('cannot shadow an active resource '+node.name,node)
                walk(node.body,inner,context)
                for name in state:state[name]=(state[name][0] and inner.get(name,state[name])[0],state[name][1])
                return
            if isinstance(node,S.If):
                walk(node.cond,state);a=dict(state);b=dict(state);walk(node.then,a,context);walk(node.els,b,context)
                for name in state:state[name]=(a[name][0] and b[name][0],state[name][1])
                return
            if isinstance(node,S.Check):walk(node.pred,state);walk(node.body,state,context);return
            if isinstance(node,S.Call):
                if getattr(node,'resource_cleanup',False):return
                if node.name=='borrow_ref':
                    if context!='borrow':error('borrow_ref is only valid as an immediate borrowed argument',node)
                    for arg in node.args:walk(arg,state)
                    return
                callee=None if getattr(node,'indirect_signature',None) is not None else checker.fns.get(node.name)
                if is_resource(ty) and context=='borrow':error('temporary resource must be bound with using before borrowing',node)
                for index,arg in enumerate(node.args):
                    if is_resource(getattr(arg,'ty',None)):
                        owned=(node.name=='adopt' and index==0) or (callee is not None and index<len(callee.params) and callee.params[index].owned) or node.name in {td.resource_drop for td in resources.values()}
                        if isinstance(arg,S.Call) and arg.name=='borrow_ref' and not owned:walk(arg,state,'borrow');continue
                        if not isinstance(arg,S.Var):error('resource call arguments must name an existing owner or borrow',arg)
                        walk(arg,state,'consume' if owned else 'borrow')
                    else:walk(arg,state)
                return
            if isinstance(node,S.RecLit) and is_resource(ty):
                if context!='factory':error('resource construction requires a using scope',node)
                for child in S.children(node):walk(child,state)
                return
            if isinstance(node,S.With) and is_resource(ty):error('resources cannot be copied with record updates',node)
            if isinstance(node,S.Field) and is_resource(getattr(node.expr,'ty',None)):
                declaration=resources[node.expr.ty.name]
                if getattr(fn,'source',None)!=getattr(declaration,'source',None):error('resource representation is private; use its borrowing operations',node)
                walk(node.expr,state,'borrow');return
            if isinstance(node,(S.Loop,S.ArrC,S.Sum)):
                before=dict(state);inner=dict(state)
                for child in S.children(node):walk(child,inner)
                for name in before:
                    if before[name][0] and not inner.get(name,before[name])[0]:error('cannot move an outer resource from a repeating region',node)
                return
            for child in S.children(node):walk(child,state)
        walk(fn.body,initial,'factory' if is_resource(fn.ret) else 'value')
