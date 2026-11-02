#!/usr/bin/env python3
import json,os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def main():
 with tempfile.TemporaryDirectory(prefix='neo-token-growth-') as temp:
  binary=Path(temp)/'tokens';before=os.environ.get('NEO_ALLOC_STATS');os.environ['NEO_ALLOC_STATS']='1'
  try:build('tests/fixtures/json_token_growth.neo',binary)
  finally:
   if before is None:os.environ.pop('NEO_ALLOC_STATS',None)
   else:os.environ['NEO_ALLOC_STATS']=before
  for n in [0,1,1000,10000,100000]:
   data=json.dumps([{'n':i,'text':'item'} for i in range(n)],separators=(',',':'))
   for workers in [1,4]:
    r=subprocess.run(RUNNER+[str(binary)],input=data,capture_output=True,text=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90);assert r.returncode==0,r.stderr
    count,total,keys,allocations,allocated=map(int,r.stdout.split());assert (count,total,keys)==(6*n+2,n*(n-1)//2,n),(n,r.stdout)
    # Formatting the three metric words happens before the final counter read.
    assert allocations<=4 and allocated<=128,(n,workers,r.stdout)
 print('PASS complete 1k/10k/100k object token traversal, independent token/key/integer totals and constant allocation bounds, 1/4 workers',flush=True)
if __name__=='__main__':main()
