"""Content-addressed native libraries built from checked Neo LLVM IR.

Caches contain dependency code, never application bodies. Pre-optimization
dependency bodies remain available to the application inliner. All code is
statically linked.
"""
import hashlib,json,os,re,subprocess,tempfile,time
from pathlib import Path
from . import syntax as S

SYMBOL=re.compile(r'@([^\s(),]+)')
HEADER=re.compile(r'^define (.*?)@([^\s(]+)\(',re.M)
OBJECT_INLINE_EXPANSION = 8_192
PURE_OBJECT_INLINE_EXPANSION = 32_768

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

def inline_policy(gen, callers, bodies=None):
 """Apply source heuristics only while their lowered IR stays affordable."""
 eligible=lambda f:not (f.external or f.exported or getattr(f,'cold',False)) and not gen.is_recursive(f)
 chosen={f.name for f in gen.fns if f.name in gen.library_names and eligible(f) and
         (getattr(f,'inline',False) or gen.policy_inline_enabled and not f.effect and gen.node_count(f)<=gen.inline_budget)}
 def visit(node):
  if gen.policy_inline_enabled and isinstance(node,S.Call):
   target=gen.fn_map.get(node.name)
   if target and target.name in gen.library_names and eligible(target):
    if (any(isinstance(a,S.BoolLit) for a in node.args) and gen.node_count(target)<=256 or
        not target.effect and any(isinstance(a,S.Str) for a in node.args) and gen.node_count(target)<=160):chosen.add(target.name)
  for child in S.children(node):visit(child)
 for f in callers:
  if not f.external:visit(f.body)
 symbols={gen.fname(f,mode).removeprefix('@') for f in gen.fns if f.name in chosen
          for mode in (('seq',) if f.effect or f.exported else ('par','seq'))}
 required={gen.fname(f,mode).removeprefix('@') for f in gen.fns if f.name in chosen and getattr(f,'inline',False)
           for mode in (('seq',) if f.effect or f.exported else ('par','seq'))}
 from .inline_cost import bounded_policy
 if bodies is None:bodies={name(body):body for body in gen.all_function_bodies}
 return bounded_policy(bodies,symbols,required,expansion_limit=0)

def bound_calls(gen, bodies, policy, library=False):
 from .inline_cost import bounded_calls
 required={gen.fname(f,mode).removeprefix('@') for f in gen.fns if getattr(f,'inline',False)
           for mode in (('seq',) if f.effect or f.exported else ('par','seq'))}
 if not library:
  return bounded_calls(bodies,policy,required,gen.inline_expansion)
 limit=min(gen.inline_expansion,OBJECT_INLINE_EXPANSION)
 # Pure record-producing helpers benefit from exposing their fields to callers.
 # Retain the smaller budget in effectful I/O loops and generated helpers.
 pure_limit=min(gen.inline_expansion,PURE_OBJECT_INLINE_EXPANSION)
 caller_limits={gen.fname(f,mode).removeprefix('@'):pure_limit
                for f in gen.fns if not (f.effect or f.external)
                for mode in (('seq',) if f.exported else ('par','seq'))}
 return bounded_calls(bodies,policy,required,limit,caller_limits)

