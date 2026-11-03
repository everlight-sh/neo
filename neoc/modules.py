"""Lexically resolved source modules, aliases and explicit private declarations.

Import aliases never become runtime objects. Canonical module names are stable
under project relocation. Runtime/standard ABI names remain unchanged.
"""
import hashlib
import os
from pathlib import Path
import tomllib
from . import legacy, syntax as S

STDLIB = Path(__file__).resolve().parents[1] / 'stdlib'
RUNTIME = STDLIB.parent/'runtime'


class SourceError(Exception):
    def __init__(self, message, path, pos=(1, 1)):
        super().__init__(message)
        self.diagnostic = {'kind': 'source', 'file': str(path), 'pos': list(pos), 'msg': message}


def _identity(path,entry,manifests=None):
    """manifests, when given, records which manifest named the module and the
    text it held, so a cached build can tell when either changes."""
    for parent in path.parents:
        manifest=legacy.existing(parent,legacy.MANIFESTS)
        if manifest.is_file():
            try:
                text=manifest.read_text()
                if manifests is not None:manifests[str(path)]=[str(manifest),hashlib.sha256(text.encode()).hexdigest()]
                package=tomllib.loads(text).get('package',{})
                key=(package.get('name',parent.name),package.get('version','0'),str(path.relative_to(parent)))
                return hashlib.sha256(repr(key).encode()).hexdigest()[:16]
            except (ValueError,OSError):break
    if manifests is not None:manifests.setdefault(str(path),['',''])
    return hashlib.sha256(os.path.relpath(path,entry.parent).encode()).hexdigest()[:16]


