#!/usr/bin/env python3
import os,random,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build
def main():
    rng=random.Random(602627)
    with tempfile.TemporaryDirectory(prefix='neo-bit-counts-') as tmp:
        binary=Path(tmp)/'counts';build('tests/fixtures/bit_counts.neo',binary)
        for value in [0,-1,-2**63,2**63-1]+[1<<i for i in range(63)]+[-(1<<i) for i in range(64)]+[rng.randrange(-2**63,2**63) for _ in range(80)]:
            raw=value%(1<<64);want=64 if raw==0 else len(bin(raw))-len(bin(raw).rstrip('0'))
            for workers in [1,4]:
                run=subprocess.run(RUNNER+[str(binary),str(value)],capture_output=True,text=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=20)
                assert run.returncode==0 and run.stdout.strip()==str(want),(value,run.stdout,run.stderr)
    print('PASS native trailing-zero counts: zero, sign bits, every power of two and random words, 1/4 workers',flush=True)
if __name__=='__main__':main()
