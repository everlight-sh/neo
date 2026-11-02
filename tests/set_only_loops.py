#!/usr/bin/env python3
"""Set-only loop states: one uniqueness test at entry, never a write through a shared buffer."""
import os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def main():
    with tempfile.TemporaryDirectory(prefix='neo-set-only-loops-') as temp:
        binary=Path(temp)/'probe';build('tests/fixtures/set_only_loops.neo',binary)
        for workers in ['1','4']:
            result=subprocess.run(RUNNER+[str(binary)],env={**os.environ,'NEO_THREADS':workers},capture_output=True,text=True,timeout=60)
            assert result.returncode==0 and result.stdout=='set-only loops OK\n',(workers,result.returncode,result.stdout,result.stderr)
    print('PASS set-only loop states: shared, borrowed, moved, aliased-state, zero-iteration and literal sources stay intact',flush=True)

if __name__=='__main__':main()
