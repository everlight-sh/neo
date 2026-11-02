#!/usr/bin/env python3
"""Bit-pattern semantics across folding and native backends."""
import json,os,random,shlex,subprocess,sys,tempfile
from pathlib import Path
from kernel_runtime_smoke import audit
ROOT=Path(__file__).resolve().parents[1];RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))
def signed(n):return (n+(1<<63))%(1<<64)-(1<<63)
def main():
 rng=random.Random(246425);values=[0,1,-1,127,128,255,256,-(1<<63),(1<<63)-1,0x0102030405060708]
 values += [rng.randrange(-(1<<63),1<<63) for _ in range(40)]
 with tempfile.TemporaryDirectory(prefix='neo-bitwise-') as tmp:
  for fold in ('0','1'):
   binary=Path(tmp)/('bits-'+fold)
   subprocess.run([sys.executable,'-m','neoc','build','tests/fixtures/bitwise.neo','-o',str(binary)],cwd=ROOT,env={**os.environ,'NEO_FOLD':fold},capture_output=True,text=True,check=True);audit(binary)
   for a in values:
    b=rng.choice(values);expected=[signed(a&b),signed(a|b),signed(a^b),signed(int.from_bytes((a%(1<<64)).to_bytes(8,'big'),'little')),signed(((a%(1<<64))*(b%(1<<64)))>>64),127]
    for mode,want in enumerate(expected):
     r=subprocess.run(RUNNER+[str(binary),str(mode),str(a),str(b)],capture_output=True,text=True,check=True,timeout=15)
     assert int(r.stdout)==want,(fold,mode,a,b,r.stdout,want)
   print(f'PASS bitwise folding={fold}: {len(values)*6} high-bit/negative/random patterns',flush=True)
if __name__=='__main__':main()
