"""Content-addressed native libraries built from checked Neo LLVM IR.

Caches contain dependency code, never application bodies. Optimized dependency
IR remains available to the application inliner. All code is statically linked.
"""
import hashlib,json,os,re,subprocess,tempfile,time
from pathlib import Path
from . import syntax as S

SYMBOL=re.compile(r'@([^\s(),]+)')
HEADER=re.compile(r'^define (.*?)@([^\s(]+)\(',re.M)

def digest(data):return hashlib.sha256(data).hexdigest()
def name(body):
 match=HEADER.search(body);return match[2] if match else None

def public(body):
 return re.sub(r'^define (?:(?:internal|private|hidden|dso_local|available_externally) )*','define hidden ',body,flags=re.M)

def functions(ir):
 out={};header=[];footer=[];active=None;body=[]
 for line in ir.splitlines():
  if line.startswith('define '):active=name(line);body=[line]
  elif active:
   body.append(line)
   if line=='}':out[active]='\n'.join(body);active=None
  elif line.startswith(('attributes ','!')):footer.append(line)
  elif not line.startswith(';'):header.append(line)
 return out,header,footer

def declaration(body):
 line=next(line for line in body.splitlines() if line.startswith('define '))
 line=public(line).removesuffix(' {').replace('define hidden ','declare hidden ',1)
 return line.replace('alwaysinline ','')

def apply(gen, cache, target, force=False):
 started=time.monotonic();all_bodies={name(body):body for body in gen.all_function_bodies};all_bodies.pop(None,None)
 known={gen.fname(f,mode).removeprefix('@'):f for f in gen.fns if not f.external for mode in (('seq',) if f.effect or f.exported else ('par','seq'))}
 selected={symbol for symbol,f in known.items() if f.name in gen.library_names}
 pending=list(selected)
 while pending:
  symbol=pending.pop()
  for dependency in SYMBOL.findall(all_bodies[symbol]):
   if dependency not in all_bodies or dependency in selected:continue
   if dependency in known:
    return None,[],{'cache':'unsupported','reason':'library body depends on an application function'}
   selected.add(dependency);pending.append(dependency)
 references={symbol for n in selected for symbol in SYMBOL.findall(all_bodies[n])}
 base=[]
 for line in gen.module_header.splitlines():
  if line.startswith('@'):
   symbol=line.split(' ',1)[0].removeprefix('@')
   if symbol not in references:continue
   line=line.replace('internal global','hidden global').replace('private unnamed_addr constant','linkonce_odr hidden unnamed_addr constant')
  elif line.startswith('declare ') and not any('@'+symbol+'(' in line for symbol in references):continue
  base.append(line)
 # Source/debug comments and call-site-specific forced-inline annotations do
 # not belong to a reusable library. Application imports restore its policy.
 raw='\n'.join(base)+'\n'+'\n'.join('\n'.join(line for line in public(all_bodies[n]).replace('alwaysinline ','').splitlines() if not line.startswith(';')) for n in sorted(selected))+'\n'
 version=subprocess.check_output(['clang','--version'])
 flags=['--target='+target,'-O3','-ffunction-sections','-fdata-sections']+(['-mno-outline-atomics'] if target.startswith(('arm64','aarch64')) else [])
 key=digest(raw.encode()+version+repr(flags).encode());folder=Path(cache)/key
 folder.mkdir(parents=True,exist_ok=True,mode=0o700)
 manifest=folder/'manifest.json';optimized=folder/'library.ll';obj=folder/'library.o';hit=False
 try:
  data=json.loads(manifest.read_text())
  hit=not force and data['ir_sha256']==digest(optimized.read_bytes()) and data['object_sha256']==digest(obj.read_bytes())
 except (OSError,ValueError,KeyError):pass
 if not hit:
  with tempfile.TemporaryDirectory(prefix='prepare-',dir=folder) as temporary:
   stage=Path(temporary);source=stage/'source.ll';source.write_text(raw)
   result=subprocess.run(['clang',*flags,'-S','-emit-llvm',str(source),'-o',str(stage/'optimized.ll')],capture_output=True,text=True)
   if result.returncode:raise ValueError('native library optimization failed: '+result.stderr)
   content=(stage/'optimized.ll').read_text();defs,head,foot=functions(content)
   # Optimizer-created helpers must retain an ABI when imported into another
   # LLVM module. Their checked source remains part of the same cache key.
   content='\n'.join(head)+'\n'+'\n'.join(public(body) for body in defs.values())+'\n'+'\n'.join(foot)+'\n'
   (stage/'public.ll').write_text(content)
   result=subprocess.run(['clang',*flags,'-c',str(stage/'public.ll'),'-o',str(stage/'library.o')],capture_output=True,text=True)
   if result.returncode:raise ValueError('native library compilation failed: '+result.stderr)
   os.replace(stage/'public.ll',optimized);os.replace(stage/'library.o',obj)
   data={'ir_sha256':digest(optimized.read_bytes()),'object_sha256':digest(obj.read_bytes()),'sources':sorted({f.source for symbol,f in known.items() if symbol in selected}),'functions':sorted(selected),'target':target}
   temp=stage/'manifest.json';temp.write_text(json.dumps(data,indent=2)+'\n');os.replace(temp,manifest)
 return merge(gen,folder,key,data,hit,started)


