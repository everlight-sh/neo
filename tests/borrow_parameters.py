#!/usr/bin/env python3
"""Explicit effect borrows: no copies, escaped ownership and overlapping aliases."""
import json,os,shlex,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    with tempfile.TemporaryDirectory(prefix='neo-borrow-parameters-') as folder:
        binary=Path(folder)/'probe'
        result=subprocess.run(['python3','-m','neoc','build','tests/fixtures/borrow_parameters.neo','-o',str(binary),'--report'],cwd=ROOT,env={**os.environ,'NEO_ALLOC_STATS':'1'},capture_output=True,text=True)
        report=json.loads(result.stdout)
        assert result.returncode==0,({key:value for key,value in report.items() if key in ('error','errors','summary')},result.stderr)
        assert report['undefined_symbols']==[]
        for count in [1,1000,10000]:
            run=subprocess.run(shlex.split(os.environ.get('NEO_RUNNER',''))+[str(binary),str(count)],capture_output=True,text=True,timeout=30)
            assert run.returncode==0 and run.stdout=='borrow parameters OK\n',(count,run.returncode,run.stdout,run.stderr)
    print('PASS effect borrows: zero-allocation record inspection, overlapping moves/updates, generic escapes and temporary cleanup',flush=True)
if __name__=='__main__':main()
