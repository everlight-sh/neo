#!/usr/bin/env python3
"""Write-only loop states (set/byte_write_le/byte_copy, conditional or chained): one
uniqueness test at loop entry, never a write through a shared buffer, and a yield
that shares the final state still copies before writing."""
import os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def main():
    with tempfile.TemporaryDirectory(prefix='neo-write-only-loops-') as temp:
        binary=Path(temp)/'probe';build('tests/fixtures/write_only_loops.neo',binary)
        for workers in ['1','4']:
            result=subprocess.run(RUNNER+[str(binary)],env={**os.environ,'NEO_THREADS':workers},capture_output=True,text=True,timeout=60)
            assert result.returncode==0 and result.stdout=='write-only loops OK\n',(workers,result.returncode,result.stdout,result.stderr)
    print('PASS write-only loop states: shared, borrowed, moved, literal, overlapping, conditional, chained and yield-aliased sources stay intact',flush=True)

if __name__=='__main__':main()
