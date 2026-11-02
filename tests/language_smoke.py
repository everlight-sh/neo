#!/usr/bin/env python3
"""Native language checks against external hash vectors and a Python map model."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))


def model(n):
    values={};checksum=0
    for i in range(n):
        checksum+=values.get((i*31)%257,-1)
        if i%5==0:values.pop((i*73)%257,None)
        else:values[(i*73)%257]=i*11
    return f'{len(values)} {checksum}\n'


def main():
    with tempfile.TemporaryDirectory(prefix='neo-language-') as tmp:
        binaries={}
        for name in ('collections','resources','hash','types'):
            binary=Path(tmp)/name
            built=subprocess.run(['python3','-m','neoc','build','tests/fixtures/language_'+name+'.neo','-o',str(binary),'--report'],cwd=ROOT,capture_output=True,text=True)
            assert built.returncode==0,(name,built.stdout,built.stderr)
            report=json.loads(built.stdout);assert report['undefined_symbols']==[],report
            binaries[name]=binary
        def run(name,n,timeout=45):
            result=subprocess.run(RUNNER+[str(binaries[name]),str(n)],capture_output=True,text=True,timeout=timeout)
            assert result.returncode==0,(name,n,result.returncode,result.stderr)
            return result.stdout
        for n in (0,1,2,3,17,256,257,511,1000,10000,100000):assert run('collections',n)==model(n),n
        print('PASS native collections: independent map model, tombstones, binary/empty keys, owned values, aliases and sorting',flush=True)
        vectors=json.loads((ROOT/'tests/fixtures/siphash_vectors.json').read_text())
        for n,value in enumerate(vectors['vectors']):assert int(run('hash',n))%(1<<64)==int(value,16),n
        print('PASS all 64 independent SipHash-2-4 vectors in native machine code',flush=True)
        for n in (0,1,7,1000,10000):assert run('resources',n)=='resources OK\n',n
        print('PASS scoped cleanup, error propagation, moves, cancellation, deadlines, exact channel bounds and 10,000 cross-process messages',flush=True)
        assert run('types',7)=='owned:value=7\n';assert run('types',-1)=='error:negative\n'
        print('PASS generic owned data, checked matches and typed error short circuit',flush=True)


if __name__=='__main__':main()
