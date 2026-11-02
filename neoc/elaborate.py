"""Compile-time specialization and checked tagged-alternative lowering.

No type dictionaries, boxing runtime, or interpreter is linked into programs.
Specializations retain source positions and pass the ordinary ownership/effect/
refinement checker. Alternative representations are private to the compiler.
"""
from copy import deepcopy
import hashlib
from . import syntax as S


class ElaborationError(Exception):
    def __init__(self,message,node=None,source=None):
        self.errors=[dict(kind='language',file=source,pos=list(getattr(node,'pos',(1,1))),msg=message)]
        super().__init__(message)


def nodes(node):
    yield node
    for child in S.children(node):yield from nodes(child)


def prepare(program):
    if getattr(program,'elaborated',False):return program
    required=(any(t.type_params or t.variants is not None or t.resource_drop for t in program.types) or
              any(f.type_params or any(isinstance(n,(S.Match,S.Try,S.Using)) or getattr(n,'type_args',())
                                      for n in nodes(f.body)) for f in program.fns) or
              any(getattr(t,'args',()) for f in program.fns for t in [f.ret]+[p.ty for p in f.params]))
    if required:Elaborator(program).run()
    program.elaborated=True
    return program


class Elaborator:
    def __init__(self,program):
        self.program=program
        self.decls={t.name:t for t in program.types}
        self.functions={f.name:f for f in program.fns}
        if len(self.decls)!=len(program.types):raise ElaborationError('duplicate type declaration')
        if len(self.functions)!=len(program.fns):raise ElaborationError('duplicate function declaration')
        self.constructors={}
        self.types={}
        self.generated=[]
        self.active=set()
        self.specializations={}
        self.counter=0
        self.source=None
        self.fn=None
        self.used={n.name for f in program.fns for n in nodes(f.body) if isinstance(n,S.Var)}
        self.used.update(p.name for f in program.fns for p in f.params)
        for td in program.types:
            if td.resource_drop and td.type_params:self.fail('resource types currently require a concrete nongeneric declaration',td)
            if td.variants is None:continue
            if not td.variants:self.fail('an enum requires at least one alternative',td)
            names=[n for n,_ in td.variants]
            if len(set(names))!=len(names):self.fail('duplicate enum alternative',td)
            for name,payload in td.variants:
                if name in self.constructors or name in self.functions:
                    self.fail('duplicate constructor '+name+'; use module namespaces',td)
                self.constructors[name]=(td,name,payload)
        for f in program.fns:
            if f.type_params and (f.external or f.exported):self.fail('generic functions cannot expose an external ABI',f)

    def fail(self,message,node=None):raise ElaborationError(message,node,self.source)

    def fresh(self):
        while True:
            self.counter+=1;name='__neo_value_'+str(self.counter)
            if name not in self.used:self.used.add(name);return name

    def key(self,name,args):
        return name+'__'+hashlib.sha256(repr(args).encode()).hexdigest()[:20]

    def concrete(self,ty,subst=None):
        subst=subst or {}
        if isinstance(ty,S.TRef):return S.TRef(subst.get(ty.resource.name,ty.resource) if isinstance(ty.resource,S.TRec) else ty.resource)
        if isinstance(ty,S.TFn):return S.TFn(tuple(self.concrete(t,subst) for t in ty.params),self.concrete(ty.ret,subst),ty.capabilities)
        if isinstance(ty,S.TArr):return S.TArr(self.concrete(ty.elem,subst),ty.size)
        if not isinstance(ty,S.TRec):return ty
        if ty.name in subst:
            if ty.args:self.fail('a type parameter cannot take type arguments')
            return subst[ty.name]
        args=tuple(self.concrete(t,subst) for t in ty.args)
        declaration=self.decls.get(ty.name)
        if declaration is None:return S.TRec(ty.name,(),args)
        if len(args)!=len(declaration.type_params):
            self.fail(f'{ty.name} expects {len(declaration.type_params)} type arguments, got {len(args)}',declaration)
        name=self.key(ty.name,args) if args else ty.name
        if name in self.active:self.fail('recursive value type '+ty.name,declaration)
        if name not in self.types:
            self.active.add(name)
            mapping=dict(zip(declaration.type_params,args))
            td=deepcopy(declaration);td.name=name;td.type_params=()
            td.generic_origin=(declaration.name,args)
            if declaration.variants is None:
                td.fields=[(n,self.concrete(t,mapping)) for n,t in declaration.fields]
            else:
                td.fields=[('__tag',S.I64)];layout=[]
                for tag,(variant,payload) in enumerate(declaration.variants):
                    fields=[]
                    for i,ty in enumerate(payload):
                        field=f'__variant_{tag}_{i}';actual=self.concrete(ty,mapping)
                        fields.append((field,actual));td.fields.append((field,actual))
                    layout.append((variant,fields))
                td.variant_layout=layout;td.variants=None
            self.types[name]=td;self.active.remove(name)
        return S.TRec(name,())

    def fields(self,ty):
        if not isinstance(ty,S.TRec):return {}
        td=self.types.get(ty.name) or self.decls.get(ty.name)
        return dict(td.fields) if td else dict(ty.fields)

    def zero(self,ty,pos):
        if isinstance(ty,S.TRef):
            result=S.Call('ref_null',[],pos=pos);result.compiler_generated=True;result.ref_null_type=ty;return result
        if isinstance(ty,S.TFn):
            result=S.Call('function_null',[],pos=pos);result.compiler_generated=True;result.function_null_type=ty;return result
        if ty==S.I64:return S.Num(0,pos=pos)
        if ty==S.I32:return S.Cast(S.I32,S.Num(0),pos=pos)
        if ty==S.U8:return S.Byte(0,pos=pos)
        if ty==S.U16:return S.Cast(S.U16,S.Num(0),pos=pos)
        if ty==S.F64:return S.Flt(0.0,pos=pos)
        if ty==S.BOOL:return S.BoolLit(False,pos=pos)
        if ty==S.UNIT:return S.Call('noop',[],pos=pos)
        if ty==S.PTR:return S.Call('null',[],pos=pos)
        if isinstance(ty,S.TArr):return S.ArrC(self.fresh(),S.Num(0),S.Num(0),self.zero(ty.elem,pos),pos=pos)
        if isinstance(ty,S.TRec):
            td=self.types.get(ty.name)
            value=S.RecLit(ty.name,[(n,self.zero(t,pos)) for n,t in self.fields(ty).items()],pos=pos)
            value.compiler_generated=True
            return value
        self.fail('cannot create inactive alternative storage for '+str(ty))

    def specialize(self,name,args,node):
        f=self.functions[name]
        if len(args)!=len(f.type_params):self.fail(f'{name} expects {len(f.type_params)} type arguments, got {len(args)}',node)
        if not args:return f
        key=self.key(name,args)
        if key in self.specializations:return self.specializations[key]
        if len(self.specializations)>=256:self.fail('generic specialization limit exceeded (possible polymorphic recursion)',node)
        clone=deepcopy(f);clone.name=key;clone.type_params=()
        mapping=dict(zip(f.type_params,args));clone.params=[S.Param(p.name,self.concrete(p.ty,mapping),deepcopy(p.preds),p.pos,p.owned,p.borrowed) for p in f.params]
        clone.ret=self.concrete(f.ret,mapping)
        clone.body=self.owned_scopes(clone)
        self.specializations[key]=clone;self.generated.append(clone)
        self.functions[key]=clone
        previous=(self.fn,self.source)
        self.fn=clone;self.source=getattr(clone,'source',None)
        clone.body,_=self.lower(clone.body,{p.name:p.ty for p in clone.params},mapping)
        self.fn,self.source=previous
        return clone

    def infer_arguments(self,params,templates,actuals,node):
        found={}
        def shape(ty):
            # Value-type parameters describe element/layout shapes. A caller's
            # local length variable is not a new monomorphic type or a binder
            # that can escape into a generic record declaration.
            if isinstance(ty,S.TRef):return ty
            if isinstance(ty,S.TFn):return S.TFn(tuple(shape(t) for t in ty.params),shape(ty.ret),ty.capabilities)
            if isinstance(ty,S.TArr):return S.TArr(shape(ty.elem),'_')
            if isinstance(ty,S.TRec):return S.TRec(ty.name,(),tuple(shape(t) for t in ty.args))
            return ty
        def unify(template,actual):
            if isinstance(template,S.TRec) and template.name in params and not template.args:
                actual=shape(actual)
                previous=found.get(template.name)
                if previous is not None and previous!=actual:self.fail('conflicting inference for '+template.name,node)
                if actual is not None:found[template.name]=actual
            elif isinstance(template,S.TRef) and isinstance(actual,S.TRef):unify(template.resource,actual.resource)
            elif isinstance(template,S.TFn) and isinstance(actual,S.TFn):
                for a,b in zip(template.params,actual.params):unify(a,b)
                unify(template.ret,actual.ret)
            elif isinstance(template,S.TArr) and isinstance(actual,S.TArr):unify(template.elem,actual.elem)
            elif isinstance(template,S.TRec) and isinstance(actual,S.TRec):
                td=self.types.get(actual.name)
                origin=getattr(td,'generic_origin',(actual.name,actual.args))
                if origin[0]==template.name:
                    for a,b in zip(template.args,origin[1]):unify(a,b)
        for template,actual in zip(templates,actuals):unify(template,actual)
        if set(params)!=set(found):self.fail('cannot infer '+', '.join(p for p in params if p not in found)+'; supply explicit ::<...> type arguments',node)
        return tuple(found[p] for p in params)

    def construct(self,e,env,subst):
        td,variant,payload=self.constructors[e.name]
        lowered=[self.lower(a,env,subst) for a in e.args]
        args=tuple(self.concrete(t,subst) for t in e.type_args)
        if not args and td.type_params:args=self.infer_arguments(td.type_params,payload,[t for _,t in lowered],e)
        ty=self.concrete(S.TRec(td.name,(),args));layout=self.types[ty.name].variant_layout
        tag=next(i for i,(n,_) in enumerate(layout) if n==variant)
        if len(e.args)!=len(layout[tag][1]):self.fail('constructor payload arity mismatch for '+variant,e)
        values=[a for a,_ in lowered]
        fields=[('__tag',S.Num(tag,pos=e.pos))]
        for i,(_,members) in enumerate(layout):
            for j,(name,actual) in enumerate(members):fields.append((name,values[j] if i==tag else self.zero(actual,e.pos)))
        value=S.RecLit(ty.name,fields,pos=e.pos);value.compiler_generated=True
        return value,ty

    def lower(self,e,env,subst):
        if isinstance(e,S.Num):return e,S.I64
        if isinstance(e,S.Flt):return e,S.F64
        if isinstance(e,S.BoolLit):return e,S.BOOL
        if isinstance(e,S.Byte):return e,S.U8
        if isinstance(e,S.Str):return e,S.TArr(S.U8,'_')
        if isinstance(e,S.Var):return e,env.get(e.name)
        if isinstance(e,S.Using):
            value,ty=self.lower(e.value,env,subst)
            td=self.types.get(ty.name) if isinstance(ty,S.TRec) else None
            if td is None or not td.resource_drop:self.fail('using requires a resource type',e)
            body,result_ty=self.lower(e.body,{**env,e.name:ty},subst)
            result=self.fresh();released=self.fresh()
            cleanup=S.Call(td.resource_drop,[S.Var(e.name,pos=e.pos)],pos=e.pos);cleanup.resource_cleanup=True
            tail=S.Let(released,cleanup,S.Var(result,pos=e.pos),pos=e.pos)
            captured=S.Let(result,body,tail,pos=e.pos)
            # Preserve a distinct newly constructed owner across temporary
            # cleanup, without allowing source-level borrowed owner escapes.
            captured.resource_factory_result=True
            scope=S.Let(e.name,value,captured,pos=e.pos)
            scope.resource_scope=True
            return scope,result_ty
        if isinstance(e,S.Match):
            value,ty=self.lower(e.expr,env,subst)
            td=self.types.get(ty.name) if isinstance(ty,S.TRec) else None
            if td is None or not hasattr(td,'variant_layout'):self.fail('match requires an enum value',e)
            layout=dict(td.variant_layout);seen=set();wild=False;branches=[];binding=self.fresh();out_ty=None
            for variant,names,body in e.arms:
                if wild:self.fail('unreachable arm after wildcard',e)
                if variant=='_':
                    if names:self.fail('wildcard cannot bind payloads',e)
                    wild=True;members=[]
                else:
                    if variant not in layout:self.fail('unknown alternative '+variant,e)
                    if variant in seen:self.fail('duplicate match arm '+variant,e)
                    seen.add(variant);members=layout[variant]
                    if len(names)!=len(members):self.fail('match payload arity mismatch for '+variant,e)
                    actual=[n for n in names if n!='_']
                    if len(set(actual))!=len(actual):self.fail('duplicate match binding',e)
                inner=dict(env)
                for n,(_,t) in zip(names,members):
                    if n!='_':inner[n]=t
                lowered,branch_ty=self.lower(body,inner,subst);out_ty=out_ty or branch_ty
                for n,(field,_) in reversed(list(zip(names,members))):
                    if n=='_':continue
                    access=S.Field(S.Var(binding),field,pos=e.pos);access.compiler_generated=True
                    lowered=S.Let(n,access,lowered,pos=e.pos)
                branches.append((variant,lowered))
            if not branches:self.fail('empty match',e)
            if not wild and seen!=set(layout):self.fail('non-exhaustive match; missing '+', '.join(sorted(set(layout)-seen)),e)
            result=branches[-1][1]
            for variant,body in reversed(branches[:-1]):
                tag=list(layout).index(variant)
                access=S.Field(S.Var(binding),'__tag',pos=e.pos);access.compiler_generated=True
                result=S.If(S.Bin('==',access,S.Num(tag),pos=e.pos),body,result,pos=e.pos)
            return S.Let(binding,value,result,pos=e.pos),out_ty
        if isinstance(e,S.Try):self.fail('error propagation requires a let binding: let value = result()? in ...',e)
        if isinstance(e,S.Let):
            if isinstance(e.value,S.Try):return self.propagate(e,env,subst)
            e.value,t=self.lower(e.value,env,subst);inner={**env,e.name:t};e.body,t=self.lower(e.body,inner,subst);return e,t
        if isinstance(e,S.Call):
            if e.name=='adopt' and len(e.args)==2:
                e.args[0],inner=self.lower(e.args[0],env,subst);e.args[1],_=self.lower(e.args[1],env,subst);return e,S.TRef(inner)
            if e.name=='borrow_ref' and len(e.args)==1:
                e.args[0],inner=self.lower(e.args[0],env,subst);return e,inner.resource if isinstance(inner,S.TRef) else None
            if e.name in ('ref_live','ref_release'):
                e.args=[self.lower(a,env,subst)[0] for a in e.args];return e,S.BOOL if e.name=='ref_live' else S.UNIT
            if e.name=='function' and len(e.args)==1 and isinstance(e.args[0],S.Var):
                target=self.functions.get(e.args[0].name)
                if target is None or target.type_params:self.fail('function requires a concrete named function',e)
                return e,S.TFn(tuple(p.ty for p in target.params),target.ret,target.capabilities if target.effect else None)
            if e.name in env and isinstance(env[e.name],S.TFn):
                e.args=[self.lower(a,env,subst)[0] for a in e.args];return e,env[e.name].ret
            if e.name in self.constructors:return self.construct(e,env,subst)
            lowered=[self.lower(a,env,subst) for a in e.args];e.args=[a for a,_ in lowered]
            if e.name in ('hash_key','key_equal'):
                ty=lowered[0][1] if lowered else None
                scalar=ty in (S.I64,S.U8,S.U16,S.BOOL,S.I32)
                text=isinstance(ty,S.TArr) and ty.elem==S.U8
                if not scalar and not text:self.fail('hash-map keys must be integer, bool or bytes',e)
                if e.name=='key_equal':
                    if len(lowered)!=2:self.fail('key_equal takes two keys',e)
                    if scalar:return S.Bin('==',*e.args,pos=e.pos),S.BOOL
                    return S.Call('str_equal',e.args,pos=e.pos),S.BOOL
                if len(lowered)!=3:self.fail('hash_key takes (key, seed0, seed1)',e)
                e.name='hash_bytes' if text else 'hash_integer'
                if ty==S.BOOL:e.args[0]=S.If(e.args[0],S.Num(1),S.Num(0),pos=e.pos)
                elif scalar and ty!=S.I64:e.args[0]=S.Cast(S.I64,e.args[0],pos=e.pos)
                return e,S.I64
            if e.name in self.functions:
                args=tuple(self.concrete(t,subst) for t in e.type_args)
                definition=self.functions[e.name]
                if not args and definition.type_params:
                    args=self.infer_arguments(definition.type_params,[p.ty for p in definition.params],[t for _,t in lowered],e)
                target=self.specialize(e.name,args,e);e.name=target.name;e.type_args=()
                return e,target.ret
            from .check import SYSTEMS
            if e.type_args:self.fail('unknown generic function '+e.name,e)
            if e.name in SYSTEMS:return e,SYSTEMS[e.name][1]
            if e.name in ('noop','serve','serve_effect'):return e,S.UNIT
            if e.name in ('null','data','addr'):return e,S.PTR
            if e.name=='sqrt':return e,S.F64
            if e.name=='byte_equal':return e,S.BOOL
            if e.name in ('set','push'):return e,self.rough(e.args[0],env)
            if e.name=='concat' and lowered and isinstance(lowered[0][1],S.TArr):return e,S.TArr(lowered[0][1].elem,'_')
            if e.name in ('concat','view','byte_slice','byte_copy','byte_write_le'):return e,S.TArr(S.U8,'_')
            return e,S.I64
        if isinstance(e,S.RecLit):
            ty=self.concrete(S.TRec(e.tname,(),tuple(self.concrete(t,subst) for t in getattr(e,'type_args',()))))
            e.tname=ty.name;e.fields=[(n,self.lower(v,env,subst)[0]) for n,v in e.fields];return e,ty
        if isinstance(e,S.Field):
            e.expr,t=self.lower(e.expr,env,subst);return e,self.fields(t).get(e.name)
        if isinstance(e,S.With):
            e.expr,t=self.lower(e.expr,env,subst);e.fields=[(n,self.lower(v,env,subst)[0]) for n,v in e.fields];return e,t
        if isinstance(e,S.If):
            e.cond,_=self.lower(e.cond,env,subst);e.then,t=self.lower(e.then,env,subst);e.els,u=self.lower(e.els,env,subst);return e,t or u
        if isinstance(e,S.Check):
            e.pred,_=self.lower(e.pred,env,subst);e.body,t=self.lower(e.body,env,subst);return e,t
        if isinstance(e,S.Bin):
            e.left,t=self.lower(e.left,env,subst);e.right,_=self.lower(e.right,env,subst)
            return e,S.BOOL if e.op in ('==','!=','<','<=','>','>=','&&','||') else t
        if isinstance(e,S.Un):e.expr,t=self.lower(e.expr,env,subst);return e,S.BOOL if e.op=='!' else t
        if isinstance(e,S.Cast):e.expr,_=self.lower(e.expr,env,subst);return e,e.to
        if isinstance(e,S.Len):e.expr,_=self.lower(e.expr,env,subst);return e,S.I64
        if isinstance(e,S.Index):
            e.arr,t=self.lower(e.arr,env,subst);e.idx,_=self.lower(e.idx,env,subst);return e,t.elem if isinstance(t,S.TArr) else None
        if isinstance(e,(S.ArrC,S.Sum)):
            e.lo,_=self.lower(e.lo,env,subst);e.hi,_=self.lower(e.hi,env,subst);e.body,t=self.lower(e.body,{**env,e.var:S.I64},subst)
            return e,S.TArr(t,'_') if isinstance(e,S.ArrC) else t
        if isinstance(e,S.Loop):
            values=[self.lower(v,env,subst) for v in e.inits];e.inits=[v for v,_ in values];inner={**env,**dict(zip(e.names,[t for _,t in values]))}
            e.cond,_=self.lower(e.cond,inner,subst);e.nexts=[self.lower(v,inner,subst)[0] for v in e.nexts];e.yld,t=self.lower(e.yld,inner,subst)
            e.annots=[None if a is None else (self.concrete(a[0],subst),a[1]) for a in e.annots];return e,t
        self.fail('unsupported language expression '+type(e).__name__,e)

    def rough(self,e,env):return self.lower(deepcopy(e),env,{})[1]

    def propagate(self,e,env,subst):
        value,ty=self.lower(e.value.expr,env,subst)
        td=self.types.get(ty.name) if isinstance(ty,S.TRec) else None
        target=self.types.get(self.fn.ret.name) if isinstance(self.fn.ret,S.TRec) else None
        if td is None or target is None or not hasattr(td,'variant_layout') or not hasattr(target,'variant_layout'):
            self.fail('? requires a Result-like enum and a Result-like function return type',e)
        layout={getattr(td,'variant_names',{}).get(n,n):members for n,members in td.variant_layout}
        out={getattr(target,'variant_names',{}).get(n,n):members for n,members in target.variant_layout}
        if set(layout)!={'Ok','Err'} or set(out)!={'Ok','Err'} or any(len(layout[k])!=1 or len(out[k])!=1 for k in ('Ok','Err')):
            self.fail('? requires Ok(T), Err(E) alternatives',e)
        if layout['Err'][0][1]!=out['Err'][0][1]:self.fail('? error types do not match',e)
        name=self.fresh();error=self.fresh();inner={**env,e.name:layout['Ok'][0][1]}
        success,result_ty=self.lower(e.body,inner,subst)
        # This continuation form performs an ordinary branch, preserving normal
        # deterministic cleanup on both paths without a hidden exception runtime.
        fields=[('__tag',S.Num(list(out).index('Err'),pos=e.pos))]
        for variant,members in target.variant_layout:
            display=getattr(target,'variant_names',{}).get(variant,variant)
            for field,t in members:fields.append((field,S.Var(error) if display=='Err' else self.zero(t,e.pos)))
        failed=S.RecLit(target.name,fields,pos=e.pos);failed.compiler_generated=True
        access_ok=S.Field(S.Var(name),layout['Ok'][0][0],pos=e.pos);access_ok.compiler_generated=True
        access_err=S.Field(S.Var(name),layout['Err'][0][0],pos=e.pos);access_err.compiler_generated=True
        tag=S.Field(S.Var(name),'__tag',pos=e.pos);tag.compiler_generated=True
        body=S.If(S.Bin('==',tag,S.Num(list(layout).index('Ok')),pos=e.pos),S.Let(e.name,access_ok,success,pos=e.pos),S.Let(error,access_err,failed,pos=e.pos),pos=e.pos)
        return S.Let(name,value,body,pos=e.pos),result_ty

    def run(self):
        originals=[f for f in self.program.fns if not f.type_params]
        for td in self.program.types:
            if not td.type_params:self.concrete(S.TRec(td.name,()))
        for f in originals:
            self.source=getattr(f,'source',None)
            f.params=[S.Param(p.name,self.concrete(p.ty),p.preds,p.pos,p.owned,p.borrowed) for p in f.params];f.ret=self.concrete(f.ret)
        for f in originals:
            self.fn=f;self.source=getattr(f,'source',None)
            f.body=self.owned_scopes(f)
            if any(isinstance(n,(S.Match,S.Try,S.Using)) or getattr(n,'type_args',()) or
                   isinstance(n,S.Call) and (n.name in self.constructors or n.name in self.functions and self.functions[n.name].type_params)
                   for n in nodes(f.body)):
                f.body,_=self.lower(f.body,{p.name:p.ty for p in f.params},{})
        self.program.types=list(self.types.values());self.program.fns=originals+self.generated

    def owned_scopes(self,function):
        body=function.body
        for p in reversed(function.params):
            td=self.types.get(p.ty.name) if isinstance(p.ty,S.TRec) else None
            if p.owned and td is not None and td.resource_drop:body=S.Using(p.name,S.Var(p.name,pos=p.pos),body,pos=p.pos)
        return body
