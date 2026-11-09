#!/usr/bin/env python3
"""Native library reuse, ABI/source invalidation, effects and corruption checks."""
import json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
 with tempfile.TemporaryDirectory(prefix='neo-native-libraries-') as temporary:
  base=Path(temporary);dep=base/'dependency';dep.mkdir();(dep/'neo.toml').write_text('[package]\nname="cache-fixture"\nversion="1"\n')
  library=dep/'lib.neo';library.write_text('fn inc(n:i64)->i64=n+1\neffect(fs) fn read_value(n:i64)->i64=n+1\neffect fn invoke(callback:Effect<net>(i64)->i64,n:i64)->i64=callback(n)\n')
  cache=base/'cache';apps=[]
  for name in ('one','two'):
   app=base/name;app.mkdir();apps.append(app/'main.neo')
  def source(path,body):path.write_text('import '+json.dumps(str(library))+'\n'+body+'\nfn sentinel()->Arr u8 _="APPLICATION_SENTINEL_MUST_NOT_BE_CACHED"\n')
  def build(path,success=True):
   binary=path.parent/'app'
   run=subprocess.run([sys.executable,'-m','neoc','build',str(path),'-o',str(binary),'--report','--library-cache',str(cache),'--library-root',str(library)],cwd=ROOT,capture_output=True,text=True)
   assert (run.returncode==0)==success,run.stdout+run.stderr
   report=json.loads(run.stdout)
   if success:assert not report['undefined_symbols']
   return report,binary
  def execute(binary,value,expected):assert subprocess.check_output([str(binary),str(value)],text=True)==str(expected)+'\n'
  source(apps[0],'fn main(n:i64)->i64=inc(n)');first,binary=build(apps[0]);execute(binary,41,42)
  assert first['native_libraries']['cache']=='miss'
  artifact=Path(first['native_libraries']['directory']);assert b'APPLICATION_SENTINEL' not in (artifact/'library.o').read_bytes() and 'APPLICATION_SENTINEL' not in (artifact/'library.ll').read_text()
  assert 'APPLICATION_SENTINEL' not in (artifact/'hints.ll').read_text()
  # Object-local inlining constraints must not be replayed at application
  # sites, where specialization has a different configured expansion budget.
  assert not any('call ' in line and ' noinline' in line for line in (artifact/'hints.ll').read_text().splitlines())
  # Constant booleans specialize allocator policy even with an effectful
  # helper. Prepared objects and application hints must retain that policy.
  header=next(line for line in (artifact/'hints.ll').read_text().splitlines() if line.startswith('define ') and '@ax_rt_heap_small_kind__seq(' in line)
  assert 'alwaysinline' in header
  shutil.rmtree(apps[0].parent/'.neo-build');again,binary=build(apps[0]);execute(binary,41,42)
  assert again['build']['cache']=='miss' and again['native_libraries']['cache']=='hit' and again['native_libraries']['prechecked_obligations']>0
  assert first['binary_sha256']==again['binary_sha256'],'Cache warmth changed emitted application code'
  (artifact/'hints.ll').write_text('corrupt optimization hints')
  shutil.rmtree(apps[0].parent/'.neo-build');restored,binary=build(apps[0]);execute(binary,41,42)
  assert restored['native_libraries']['cache']=='miss' and 'prechecked_obligations' not in restored['native_libraries']
  source(apps[1],'fn main(n:i64)->i64=inc(n)+10');second,binary=build(apps[1]);execute(binary,41,52)
  assert second['build']['cache']=='miss' and second['native_libraries']['key']==first['native_libraries']['key'] and second['native_libraries']['cache']=='hit'
  source(apps[1],'effect(net) fn main(n:i64)->i64=read_value(n)');bad,_=build(apps[1],False);assert 'missing effect capabilities: fs' in json.dumps(bad)
  source(apps[1],'effect(net) fn callback(n:i64)->i64=n\neffect(fs) fn main(n:i64)->i64=invoke(function(callback),n)');bad,_=build(apps[1],False);assert 'missing effect capabilities: net' in json.dumps(bad)
  source(apps[1],'fn main(n:i64{n>=0})->i64=let a=arr(i in 0..n) i in a[n]');bad,_=build(apps[1],False);assert 'unproven obligations' in json.dumps(bad)
  library.write_text('fn inc(n:i64)->i64=n+2\neffect(fs) fn read_value(n:i64)->i64=n+1\n')
  source(apps[1],'fn main(n:i64)->i64=inc(n)');changed,binary=build(apps[1]);execute(binary,41,43)
  assert changed['native_libraries']['key']!=first['native_libraries']['key'] and 'prechecked_obligations' not in changed['native_libraries']
  types=dep/'types.neo';types.write_text('type Box={value:i64}\n');library.write_text('import "types.neo"\nfn value(box:Box)->i64=box.value\n')
  source(apps[1],'fn main(n:i64)->i64=value(Box {value=n})');old,binary=build(apps[1]);execute(binary,42,42)
  types.write_text('type Box={padding:i64,value:i64}\n');source(apps[1],'fn main(n:i64)->i64=value(Box {padding=99,value=n})')
  new,binary=build(apps[1]);execute(binary,42,42);assert new['native_libraries']['key']!=old['native_libraries']['key']
  (Path(new['native_libraries']['directory'])/'library.o').write_bytes(b'corrupt')
  shutil.rmtree(apps[1].parent/'.neo-build');repaired,binary=build(apps[1]);execute(binary,42,42);assert repaired['native_libraries']['cache']=='miss'
  library.write_text('fn invalid(n:i64{n>=0})->i64=let a=arr(i in 0..n) i in a[n]\nfn value()->i64=42\n')
  source(apps[1],'fn main()->i64=value()');bad,_=build(apps[1],False);assert 'unproven obligations' in json.dumps(bad),'Unused dependency body escaped verification'
  library.write_text('import "std:io"\nfn formatted(n:i64)->Arr u8 _=concat("library:",int_text(n)," end")\n')
  source(apps[1],'effect(fs) fn main(n:i64)->unit=let printed=print_out(concat("app:",int_text(n)," / ",formatted(n),"\\n")) in noop()')
  formatted,binary=build(apps[1])
  assert subprocess.check_output([str(binary),'-9223372036854775808'],text=True)=='app:-9223372036854775808 / library:-9223372036854775808 end\n'
  shutil.rmtree(apps[1].parent/'.neo-build')
  reused,binary=build(apps[1]);assert reused['native_libraries']['cache']=='hit'
  assert subprocess.check_output([str(binary),'42'],text=True)=='app:42 / library:42 end\n'
  # Warm prechecking must preserve the checked ownership facts, not turn all
  # dependency returns into unknown aliases. Exercise arrays and records,
  # including an intentional borrowed alias that must stay shared.
  library.write_text('type Packet={bytes:Arr i64 _}\nfn fresh(n:i64{n>=0})->Arr i64 _=arr(i in 0..n) i\nfn shared(borrow values:Arr i64 _)->Arr i64 _=values\nfn packet(n:i64{n>=0})->Packet=Packet {bytes=fresh(n)}\nfn observe(values:Arr i64 _)->i64=len(values)\n')
  source(apps[1],'fn main(n:i64{n>0})->i64=let original=fresh(n) in check len(original)==n in let alias=shared(original) in let changed=set(original,0,99) in let item=packet(n) in check len(alias)==n && len(changed)==n in observe(item.bytes)+alias[0]+changed[0]')
  cold,binary=build(apps[1]);execute(binary,42,141)
  shutil.rmtree(apps[1].parent/'.neo-build');warm,binary=build(apps[1]);execute(binary,42,141)
  assert warm['native_libraries']['cache']=='hit'
  assert warm['binary_sha256']==cold['binary_sha256'],'Prechecking changed ownership lowering for managed values'
  index=next(path for path in (cache/'index').glob('*.json') if json.loads(path.read_text())['key']==warm['native_libraries']['key'])
  item=json.loads(index.read_text());proof=cache/'checked'/(index.stem+'.json');facts=json.loads(proof.read_text())
  assert any(value==[] for name,value in facts['return_aliases'].items() if name.endswith('_fresh'))
  assert any(value==[0] for name,value in facts['return_aliases'].items() if name.endswith('_shared'))
  # Even internally consistent cache files must reject invalid parameter indexes.
  key=next(name for name in facts['return_aliases'] if name.endswith('_fresh'))
  facts['return_aliases'][key]=[999];proof.write_text(json.dumps(facts))
  import hashlib
  item['checked_sha256']=hashlib.sha256(proof.read_bytes()).hexdigest();index.write_text(json.dumps(item))
  shutil.rmtree(apps[1].parent/'.neo-build');rechecked,binary=build(apps[1]);execute(binary,42,141)
  assert 'prechecked_obligations' not in rechecked['native_libraries']
  assert json.loads(proof.read_text())['return_aliases'][key]==[]
  # Import the larger JSON helper bodies, including cold decoder paths. Cold
  # attributes must never acquire a conflicting alwaysinline annotation.
  library.write_text('import "std:json"\nfn parse(raw:Arr u8 _)->JsonResult=json_parse(raw)\nfn title(value:Json)->BytesResult=json_text(json_get(value,"title").value)\n')
  source(apps[1],'import "std:io"\neffect(fs) fn main(n:i64)->unit=let value=concat("caf\\xc3\\xa9 < & \\"> ",int_text(n)) in let parsed=parse(concat("{\\"title\\":",json_quote(value),"}")) in check parsed.ok in let decoded=title(parsed.value) in check decoded.ok in let printed=print_out(decoded.value) in noop()')
  cold,binary=build(apps[1]);assert subprocess.check_output([str(binary),'42'])=='café < & "> 42'.encode()
  shutil.rmtree(apps[1].parent/'.neo-build');warm,binary=build(apps[1]);assert warm['native_libraries']['cache']=='hit'
  assert subprocess.check_output([str(binary),'42'])=='café < & "> 42'.encode()
  assert cold['binary_sha256']==warm['binary_sha256'],'Prechecking changed JSON/decoder ownership or policy'
  # Callbacks resident in the prepared object must resume with the same ABI,
  # and the warm prechecked path must preserve owned byte results.
  library.write_text('import "std:async"\neffect(fs,net,env,time,process) fn produce(capture:Arr u8 _)->Arr u8 _=let waited=sleep_ms(2) in capture\n')
  source(apps[1],'import "std:async"\neffect fn main(n:i64)->i64=let deadline=deadline_after(1000) in using task=async_bytes(function(produce),int_text(n),deadline.value) in let result=async_bytes_await(task,deadline.value) in check result.ok in int_parse(result.value).value')
  cold,binary=build(apps[1]);execute(binary,42,42)
  shutil.rmtree(apps[1].parent/'.neo-build');warm,binary=build(apps[1]);execute(binary,42,42)
  assert warm['native_libraries']['cache']=='hit' and warm['native_libraries']['prechecked_obligations']>0
  assert cold['binary_sha256']==warm['binary_sha256'],'Prepared callback resumption changed between cold/warm checks'
 print('PASS new-project dependency reuse; deterministic cold/warm code; application checks/effects; dependency and imported-type invalidation; corrupt-object repair; no application code in library cache')
if __name__=='__main__':main()