def force_inline(body):
 return re.sub(r'^(define .*?)( #(\d+))? \{$',lambda m:m[1]+' alwaysinline'+(m[2] or '')+' {',body,count=1,flags=re.M)

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
 # Preserve pre-optimization bodies for application specialization. Running
 # scalar replacement/inlining separately first can permanently hide record
 # fields and ownership flags behind optimizer-created helper boundaries.
 raw_defs,raw_head,raw_foot=functions(raw)
 policy=inline_policy(gen,[f for f in gen.fns if f.name in gen.library_names],raw_defs)
 # Optimization hints precede caller-local budgets as well as LLVM passes.
 # A dependency's conservative object budget must not constrain a different
 # application's specialization context or its configured expansion budget.
 hints_ir='\n'.join(raw_head)+'\n'+'\n'.join(force_inline(public(body)) if symbol in policy else public(body) for symbol,body in raw_defs.items())+'\n'+'\n'.join(raw_foot)+'\n'
 raw_defs=bound_calls(gen,raw_defs,policy,library=True)
 raw='\n'.join(raw_head)+'\n'+'\n'.join(force_inline(public(body)) if symbol in policy else public(body) for symbol,body in raw_defs.items())+'\n'+'\n'.join(raw_foot)+'\n'
 version=subprocess.check_output(['clang','--version'])
 flags=['--target='+target,'-O3','-ffunction-sections','-fdata-sections']+(['-mno-outline-atomics'] if target.startswith(('arm64','aarch64')) else [])
 key=digest(raw.encode()+hints_ir.encode()+version+repr(flags).encode());folder=Path(cache)/key
 folder.mkdir(parents=True,exist_ok=True,mode=0o700)
 manifest=folder/'manifest.json';optimized=folder/'library.ll';hints=folder/'hints.ll';obj=folder/'library.o';hit=False
 try:
  data=json.loads(manifest.read_text())
  hit=not force and data['ir_sha256']==digest(optimized.read_bytes()) and data['hints_sha256']==digest(hints.read_bytes()) and data['object_sha256']==digest(obj.read_bytes())
 except (OSError,ValueError,KeyError):pass
 if not hit:
  with tempfile.TemporaryDirectory(prefix='prepare-',dir=folder) as temporary:
   stage=Path(temporary);source=stage/'source.ll';source.write_text(raw)
   result=subprocess.run(['clang',*flags,'-S','-emit-llvm',str(source),'-o',str(stage/'optimized.ll')],capture_output=True,text=True)
   if result.returncode:raise ValueError('native library optimization failed: '+result.stderr)
   content=(stage/'optimized.ll').read_text();defs,head,foot=functions(content)
   # Retain the optimized dependency ABI across the final code generation pass.
   content='\n'.join(head)+'\n'+'\n'.join(public(body) for body in defs.values())+'\n'+'\n'.join(foot)+'\n'
   (stage/'public.ll').write_text(content)
   result=subprocess.run(['clang',*flags,'-c',str(stage/'public.ll'),'-o',str(stage/'library.o')],capture_output=True,text=True)
   if result.returncode:raise ValueError('native library compilation failed: '+result.stderr)
   os.replace(stage/'public.ll',optimized);os.replace(stage/'library.o',obj)
   hint_source=stage/'hints.ll';hint_source.write_text(hints_ir);os.replace(hint_source,hints)
   data={'ir_sha256':digest(optimized.read_bytes()),'hints_sha256':digest(hints.read_bytes()),'object_sha256':digest(obj.read_bytes()),'sources':sorted({f.source for symbol,f in known.items() if symbol in selected}),'functions':sorted(selected),'target':target}
   temp=stage/'manifest.json';temp.write_text(json.dumps(data,indent=2)+'\n');os.replace(temp,manifest)
 return merge(gen,folder,key,data,hit,started)


def merge(gen,folder,key,data,hit=True,started=None):
 if started is None:started=time.monotonic()
 folder=Path(folder);obj=folder/'library.o';selected=set(data['functions'])
 defs,head,foot=functions((folder/'hints.ll').read_text())
 app_bodies=[body for body in gen.funcs if name(body) not in selected]
 # Generated formatting/escaping helpers also occur in the module header.
 # LLVM may retain a specialized fastcc version in the optimized library.
 # Give application copies distinct names: deduplicating declarations alone
 # would leave library calls targeting a helper with a different ABI.
 header=gen.module_header
 helpers,_,_=functions(header)
 rename={symbol:symbol+'_app_'+key[:12] for symbol in helpers if symbol in defs}
 def application_symbols(text):
  return SYMBOL.sub(lambda match:'@'+rename.get(match[1],match[1]),text)
 header=application_symbols(header)
 app_bodies=[application_symbols(body) for body in app_bodies]
 app_names={name(body) for body in app_bodies}
 app_header=[line for line in header.splitlines() if not line.startswith('module asm ')]
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
 forced=inline_policy(gen,gen.fns,{**defs,**{name(body):body for body in app_bodies}})
 # Restore Neo's small-pure-helper policy at application call sites. A
 # cache boundary must not silently switch off the monolithic inlining policy.
 imported=[];needed={symbol for body in app_bodies for symbol in SYMBOL.findall(body) if symbol in defs and symbol not in app_names};visited=set()
 while needed:
  symbol=min(needed);needed.remove(symbol)
  if symbol in visited:continue
  # Hints were prepared in a different caller context; their old policy must
  # not override the expansion budget recomputed for this application.
  visited.add(symbol);body=defs[symbol].replace('alwaysinline ','')
  # Optimized ownership/checking code can exceed 512 lines even for a small
  # source helper (e.g. validated JSON slicing/indexing). Import its body so
  # LLVM can specialize away unused record fields at an application call.
  # Bodies remain optimization-only; the prepared object owns emitted code.
  if symbol in forced or len(body.splitlines())<=2048:
   body=re.sub(r'^define (?:(?:hidden|dso_local|internal|private) )*','define available_externally hidden ',body,flags=re.M)
   if symbol in forced:
    # Put the attribute before an optional numbered attribute group.
    if 'alwaysinline' not in body.splitlines()[0]:body=force_inline(body)
   imported.append(body)
   needed.update(dependency for dependency in SYMBOL.findall(body) if dependency in defs and dependency not in visited and dependency not in app_names)
  else:declarations[symbol]=declaration(body)
 # All actual LLVM definitions outside the cache are application code; an
 # available_externally body is an optimization hint, not emitted library code.
 bounded=bound_calls(gen,{name(body):body for body in imported+app_bodies},forced)
 merged='\n'.join(ordinary+[globals_[key] for key in sorted(globals_)]+[declarations[key] for key in sorted(declarations)])+'\n'+'\n'.join(bounded.values())+'\n'+'\n'.join(foot)+'\n'
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


