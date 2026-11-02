#!/usr/bin/env python3
"""Strict bounded UTF-8 validation against Python's independent decoder."""
import json,os,random,subprocess
from pathlib import Path
from agent_codecs import RUNNER,build
ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'.kernel-build/utf8-ranges';folder.mkdir(parents=True,exist_ok=True);binary=folder/'probe';build('tests/fixtures/utf8_ranges.neo',binary)
    rng=random.Random(261028);cases=[]
    samples=[b'',bytes(range(128)),b'a'*200,'café 🚀\x00é世界'.encode(),b'\xc0\x80',b'\xed\xa0\x80',b'\xf4\x90\x80\x80']+[bytes(rng.randrange(256) for _ in range(rng.randrange(70))) for _ in range(500)]
    for raw in samples:
        wrapped=b'padding123'+raw+b'\xa9\x80tail'
        for start,end in [(10,10+len(raw)),(0,len(wrapped)),(-1,4),(4,len(wrapped)+1),(5,4)]+[(rng.randrange(len(wrapped)+1),rng.randrange(len(wrapped)+1)) for _ in range(8)]:cases.append((wrapped,start,end))
    for scalar in [0x80,0x7ff,0x800,0xd7ff,0xe000,0xffff,0x10000,0x10ffff]:
        raw=chr(scalar).encode()
        for padding in range(17):
            wrapped=b'a'*padding+raw+b'tail'
            for start in range(padding,padding+len(raw)+1):
                for end in range(start,padding+len(raw)+1):cases.append((wrapped,start,end))
    for start in range(0,len(cases),80):
        batch=cases[start:start+80];payload=b''.join(json.dumps([raw.hex(),a,b]).encode().hex().encode()+b'\n' for raw,a,b in batch)
        result=subprocess.run(RUNNER+[str(binary)],input=payload,capture_output=True,env={**os.environ,'NEO_THREADS':'1'},timeout=60)
        assert result.returncode==0,result.stderr;actual=[json.loads(x) for x in result.stdout.splitlines()];assert len(actual)==len(batch)
        for (raw,a,b),got in zip(batch,actual):
            valid=0<=a<=b<=len(raw)
            if valid:
                try:raw[a:b].decode('utf-8')
                except UnicodeError:valid=False
            assert got==valid,(raw,a,b,got)
    print(f'PASS {len(cases)} bounded UTF-8 cases: independent decoder, invalid bounds, ASCII words, every scalar-boundary split and invalid encodings',flush=True)
if __name__=='__main__':main()
