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
  shutil.rmtree(apps[0].parent/'.neo-build');again,binary=build(apps[0]);execute(binary,41,42)
  assert again['build']['cache']=='miss' and again['native_libraries']['cache']=='hit' and again['native_libraries']['prechecked_obligations']>0
  assert first['binary_sha256']==again['binary_sha256'],'Cache warmth changed emitted application code'
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
 print('PASS new-project dependency reuse; deterministic cold/warm code; application checks/effects; dependency and imported-type invalidation; corrupt-object repair; no application code in library cache')
if __name__=='__main__':main()