def lookup(cache, identity, names, functions):
 try:
  root=Path(cache);index=json.loads((root/'index'/(identity+'.json')).read_text())
  if not re.fullmatch('[0-9a-f]{64}',index['key']):return None
  proof_path=root/'checked'/(identity+'.json')
  if index['checked_sha256']!=digest(proof_path.read_bytes()):return None
  proof=json.loads(proof_path.read_text())
  if proof['identity']!=identity or proof['key']!=index['key']:return None
  if proof.get('format')!=2:return None
  folder=root/index['key'];data=json.loads((folder/'manifest.json').read_text())
  if proof['manifest_sha256']!=digest((folder/'manifest.json').read_bytes()):return None
  if data['object_sha256']!=digest((folder/'library.o').read_bytes()):return None
  if data['ir_sha256']!=digest((folder/'library.ll').read_bytes()):return None
  if data['hints_sha256']!=digest((folder/'hints.ll').read_bytes()):return None
  if set(proof['capabilities'])!=set(names):return None
  if not all(set(caps)<={'fs','net','env','time','process','unsafe'} for caps in proof['capabilities'].values()):return None
  signatures={fn.name:fn for fn in functions}
  aliases=proof['return_aliases']
  if not isinstance(aliases,dict) or set(aliases)!=set(names):return None
  for name,indexes in aliases.items():
   fn=signatures[name]
   # Arity is available before checking; record-field types are resolved by
   # the checker later. An extra scalar index would only be conservative.
   if not isinstance(indexes,list) or any(type(i) is not int or i< -1 or i>=len(fn.params) for i in indexes):return None
   if sorted(set(indexes))!=indexes:return None
  return dict(proof,folder=str(folder),data=data)
 except (OSError,ValueError,KeyError,AssertionError,TypeError):return None


def atomic_json(path,value):
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 fd,temporary=tempfile.mkstemp(prefix='publish-',dir=path.parent);os.close(fd)
 try:
  Path(temporary).write_text(json.dumps(value,sort_keys=True)+'\n');os.replace(temporary,path)
 finally:
  if Path(temporary).exists():Path(temporary).unlink()


def publish_index(cache, identity, names, report, checker, return_aliases):
 if report.get('cache') not in ('hit','miss'):return
 root=Path(cache);folder=Path(report['directory'])
 value={'format':2,'identity':identity,'key':report['key'],'manifest_sha256':digest((folder/'manifest.json').read_bytes()),
        'capabilities':{name:sorted(checker.required_caps[name]) for name in names},
        'return_aliases':{name:sorted(return_aliases[name]) for name in names},
        'checked_obligations':sum(o['fn'] in names for o in checker.obligations),
        'checked_runtime_checks':sum(checker.function_runtime_checks.get(name,0) for name in names)}
 checked=root/'checked'/(identity+'.json');atomic_json(checked,value)
 atomic_json(root/'index'/(identity+'.json'),{'key':report['key'],'checked_sha256':digest(checked.read_bytes())})
