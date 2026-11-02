#!/usr/bin/env python3
"""Fresh observer arguments and escaped references under allocator reuse."""
import os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def main():
    with tempfile.TemporaryDirectory(prefix='neo-observer-lifetimes-') as temp:
        binary=Path(temp)/'probe';build('tests/fixtures/observer_lifetimes.neo',binary)
        for workers in ['1','4']:
            result=subprocess.run(RUNNER+[str(binary)],env={**os.environ,'NEO_THREADS':workers},capture_output=True,text=True,timeout=60)
            assert result.returncode==0 and result.stdout=='observer lifetimes OK\n',(workers,result.returncode,result.stdout,result.stderr)
    print('PASS observer lifetime proofs: 10k cases per worker mode, live aliases, copied outputs, escaping boxes/nested set children/loop states/indirect callbacks and heavy allocator reuse',flush=True)

if __name__=='__main__':main()