def merge(gen,folder,key,data,hit=True,started=None):
 if started is None:started=time.monotonic()
 folder=Path(folder);optimized=folder/'library.ll';obj=folder/'library.o';selected=set(data['functions'])
 defs,head,foot=functions(optimized.read_text())
 app_bodies=[body for body in gen.funcs if name(body) not in selected]
 app_names={name(body) for body in app_bodies}
 app_header=[line for line in gen.module_header.splitlines() if not line.startswith('module asm ')]
 declarations={};globals_={};ordinary=[]
 def add(lines,from_library):
  for line in lines:
   if line.startswith('declare '):
    match=SYMBOL.search(line)
    if match:declarations[match[1]]=line
   elif line.startswith('@'):
    symbol=line.split(' ',1)[0]
    if symbol=='@ax_runtime_state':line='@ax_runtime_state = external hidden global [256 x i64], align 16'
    else:line=line.replace('private unnamed_addr constant','linkonce_odr hidden unnamed_addr constant')
    globals_[symbol]=line
   elif not from_library and line.strip():ordinary.append(line)
 add(app_header,False);add([line for line in head if not line.startswith('module asm ')],True)
 forced={gen.fname(f,mode).removeprefix('@') for f in gen.fns if f.name in gen.literal_inlined|gen.small_pure_inlined for mode in (('seq',) if f.effect or f.exported else ('par','seq'))}
 imported=[];needed={symbol for body in app_bodies for symbol in SYMBOL.findall(body) if symbol in defs and symbol not in app_names};visited=set()
 while needed:
  symbol=min(needed);needed.remove(symbol)
  if symbol in visited:continue
  visited.add(symbol);body=defs[symbol]
  if len(body.splitlines())<=16:
   body=re.sub(r'^define (?:(?:hidden|dso_local|internal|private) )*','define available_externally hidden ',body,flags=re.M)
   if symbol in forced:
    # Put the attribute before an optional numbered attribute group.
    body=re.sub(r'^(define .*?)( #(\d+))? \{$',lambda m:m[1]+' alwaysinline'+(m[2] or '')+' {',body,count=1,flags=re.M)
   imported.append(body)
   needed.update(dependency for dependency in SYMBOL.findall(body) if dependency in defs and dependency not in visited and dependency not in app_names)
  else:declarations[symbol]=declaration(body)
 # All actual LLVM definitions outside the cache are application code; an
 # available_externally body is an optimization hint, not emitted library code.
 merged='\n'.join(ordinary+[globals_[key] for key in sorted(globals_)]+[declarations[key] for key in sorted(declarations)])+'\n'+'\n'.join(imported+app_bodies)+'\n'+'\n'.join(foot)+'\n'
 return merged,[str(obj)],{'cache':'hit' if hit else 'miss','key':key,'directory':str(folder),'object_sha256':data['object_sha256'],'functions':len(selected),'seconds':round(time.monotonic()-started,4)}


