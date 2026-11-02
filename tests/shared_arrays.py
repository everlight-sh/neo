#!/usr/bin/env python3
"""Native immutable sharing, copy-on-write and nested ownership."""
import json,os,shlex,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    with tempfile.TemporaryDirectory(prefix='neo-shared-arrays-') as folder:
        binary=Path(folder)/'probe'
        built=subprocess.run(['python3','-m','neoc','build','tests/fixtures/shared_arrays.neo','--report','-o',str(binary)],cwd=ROOT,env={**os.environ,'NEO_ALLOC_STATS':'1'},capture_output=True,text=True)
        assert built.returncode==0,(built.stdout[-5000:],built.stderr)
        assert json.loads(built.stdout)['undefined_symbols']==[]
        for workers in ['1','4']:
            for count in [1,1000,10000]:
                result=subprocess.run(shlex.split(os.environ.get('NEO_RUNNER',''))+[str(binary),str(count)],env={**os.environ,'NEO_THREADS':workers},capture_output=True,text=True,timeout=60)
                assert result.returncode==0 and result.stdout=='shared arrays OK\n',(workers,count,result.returncode,result.stdout,result.stderr)
    print('PASS shared arrays: 100 snapshots use one descriptor allocation; nested writes isolate aliases; retained snapshots survive owner destruction; offset slices, append and repeated detach/release',flush=True)
if __name__=='__main__':main()
