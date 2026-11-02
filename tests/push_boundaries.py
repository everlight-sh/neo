#!/usr/bin/env python3
"""Native push against value and exact allocation models at growth boundaries."""
import os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def allocation_model(n,size):
    requests=traffic=0
    for old in range(n):
        capacity=max(16,1<<((max(1,old*size)-1).bit_length()))
        needed=(old+1)*size
        if old==0 or needed>capacity:requests+=1;traffic+=needed
    # Nested immutable string literals are immortal references: neither insertion
    # nor verification needs a separate child-buffer allocation.
    return requests,traffic

def main():
    with tempfile.TemporaryDirectory(prefix='neo-push-boundaries-') as tmp:
        binary=Path(tmp)/'push';previous=os.environ.get('NEO_ALLOC_STATS');os.environ['NEO_ALLOC_STATS']='1'
        try:build('tests/fixtures/push_boundaries.neo',binary)
        finally:
            if previous is None:os.environ.pop('NEO_ALLOC_STATS')
            else:os.environ['NEO_ALLOC_STATS']=previous
        for mode,size in enumerate([8,4,1,1,24,16]):
            lengths=set(range(34))
            for power in range(6,20):lengths.update([2**power-1,2**power,2**power+1])
            lengths.add(1000000)
            for n in sorted(lengths):
                if mode==4 and n>4097:continue
                if mode==5 and n>129:continue
                result=subprocess.run(RUNNER+[str(binary),str(mode),str(n)],capture_output=True,text=True,timeout=30)
                assert result.returncode==0,(mode,n,result.stderr)
                checksum,requests,traffic=map(int,result.stdout.split())
                expected=sum(i%251 for i in range(n)) if mode<3 else (n+1)//2 if mode==3 else 7*n if mode==4 else 8*sum(i%251 for i in range(n))
                allocations=allocation_model(n,size) if mode!=5 else (n,16*n*(n+1)//2)
                assert (checksum,requests,traffic)==(expected,*allocations),(mode,n,result.stdout,expected,allocations)
        print('PASS native push: i64/i32/u8/bool, nested arrays and SoA records; retained aliases and exact growth allocations/bytes through 1M elements',flush=True)
if __name__=='__main__':main()
