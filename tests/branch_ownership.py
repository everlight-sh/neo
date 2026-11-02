#!/usr/bin/env python3
"""Branch-local record moves, nested scalar borrowing and safe field mutation."""
import json,os,shlex,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    with tempfile.TemporaryDirectory(prefix='neo-branch-ownership-') as folder:
        binary=Path(folder)/'probe'
        built=subprocess.run(['python3','-m','neoc','build','tests/fixtures/branch_ownership.neo','-o',str(binary),'--report'],cwd=ROOT,
                             env={**os.environ,'NEO_ALLOC_STATS':'1'},capture_output=True,text=True)
        assert built.returncode==0,(built.stdout[-3000:],built.stderr[-3000:])
        assert json.loads(built.stdout)['undefined_symbols']==[]
        runner=shlex.split(os.environ.get('NEO_RUNNER',''))
        measurements=[]
        for count in [1000,10000,100000]:
            run=subprocess.run(runner+[str(binary),str(count)],capture_output=True,text=True,timeout=30)
            assert run.returncode==0,(count,run.returncode,run.stdout,run.stderr)
            checksum,requests,traffic=map(int,run.stdout.split())
            assert checksum==1000*count
            assert requests<20*count+100 and traffic<2048*count+65536,(count,requests,traffic)
            measurements.append((count,requests,traffic))
        for previous,current in zip(measurements,measurements[1:]):
            assert current[2]<20*previous[2],measurements
        print('PASS branch-local ownership, alias isolation, field mutation, nested scalar reads and linear allocation traffic:',measurements,flush=True)
if __name__=='__main__':main()
