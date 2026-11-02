#!/usr/bin/env python3
import json,os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build
def main():
    with tempfile.TemporaryDirectory(prefix='neo-sort-cases-') as tmp:
        binary=Path(tmp)/'sort';build('tests/fixtures/vector_sort_probe.neo',binary)
        for n in [0,1,2,3,4,5,8,17,127,1024,4097]:
            for mode in range(4):
                values=[n-i if mode==0 else (i*73+19)%101-50 if mode==1 else [-2**63,2**63-1,0][i%3] if mode==2 else i for i in range(n)]
                for workers in [1,4]:
                    result=subprocess.run(RUNNER+[str(binary),str(mode),str(n)],env={**os.environ,'NEO_THREADS':str(workers)},capture_output=True,text=True,timeout=30)
                    assert result.returncode==0 and json.loads(result.stdout)==sorted(values),(mode,n,workers,result.stderr)
    print('PASS 88 complete sort results and preserved input aliases: empty/single/odd sizes, duplicates, reversed/sorted and signed extremes, 1/4 workers',flush=True)
if __name__=='__main__':main()
