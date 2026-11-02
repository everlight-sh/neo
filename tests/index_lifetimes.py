#!/usr/bin/env python3
"""Indexed loads retain parents across consuming/recycling index expressions."""
import os,subprocess,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 with tempfile.TemporaryDirectory(prefix='neo-index-lifetimes-') as t:
  binary=Path(t)/'probe';r=subprocess.run(['python3','-m','neoc','build',str(ROOT/'tests/fixtures/index_lifetimes.neo'),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
  assert r.returncode==0,(json.loads(r.stdout).get('errors') or [x for x in json.loads(r.stdout).get('obligations',[]) if x.get('status') not in ('proven','checked')] if r.stdout.startswith('{') else r.stdout[:2000],r.stderr[-2000:])
  checked=0
  for threads in ['1','4']:
   for n in [1,2,8,31,128,1024,8192]:
    for mode in range(10):
     expected=42 if mode in [1,3] else 256 if mode==7 else 120 if mode==8 else 128
     r=subprocess.run([str(binary),str(n),str(mode)],capture_output=True,text=True,timeout=30,env={**os.environ,'NEO_THREADS':threads})
     assert r.returncode==0 and r.stdout==str(expected)+'\n',(n,mode,threads,r.returncode,r.stdout,r.stderr)
     checked+=1
 print(f'PASS {checked} independent indexed-parent lifetimes: consuming/recycling callbacks, scalar/array/record fields, nested holders, temporaries, observers, retained aliases and heap children; 1/4 workers',flush=True)
if __name__=='__main__':main()
