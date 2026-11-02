#!/usr/bin/env python3
"""Section collection preserves unused user ABI entries and cached imports."""
import json,os,platform,shlex,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 with tempfile.TemporaryDirectory(prefix='neo-native-sections-') as temp:
  root=Path(temp);(root/'lib').mkdir();(root/'lib/functions.neo').write_text('fn twice(x:i64) -> i64 = x*2\nexport fn public_entry(x:i64) -> i64 = x+17\n')
  source=root/'main.neo';source.write_text('import "lib/functions.neo" fn main(x:i64) -> i64 = twice(x)\n')
  for cached in [False,True]:
   binary=root/('cached' if cached else 'whole');args=['python3','-m','neoc','build',str(source),'-o',str(binary),'--report']
   if cached:args+=['--library-cache',str(root/'cache'),'--library-root',str(root/'lib')]
   r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True);assert r.returncode==0,(r.stdout[-3000:],r.stderr)
   assert json.loads(r.stdout)['undefined_symbols']==[]
   symbols=subprocess.check_output(['nm',str(binary)],text=True);symbol='_public_entry' if platform.system()=='Darwin' else 'public_entry'
   assert any(line.split()[-1:]==[symbol] for line in symbols.splitlines()),symbols
   assert subprocess.check_output(shlex.split(os.environ.get('NEO_RUNNER',''))+[str(binary),'21'],text=True).strip()=='42'
   if platform.system()=='Linux':
    assert 'INTERP' not in subprocess.check_output(['readelf','-l',str(binary)],text=True)
    assert 'NEEDED' not in subprocess.check_output(['readelf','-d',str(binary)],text=True)
 print('PASS unused explicit ABI exports and native cached-library entry points survive section collection; complete output and no runtime imports',flush=True)
if __name__=='__main__':main()
