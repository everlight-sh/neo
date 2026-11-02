#!/usr/bin/env python3
"""Owned little-endian byte comprehension, short-store and ordinary paths."""
import random,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build
def main():
    rng=random.Random(20261025)
    with tempfile.TemporaryDirectory(prefix='neo-word-bytes-') as tmp:
        binary=Path(tmp)/'words';build('tests/fixtures/word_bytes.neo',binary)
        for word in [0,-1,1,-2**63,2**63-1,0x0102030405060708]+[rng.randrange(-2**63,2**63) for _ in range(20)]:
            for n in [*range(18),31,32,33,511,1024]:
                data=bytes((word>>((i*8)%64))&255 for i in range(n))
                run=subprocess.run(RUNNER+[str(binary),str(word),str(n)],capture_output=True,text=True,timeout=10)
                assert run.returncode==0 and tuple(map(int,run.stdout.split()))==(n,sum(data),sum(data[1:])),(word,n,run.stdout,run.stderr)
    print('PASS owned word-byte arrays: zero/short/large lengths, signed words, repeated shifts and alias isolation',flush=True)
if __name__=='__main__':main()
