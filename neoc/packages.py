"""Deterministic local source packages. No registry, scripts or runtime loader."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import tomllib
from . import legacy

VERSION = '0.2.3'
IGNORED = {'.git','.neo-build','.kernel-build','.neo','node_modules','target','__pycache__',*legacy.IGNORED}


def root_for(source):
    path=Path(source).resolve()
    for root in ([path] if path.is_dir() else [])+list(path.parents):
        if any((root/name).is_file() for name in legacy.MANIFESTS):return root
    raise ValueError('package requires an ancestor neo.toml: '+str(path))


def metadata(root):
    try:data=tomllib.loads(legacy.existing(root,legacy.MANIFESTS).read_text())
    except OSError as exc:raise ValueError('cannot read package manifest at '+str(root)) from exc
    package=data.get('package',{})
    if not isinstance(package,dict) or not isinstance(data.get('dependencies',{}),dict):raise ValueError('package and dependencies must be tables at '+str(root))
    name=package.get('name','');version=package.get('version','')
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',name):raise ValueError('invalid package name at '+str(root))
    if not isinstance(version,str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?',version):raise ValueError('package requires an exact version at '+str(root))
    if not isinstance(package.get('entry','src/lib.neo'),str):raise ValueError('package entry must be a string at '+str(root))
    return data


def files(root):
    import os
    result=[]
    for directory,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d not in IGNORED)
        for name in dirs+sorted(names):
            path=Path(directory)/name;rel=path.relative_to(root)
            if path.is_symlink():raise ValueError('package symlinks are not supported: '+str(path))
            if path.is_file() and (path.suffix in legacy.SUFFIXES or rel.as_posix() in legacy.MANIFESTS):result.append(rel)
    return sorted(result)


def digest(root):
    h=hashlib.sha256()
    for rel in files(root):
        content=(root/rel).read_bytes();h.update(rel.as_posix().encode()+b'\0'+str(len(content)).encode()+b'\0'+content)
    return h.hexdigest()


def create(root):
    root=Path(root).resolve();packages={};active=[];by_path={}
    def visit(path):
        path=path.resolve()
        if path in active:raise ValueError('cyclic package dependencies: '+' -> '.join(str(p) for p in active+[path]))
        if path in by_path:return by_path[path]
        data=metadata(path);p=data['package'];identity=p['name']+'@'+p['version']
        if identity in packages:raise ValueError('multiple source roots for '+identity+'; use one canonical local dependency')
        active.append(path);deps={}
        for alias,spec in sorted(data.get('dependencies',{}).items()):
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',alias) or not isinstance(spec,dict) or set(spec)!={'path','version'}:
                raise ValueError('dependency '+alias+' requires only path and exact version')
            if not isinstance(spec['path'],str) or not isinstance(spec['version'],str):raise ValueError('dependency path and version must be strings: '+alias)
            child=(path/spec['path']).resolve();child_data=metadata(child)
            if child_data['package']['version']!=spec['version']:raise ValueError('version mismatch for dependency '+alias)
            deps[alias]=visit(child)
        active.pop();by_path[path]=identity
        import os
        item={'name':p['name'],'version':p['version'],'path':os.path.relpath(path,root),'sha256':None if path==root else digest(path),'dependencies':deps,
              'dependency_paths':{alias:spec['path'] for alias,spec in sorted(data.get('dependencies',{}).items())}}
        packages[identity]=item;return identity
    identity=visit(root)
    return {'format':1,'root':identity,'packages':dict(sorted(packages.items()))}


def write(root):
    root=Path(root).resolve();lock=create(root)
    file=legacy.existing(root,legacy.LOCKS);stage=file.with_name(file.name+'.tmp')
    stage.write_text(json.dumps(lock,sort_keys=True,indent=2)+'\n');stage.replace(file)
    return lock


def verify(root):
    root=Path(root).resolve()
    try:lock=json.loads(legacy.existing(root,legacy.LOCKS).read_text())
    except (OSError,ValueError) as exc:raise ValueError('missing or invalid neo.lock; run neo pkg lock') from exc
    if not isinstance(lock,dict) or lock.get('format')!=1 or not isinstance(lock.get('root'),str) or not isinstance(lock.get('packages'),dict) or lock['root'] not in lock['packages']:raise ValueError('unsupported package lock format')
    for identity,item in lock['packages'].items():
        if not isinstance(item,dict) or not all(isinstance(item.get(k),str) for k in ('name','version','path')) or not all(isinstance(item.get(k),dict) for k in ('dependencies','dependency_paths')):
            raise ValueError('invalid locked package '+str(identity))
        if identity!=lock['root'] and (not isinstance(item.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',item['sha256'])):raise ValueError('invalid locked source hash '+identity)
        if any(not isinstance(k,str) or not isinstance(v,str) for k,v in item['dependencies'].items()):raise ValueError('invalid locked dependency '+identity)
        if not isinstance(item.get('vendored',False),bool):raise ValueError('invalid vendor flag '+identity)
    if (root/lock['packages'][lock['root']]['path']).resolve()!=root:raise ValueError('locked root must be the current project')
    for identity,item in lock['packages'].items():
        path=(root/item['path']).resolve();data=metadata(path);p=data['package']
        if identity!=p['name']+'@'+p['version'] or item['name']!=p['name'] or item['version']!=p['version'] or identity!=lock['root'] and digest(path)!=item['sha256']:
            raise ValueError('locked source changed: '+identity+'; review changes and run neo pkg lock')
        requested=data.get('dependencies',{})
        if set(requested)!=set(item['dependencies']):raise ValueError('locked dependency aliases changed: '+identity)
        for alias,target in item['dependencies'].items():
            if not isinstance(requested[alias],dict):raise ValueError('invalid dependency '+identity+'/'+alias)
            if requested[alias].get('path')!=item.get('dependency_paths',{}).get(alias):raise ValueError('locked dependency path changed: '+identity+'/'+alias)
            if target not in lock['packages'] or requested[alias].get('version')!=lock['packages'][target]['version']:
                raise ValueError('locked dependency version changed: '+identity+'/'+alias)
            child=lock['packages'][target];actual=(root/child['path']).resolve()
            if child.get('vendored'):
                expected=root/'.neo/vendor'/(child['name']+'-'+child['version']+'-'+child['sha256'][:12])
                if actual!=expected.resolve():raise ValueError('invalid vendored source location '+target)
            elif actual!=(path/requested[alias]['path']).resolve():raise ValueError('locked dependency source path changed: '+identity+'/'+alias)
    return lock


def resolve_import(name,source,project=None):
    root=root_for(project or source);lock=verify(root)
    owner=root_for(source);item=None
    for value in lock['packages'].values():
        if (root/value['path']).resolve()==owner:item=value;break
    if item is None:raise ValueError('source package is absent from neo.lock: '+str(owner))
    parts=name[4:].split('/')
    if not parts or any(not re.fullmatch(r'[A-Za-z0-9_.-]+',p) or p in ('.','..') for p in parts):raise ValueError('invalid package import '+name)
    alias=parts[0];target=item['dependencies'].get(alias)
    if target is None:raise ValueError('undeclared package dependency '+alias)
    base=(root/lock['packages'][target]['path']).resolve();data=metadata(base)
    if len(parts)==1 and 'entry' in data['package']:path=(base/data['package']['entry']).resolve()
    else:path=legacy.source(base/'src'/('/'.join(parts[1:]) if len(parts)>1 else 'lib')).resolve()
    if not path.is_relative_to(base):raise ValueError('package import escapes source root')
    return path


def vendor(root):
    root=Path(root).resolve();lock=verify(root)
    for identity,item in lock['packages'].items():
        if identity==lock['root']:continue
        source=(root/item['path']).resolve();relative='.neo/vendor/'+item['name']+'-'+item['version']+'-'+item['sha256'][:12];target=root/relative
        if target.exists():
            if digest(target)!=item['sha256']:raise ValueError('existing vendor source changed: '+str(target))
        else:
            target.mkdir(parents=True)
            for rel in files(source):
                (target/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/rel,target/rel)
        item['path']=relative
        item['vendored']=True
    file=legacy.existing(root,legacy.LOCKS);stage=file.with_name(file.name+'.tmp')
    stage.write_text(json.dumps(lock,sort_keys=True,indent=2)+'\n');stage.replace(file)
    verify(root);return lock


def command(args):
    root=root_for(args.path)
    result={'lock':write,'verify':verify,'vendor':vendor}[args.action](root)
    print(json.dumps({'ok':True,'root':result['root'],'packages':len(result['packages']),'action':args.action},sort_keys=True))
