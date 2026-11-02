#!/usr/bin/env python3
"""Array-borrow allocation bounds plus binary/long-key map model checks."""
import os,subprocess,tempfile
from pathlib import Path
from agent_codecs import ROOT,RUNNER,build

def key(n):return bytes((i*37+n)%256 for i in range(n))
def value(n):return bytes((i*13+n)%256 for i in range(n%37))
def main():
    with tempfile.TemporaryDirectory(prefix='neo-map-optimizations-') as tmp:
        binary=Path(tmp)/'borrow';before=os.environ.get('NEO_ALLOC_STATS');os.environ['NEO_ALLOC_STATS']='1'
        build('tests/fixtures/map_array_borrows.neo',binary)
        if before is None:os.environ.pop('NEO_ALLOC_STATS')
        else:os.environ['NEO_ALLOC_STATS']=before
        for n in [1,2,17,1000,10000,100000]:
            run=subprocess.run(RUNNER+[str(binary),str(n)],capture_output=True,text=True,timeout=20);assert run.returncode==0,run.stderr
            checksum,requests,traffic=map(int,run.stdout.split());assert checksum==4*n-2 and requests<=32 and traffic<=64*n+4096,(n,run.stdout)
        print('PASS array scalar-result borrows: retained aliases, mutation isolation and linear allocation traffic through 100k elements',flush=True)
        binary=Path(tmp)/'vectors';build('tests/fixtures/map_vectors.neo',binary)
        for n in [0,1,7,8,9,15,16,17,31,32,33,64,127,257,1024]:
            run=subprocess.run(RUNNER+[str(binary),str(n)],capture_output=True,text=True,timeout=20);assert run.returncode==0,(n,run.stderr)
            original=sum(len(value(i))*31+sum(value(i)) for i in range(n));remaining=sum(len(value(i))*31+sum(value(i)) for i in range(n) if i%2)
            assert tuple(map(int,run.stdout.split()))==(original,remaining),(n,run.stdout,original,remaining)
        print('PASS native map against Python bytes model: empty/NUL/long keys, every word-tail alignment, missing keys, aliases, deletion and compaction',flush=True)
        binary=Path(tmp)/'inline';build('tests/fixtures/map_inline_keys.neo',binary)
        run=subprocess.run(RUNNER+[str(binary),'8192'],capture_output=True,text=True,timeout=60)
        assert run.returncode==0 and run.stdout=='inline maps OK\n',(run.stdout,run.stderr)
        print('PASS inline map words: binary keys/values, hash compatibility, all encoding boundaries, retained aliases and compacted collision chains',flush=True)
if __name__=='__main__':main()
