#!/usr/bin/env python3
import json,os,random,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build
def main():
    rng=random.Random(261030);keys=[b'',b'\0',bytes(range(256)),b'x'*500]+[bytes(rng.randrange(256) for _ in range(rng.randrange(1,48))) for _ in range(100)]
    commands=[];expected=[];model={}
    for i in range(1400):
        op=rng.choice(['entry']*5+['put','delete']);key=rng.choice(keys);value=bytes(rng.randrange(256) for _ in range(rng.randrange(50)))
        fresh=key not in model
        if fresh:model[key]=value
        selected=model[key]
        if op=='put':model[key]=value
        elif op=='delete':model.pop(key)
        commands.append(dict(op=op,key=key.hex(),value=value.hex()))
        expected.append(dict(inserted=fresh,value=selected.hex(),after=model[key].hex() if key in model else None,size=len(model)))
    with tempfile.TemporaryDirectory(prefix='neo-entry-') as tmp:
        binary=Path(tmp)/'entry';build('tests/fixtures/hashmap_entry.neo',binary)
        for workers in [1,4]:
            result=subprocess.run(RUNNER+[str(binary)],input=json.dumps(commands),capture_output=True,text=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90)
            assert result.returncode==0,result.stderr
            assert json.loads(result.stdout)==expected,workers
    with tempfile.TemporaryDirectory(prefix='neo-entry-growth-') as tmp:
        binary=Path(tmp)/'growth';prior=os.environ.get('NEO_ALLOC_STATS');os.environ['NEO_ALLOC_STATS']='1'
        try:build('tests/fixtures/hashmap_entry_alloc.neo',binary)
        finally:
            if prior is None:os.environ.pop('NEO_ALLOC_STATS',None)
            else:os.environ['NEO_ALLOC_STATS']=prior
        for n in [1000,10000,100000]:
            for workers in [1,4]:
                result=subprocess.run(RUNNER+[str(binary),str(n)],capture_output=True,text=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90)
                assert result.returncode==0,result.stderr
                checksum,requests,requested=map(int,result.stdout.split())
                assert checksum==7*n*(n-1)//2 and requests<=64 and requested<=512*n+1048576,(n,workers,result.stdout)
    print('PASS map-entry growth at 1k/10k/100k: logarithmic allocation requests and linear bytes, 1/4 workers',flush=True)
    print('PASS 1,400 independent map-entry/overwrite/delete results, binary keys, growth/tombstones, held snapshots and returned-value aliases, 1/4 workers',flush=True)
if __name__=='__main__':main()
