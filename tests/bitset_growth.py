#!/usr/bin/env python3
import json,os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def main():
 with tempfile.TemporaryDirectory(prefix='neo-bitset-growth-') as temp:
  binary=Path(temp)/'growth';before=os.environ.get('NEO_ALLOC_STATS');os.environ['NEO_ALLOC_STATS']='1'
  try:build('tests/fixtures/bitset_growth.neo',binary)
  finally:
   if before is None:os.environ.pop('NEO_ALLOC_STATS',None)
   else:os.environ['NEO_ALLOC_STATS']=before
  for mode in [0,1]:
   for n in [0,1,63,64,65,1000,10000,100000]+([1000000] if mode==0 else []):
    for workers in [1,4]:
     r=subprocess.run(RUNNER+[str(binary),str(mode),str(n)],capture_output=True,text=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90);assert r.returncode==0,r.stderr
     metrics,payload=r.stdout.split('\n',1);allocations,allocated,words=map(int,metrics.split());stride=1 if mode==0 else 67
     assert json.loads(payload)==list(range(0,n*stride,stride)),(n,mode,workers)
     assert words==(0 if n==0 else (n-1)*stride//64+1),(n,mode,metrics)
     assert allocations<=128 and allocated<=words*32+4096,(n,mode,metrics)
 print('PASS complete dense/sparse bitmap growth through 1M positions, exact independent ordered membership, bounded word storage and logarithmic allocation counts, 1/4 workers',flush=True)
if __name__=='__main__':main()
