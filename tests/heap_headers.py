#!/usr/bin/env python3
"""Heap class boundaries, nonoverlap, alignment and pool isolation."""
import os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build
from kernel_runtime_smoke import audit

def main():
    with tempfile.TemporaryDirectory(prefix='neo-heap-headers-') as temp:
        binary=Path(temp)/'probe';build('tests/fixtures/heap_headers.neo',binary);audit(binary)
        for workers in ['1','4']:
            result=subprocess.run(RUNNER+[str(binary)],env={**os.environ,'NEO_THREADS':workers},capture_output=True,text=True,timeout=60)
            assert result.returncode==0 and result.stdout=='0\n',(workers,result.returncode,result.stdout,result.stderr)
    print('PASS heap: 3072 live blocks do not overlap; aligned allocations, full rounded payloads, private/shared pools and reuse across 16 B–32 MiB class boundaries',flush=True)

if __name__=='__main__':main()
