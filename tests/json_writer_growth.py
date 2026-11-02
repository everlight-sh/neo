#!/usr/bin/env python3
import json,os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build
def main():
    with tempfile.TemporaryDirectory(prefix='neo-writer-growth-') as tmp:
        binary=Path(tmp)/'writer';previous=os.environ.get('NEO_ALLOC_STATS');os.environ['NEO_ALLOC_STATS']='1'
        try:build('tests/fixtures/json_writer_growth.neo',binary)
        finally:
            if previous is None:os.environ.pop('NEO_ALLOC_STATS',None)
            else:os.environ['NEO_ALLOC_STATS']=previous
        for n in [1000,10000,100000]:
            for mode in range(4):
                expected=list(range(n)) if mode==0 else [dict(i=i,name='item') for i in range(n)] if mode in [1,3] else [dict(i=7,name='item')]*n
                for workers in [1,4]:
                    run=subprocess.run(RUNNER+[str(binary),str(mode),str(n)],capture_output=True,text=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90)
                    assert run.returncode==0,run.stderr
                    metrics,payload=run.stdout.split('\n',1);requests,requested=map(int,metrics.split())
                    assert json.loads(payload)==expected,(n,mode,workers)
                    assert requests<=(128 if mode in [0,2] else n*2+128) and requested<=512*n+65536,(n,mode,workers,metrics)
    print('PASS structured JSON/fragment growth at 1k/10k/100k, complete Python results, linear bytes and logarithmic reused-fragment allocation requests, 1/4 workers',flush=True)
if __name__=='__main__':main()
