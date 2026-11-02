#!/usr/bin/env python3
"""Native arena-map model, compaction/alias and disjoint-field lifetime checks."""
import json,os,shlex,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))

def key(i):return b'' if i%257==0 else b'\0key'+str(i%257).encode()
def model(n):
    values={};checksum=0
    for i in range(n):
        v=values.get(key(i*31));checksum+=-1 if v is None else len(v)*31+sum(v)
        if i%5==0:values.pop(key(i*73),None)
        else:values[key(i*73)]=str(i).encode()+bytes(j%251 for j in range(i%80))
    return len(values),checksum

def main():
    with tempfile.TemporaryDirectory(prefix='neo-byte-map-') as tmp:
        for fixture in ('bytesmap','field_moves'):
            binary=Path(tmp)/fixture
            result=subprocess.run(['python3','-m','neoc','build',f'tests/fixtures/{fixture}.neo','-o',str(binary),'--report'],cwd=ROOT,env={**os.environ,'NEO_ALLOC_STATS':'1'},capture_output=True,text=True)
            assert result.returncode==0,(fixture,result.stdout[-4000:],result.stderr)
            report=json.loads(result.stdout);assert report['undefined_symbols']==[]
            for n in (0,1,7,257,1000,10000,100000):
                result=subprocess.run(RUNNER+[str(binary),str(n)],capture_output=True,text=True,timeout=60);assert result.returncode==0,(fixture,n,result.stderr)
                a,b,c=map(int,result.stdout.split())
                if fixture=='bytesmap':assert (a,b)==model(n) and c<150000,(n,a,b,c,model(n))
                else:assert a==4*n*(n-1) and b<=100 and c<=64*n+8192,(n,a,b,c)
            print('PASS '+fixture+': independent model, aliases, empty/binary keys, repeated growth/overwrite/delete/compaction' if fixture=='bytesmap' else 'PASS field moves: aliases/conditional/whole-record reuse and geometric traffic for two growing buffers',flush=True)
if __name__=='__main__':main()
