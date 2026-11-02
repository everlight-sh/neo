#!/usr/bin/env python3
"""Allocation complexity checks; no wall-time threshold or machine-speed guess."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))


def main():
    with tempfile.TemporaryDirectory(prefix='neo-language-allocations-') as tmp:
        binary=Path(tmp)/'collections'
        built=subprocess.run(['python3','-m','neoc','build','tests/fixtures/language_bench.neo','-o',str(binary),'--report'],cwd=ROOT,
            env={**os.environ,'NEO_ALLOC_STATS':'1'},capture_output=True,text=True)
        assert built.returncode==0,(json.loads(built.stdout).get('errors'),built.stderr)
        rows={}
        for mode in (0,1,2):
            for n in (1000,10000,100000):
                run=subprocess.run(RUNNER+[str(binary),str(mode),str(n)],capture_output=True,text=True,timeout=30)
                assert run.returncode==0,(mode,n,run.stderr)
                checksum,ns,requests,traffic=map(int,run.stdout.split());rows[mode,n]=(requests,traffic)
                if mode==0:assert requests<=64 and traffic<=32*n+1024,(mode,n,requests,traffic)
                if mode==1:assert requests==1 and traffic==8*n,(mode,n,requests,traffic)
                if mode==2:assert requests<=20*n+128 and traffic<=800*n+1048576,(mode,n,requests,traffic)
            for a,b in ((1000,10000),(10000,100000)):
                assert rows[mode,b][1]<=20*rows[mode,a][1],(mode,rows)
        print('PASS allocation complexity at 1k/10k/100k: geometric append, one sort buffer, linear hash-map traffic',flush=True)


if __name__=='__main__':main()