def library_identity(program, roots, salt):
 roots=[Path(root).resolve() for root in roots]
 selected=lambda path:any(Path(path).resolve().is_relative_to(root) for root in roots)
 dependencies={path for path in program.sources if selected(path)};pending=list(dependencies)
 while pending:
  for path in program.dependencies.get(pending.pop(),[]):
   if path not in dependencies:dependencies.add(path);pending.append(path)
 sources=sorted((path,digest(program.sources[path].encode())) for path in dependencies)
 library=[fn for fn in program.fns if getattr(fn,'source',None) and selected(fn.source)]
 names=sorted(fn.name for fn in library)
 types={td.name:td for td in program.types};referenced=set()
 def visit_type(ty):
  if isinstance(ty,S.TArr):visit_type(ty.elem)
  elif isinstance(ty,S.TRef):visit_type(ty.resource)
  elif isinstance(ty,S.TFn):
   for item in (*ty.params,ty.ret):visit_type(item)
  elif isinstance(ty,S.TRec) and ty.name in types and ty.name not in referenced:
   referenced.add(ty.name)
   for _,field in types[ty.name].fields:visit_type(field)
 def visit_node(node):
  if isinstance(node,S.RecLit):visit_type(S.TRec(node.tname,()))
  for child in S.children(node):visit_node(child)
 for fn in library:
  for ty in [fn.ret,*[p.ty for p in fn.params]]:visit_type(ty)
  visit_node(fn.body)
 shapes=sorted((name,repr(types[name].fields),repr(types[name].variants),types[name].resource_drop) for name in referenced)
 signatures=sorted((f.name,repr(f.params),repr(f.ret)) for f in library)
 return digest(salt+repr((sources,signatures,shapes)).encode()),names


def lookup(cache, identity, names):
 try:
  root=Path(cache);index=json.loads((root/'index'/(identity+'.json')).read_text())
  if not re.fullmatch('[0-9a-f]{64}',index['key']):return None
  proof_path=root/'checked'/(identity+'.json')
  if index['checked_sha256']!=digest(proof_path.read_bytes()):return None
  proof=json.loads(proof_path.read_text())
  if proof['identity']!=identity or proof['key']!=index['key']:return None
  folder=root/index['key'];data=json.loads((folder/'manifest.json').read_text())
  if proof['manifest_sha256']!=digest((folder/'manifest.json').read_bytes()):return None
  if data['object_sha256']!=digest((folder/'library.o').read_bytes()):return None
  if data['ir_sha256']!=digest((folder/'library.ll').read_bytes()):return None
  if set(proof['capabilities'])!=set(names):return None
  if not all(set(caps)<={'fs','net','env','time','process','unsafe'} for caps in proof['capabilities'].values()):return None
  return dict(proof,folder=str(folder),data=data)
 except (OSError,ValueError,KeyError,AssertionError,TypeError):return None


def atomic_json(path,value):
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 fd,temporary=tempfile.mkstemp(prefix='publish-',dir=path.parent);os.close(fd)
 try:
  Path(temporary).write_text(json.dumps(value,sort_keys=True)+'\n');os.replace(temporary,path)
 finally:
  if Path(temporary).exists():Path(temporary).unlink()


def publish_index(cache, identity, names, report, checker):
 if report.get('cache') not in ('hit','miss'):return
 root=Path(cache);folder=Path(report['directory'])
 value={'identity':identity,'key':report['key'],'manifest_sha256':digest((folder/'manifest.json').read_bytes()),
        'capabilities':{name:sorted(checker.required_caps[name]) for name in names},
        'checked_obligations':sum(o['fn'] in names for o in checker.obligations),
        'checked_runtime_checks':sum(checker.function_runtime_checks.get(name,0) for name in names)}
 checked=root/'checked'/(identity+'.json');atomic_json(checked,value)
 atomic_json(root/'index'/(identity+'.json'),{'key':report['key'],'checked_sha256':digest(checked.read_bytes())})