def sources(entry, runtime=(), overlays=None):
    entry=Path(entry).resolve();texts={};lexed={};order=[];active=[];imports={}
    # What resolution read besides source texts: each import as written and
    # where it resolved, package imports, and the manifests naming modules.
    edges=[];packaged=[];manifests={};prefixes={}
    overlays={str(Path(p).resolve()):text for p,text in (overlays or {}).items()}
    def visit(path,parent=None,pos=(1,1)):
        path=Path(path).resolve()
        if path in active:raise SourceError('cyclic import: '+' -> '.join(p.name for p in active+[path]),parent or path,pos)
        if path in texts:return
        try:text=overlays[str(path)] if str(path) in overlays else path.read_text(encoding='utf-8');tokens=S.lex(text)
        except (OSError,UnicodeError) as exc:raise SourceError(str(exc),parent or path,pos) from exc
        except S.SyntaxError_ as exc:raise SourceError(str(exc),path,exc.pos) from exc
        active.append(path);children=[]
        for i,t in enumerate(tokens):
            if t.kind!='KW' or t.text!='import':continue
            if tokens[i+1].kind!='STR':raise SourceError('import requires a quoted path',path,t.pos)
            name=tokens[i+1].text.encode('latin-1').decode('utf-8');alias=None
            if tokens[i+2].text=='as':
                if tokens[i+3].kind!='IDENT':raise SourceError('import alias requires an identifier',path,t.pos)
                alias=tokens[i+3].text
            if name.startswith('std:'):
                relative=name[4:]
                if not relative or any(p in ('..','') for p in relative.split('/')) or Path(relative).is_absolute():raise SourceError('invalid standard module path',path,t.pos)
                target=STDLIB/(relative+'.neo')
            elif name.startswith('pkg:'):
                from .packages import resolve_import
                try:target=resolve_import(name,path,entry)
                except ValueError as exc:raise SourceError(str(exc),path,t.pos) from exc
                packaged.append(str(path))
            else:target=path.parent/name
            resolved=target.resolve();edges.append([str(target),str(resolved)])
            target=resolved;visit(target,path,t.pos);children.append((target,alias,t.pos))
        imports[path]=children;active.pop();texts[path]=text;lexed[path]=tokens;order.append(path)
    for path in runtime:edges.append([str(path),str(Path(path).resolve())]);visit(path)
    visit(entry)
    names=set()
    for tokens in lexed.values():
        names.update(tokens[i+1].text for i,t in enumerate(tokens[:-1]) if t.kind=='KW' and t.text in ('type','enum'))
    parts={}
    for path in order:
        try:part=S.Parser(lexed[path],names).program()
        except S.SyntaxError_ as exc:raise SourceError(str(exc),path,exc.pos) from exc
        if path!=entry and any(f.name=='main' for f in part.fns):raise SourceError('imported modules cannot declare main',path)
        for declaration in part.fns+part.types:declaration.source=str(path)
        parts[path]=part
    from .check import BUILTINS,SYSTEMS
    builtins=BUILTINS|set(SYSTEMS)|{'null','noop','addr','data','view','hash_key','key_equal'}
    local={};surface={};canonical={}
    for path,part in parts.items():
        trusted=path.is_relative_to(STDLIB) or path.is_relative_to(RUNTIME)
        prefix='' if trusted else '__m'+_identity(path,entry,manifests)+'_'
        prefixes[str(path)]=prefix
        declared={}
        def add(name,actual,declaration):
            if name in declared:raise SourceError('duplicate declaration '+name,path,declaration.pos)
            declared[name]=actual
        for declaration in part.types+part.fns:
            original=declaration.name
            if isinstance(declaration,S.Fn) and original in builtins:raise SourceError('reserved builtin name '+original,path,declaration.pos)
            actual=original if isinstance(declaration,S.Fn) and (declaration.external or declaration.exported or path==entry and original=='main') else prefix+original
            add(original,actual,declaration);canonical[id(declaration)]=actual
            if isinstance(declaration,S.TypeDecl) and declaration.variants is not None:
                for variant,_ in declaration.variants:add(variant,prefix+variant,declaration)
        local[path]=declared
    runtime_names={}
    for path in order:
        if path.is_relative_to(RUNTIME):runtime_names.update(local[path])
    scopes={}
    for path in order:
        imported={};aliases=set()
        for child,alias,pos in imports[path]:
            if alias and alias in aliases:raise SourceError('duplicate import alias '+alias,path,pos)
            if alias:aliases.add(alias)
            for name,actual in surface[child].items():
                exposed=alias+'::'+name if alias else name
                if exposed in imported and imported[exposed]!=actual:raise SourceError('ambiguous import '+exposed+'; use aliases',path,pos)
                imported[exposed]=actual
        scope={**runtime_names,**imported,**local[path]};scopes[path]=scope
        visible={}
        for declaration in parts[path].types+parts[path].fns:
            if getattr(declaration,'visible',True):
                visible[declaration.name]=canonical[id(declaration)]
                if isinstance(declaration,S.TypeDecl) and declaration.variants is not None:
                    for variant,_ in declaration.variants:visible[variant]=local[path][variant]
        surface[path]={**imported,**visible}
    def rewrite_type(ty,scope,parameters,path):
        if isinstance(ty,S.TRef):return S.TRef(rewrite_type(ty.resource,scope,parameters,path))
        if isinstance(ty,S.TFn):return S.TFn(tuple(rewrite_type(t,scope,parameters,path) for t in ty.params),rewrite_type(ty.ret,scope,parameters,path),ty.capabilities)
        if isinstance(ty,S.TArr):return S.TArr(rewrite_type(ty.elem,scope,parameters,path),ty.size)
        if isinstance(ty,S.TRec):
            name=ty.name if ty.name in parameters else scope.get(ty.name)
            if name is None:raise SourceError('unknown or private type '+ty.name,path)
            return S.TRec(name,(),tuple(rewrite_type(t,scope,parameters,path) for t in ty.args))
        return ty
    def rewrite(node,scope,bound,parameters,path):
        if isinstance(node,S.Var):
            if node.name not in bound:
                if node.name in scope:node.name=scope[node.name]
                elif node.name not in builtins:raise SourceError('unknown or private value '+node.name,path,node.pos)
            return
        if isinstance(node,S.Call):
            if node.name not in builtins and node.name not in bound:
                if node.name not in scope:raise SourceError('unknown or private function '+node.name,path,node.pos)
                node.name=scope[node.name]
            node.type_args=tuple(rewrite_type(t,scope,parameters,path) for t in node.type_args)
        if isinstance(node,S.RecLit):
            if node.tname not in scope:raise SourceError('unknown or private type '+node.tname,path,node.pos)
            node.tname=scope[node.tname]
            node.type_args=tuple(rewrite_type(t,scope,parameters,path) for t in getattr(node,'type_args',()))
        if isinstance(node,S.Let):
            rewrite(node.value,scope,bound,parameters,path);rewrite(node.body,scope,bound|{node.name},parameters,path);return
        if isinstance(node,S.Using):
            rewrite(node.value,scope,bound,parameters,path);rewrite(node.body,scope,bound|{node.name},parameters,path);return
        if isinstance(node,(S.ArrC,S.Sum)):
            rewrite(node.lo,scope,bound,parameters,path);rewrite(node.hi,scope,bound,parameters,path);rewrite(node.body,scope,bound|{node.var},parameters,path);return
        if isinstance(node,S.Loop):
            for init in node.inits:rewrite(init,scope,bound,parameters,path)
            inner=bound|set(node.names)
            for value in [node.cond,*node.nexts,node.yld]:rewrite(value,scope,inner,parameters,path)
            node.annots=[None if a is None else (rewrite_type(a[0],scope,parameters,path),a[1]) for a in node.annots]
            for a in node.annots:
                if a:
                    for q in a[1]:rewrite(q,scope,inner,parameters,path)
            return
        if isinstance(node,S.Match):
            rewrite(node.expr,scope,bound,parameters,path);arms=[]
            for variant,binders,body in node.arms:
                if variant!='_':
                    if variant not in scope:raise SourceError('unknown or private alternative '+variant,path,node.pos)
                    variant=scope[variant]
                rewrite(body,scope,bound|set(binders),parameters,path);arms.append((variant,binders,body))
            node.arms=arms;return
        for child in S.children(node):rewrite(child,scope,bound,parameters,path)
    program=S.Program([],[])
    for path in order:
        part=parts[path];scope=scopes[path]
        for td in part.types:
            if td.resource_drop:
                if td.resource_drop not in scope:raise SourceError('unknown resource destructor '+td.resource_drop,path,td.pos)
                td.resource_drop=scope[td.resource_drop]
            parameters=set(td.type_params);td.fields=[(n,rewrite_type(t,scope,parameters,path)) for n,t in td.fields]
            if td.variants is not None:
                td.variant_names={local[path][n]:n for n,_ in td.variants}
                td.variants=[(local[path][n],[rewrite_type(t,scope,parameters,path) for t in payload]) for n,payload in td.variants]
            td.display_name=td.name;td.name=canonical[id(td)]
        for f in part.fns:
            parameters=set(f.type_params);bound={p.name for p in f.params}
            for p in f.params:
                p.ty=rewrite_type(p.ty,scope,parameters,path)
                if isinstance(p.ty,S.TArr) and isinstance(p.ty.size,str):bound.add(p.ty.size)
            for p in f.params:
                for q in p.preds:rewrite(q,scope,bound,parameters,path)
            f.ret=rewrite_type(f.ret,scope,parameters,path)
            for q in f.ret_preds:rewrite(q,scope,bound|{'result'},parameters,path)
            rewrite(f.body,scope,bound,parameters,path);f.display_name=f.name;f.name=canonical[id(f)]
        program.types.extend(part.types);program.fns.extend(part.fns)
    program.sources={str(p):texts[p] for p in order}
    program.dependencies={str(p):[str(child) for child,_,_ in imports[p]] for p in order}
    program.import_edges=edges;program.package_imports=packaged
    program.module_manifests=manifests;program.module_prefixes=prefixes
    program.module_symbols={str(p):surface[p] for p in order}
    program.entry_scope=scopes[entry]
    return program
