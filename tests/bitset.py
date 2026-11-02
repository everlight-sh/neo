#!/usr/bin/env python3
import json,os,random,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def main():
 rng=random.Random(261107);operations=[];model=set();expected=[]
 for i in range(550):
  index=rng.choice(list(range(140))+[0,1,63,64,65,127,128,129,255,256,511,512,1023,4096,65535]);remove=bool(rng.randrange(2));operations.append(dict(index=index,remove=remove))
  if remove:model.discard(index)
  else:model.add(index)
  expected.append(sorted(model))
 operations += [dict(index=i,remove=True) for i in sorted(model)]
 for i in sorted(model):model.discard(i);expected.append(sorted(model))
 with tempfile.TemporaryDirectory(prefix='neo-bitset-') as temp:
  binary=Path(temp)/'bits';build('tests/fixtures/bitset.neo',binary)
  for workers in [1,4]:
   result=subprocess.run(RUNNER+[str(binary)],input=json.dumps(operations),capture_output=True,text=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90)
   assert result.returncode==0,result.stderr
   assert json.loads(result.stdout)==expected
 print(f'PASS {len(operations)} complete independent bitmap states: repeats, boundaries, sparse high bits, removal to empty, ordered iteration and retained aliases, 1/4 workers',flush=True)
if __name__=='__main__':main()
