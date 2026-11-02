#!/usr/bin/env python3
import json,os,random,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build
def main():
    rng=random.Random(261031);cases=[]
    for n in [*range(35),63,64,65,127,128,129,1024,4097]:
        a=bytes(rng.randrange(256) for _ in range(n));cases.extend([(a,a),(a,b'x'+a),(a,a+b'x')])
        for at in range(n) if n<128 else [0,1,7,8,n//2,n-8,n-2,n-1]:
            b=bytearray(a);b[at]^=1;cases.append((a,bytes(b)))
    with tempfile.TemporaryDirectory(prefix='neo-equality-') as tmp:
        binary=Path(tmp)/'equal';build('tests/fixtures/byte_equal.neo',binary)
        for workers in [1,4]:
            for start in range(0,len(cases),80):
                batch=cases[start:start+80];data=b''.join(json.dumps([a.hex(),b.hex()]).encode().hex().encode()+b'\n' for a,b in batch)
                run=subprocess.run(RUNNER+[str(binary)],input=data,capture_output=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90)
                assert run.returncode==0,run.stderr
                assert [json.loads(x) for x in run.stdout.splitlines()]==[a==b for a,b in batch]
    print(f'PASS {len(cases)} complete byte equality cases, word/tail boundaries, every differing position, temporary/slice aliases and consuming array/record-field updates, 1/4 workers',flush=True)
if __name__=='__main__':main()
