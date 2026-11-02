#!/usr/bin/env python3
"""Short-word decimal parsing versus an independent checked integer model."""
import random,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def expected(text):
    negative=text[:1]==b'-';start=int(text[:1] in (b'-',b'+'));acc=0
    for i,byte in enumerate(text[start:],start):
        digit=byte-48
        if not 0<=digit<=9 or acc<-(2**63//10) or (acc==-(2**63//10) and digit>(8 if negative else 7)):
            return f'error {i+1}'
        acc=acc*10-digit
    if len(text)<=start:return f'error {start}'
    return f'ok {acc if negative else -acc}'

def main():
    rng=random.Random(251025)
    vectors=[b'',b'+',b'-',b'0',b'00000000',b'99999999',b'00000000000000000000000000000000000001']
    for number in [-(2**63)-1,-(2**63),-(2**63)+1,2**63-2,2**63-1,2**63]:
        vectors.append(str(number).encode())
    for size in range(1,10):
        for i in range(size):
            for byte in range(256):
                text=bytearray(b'5'*size);text[i]=byte;vectors.append(bytes(text))
        for _ in range(50):
            vectors.extend((rng.randbytes(size),bytes(rng.randrange(48,58) for _ in range(size))))
    with tempfile.TemporaryDirectory(prefix='neo-int-parse-') as tmp:
        binary=Path(tmp)/'parse';build('tests/fixtures/int_parse_vectors.neo',binary)
        for text in vectors:
            result=subprocess.run(RUNNER+[str(binary)],input=text,capture_output=True,timeout=10)
            assert result.returncode==0 and result.stdout.decode()==expected(text),(text,result.stdout,result.stderr,expected(text))
        binary=Path(tmp)/'format';build('tests/fixtures/int_text_vectors.neo',binary)
        numbers=[-2**63,2**63-1,0,99999999,100000000]+list(range(1000))
        for power in range(19):
            for delta in [-1,0,1]:numbers.extend((10**power+delta,-10**power-delta))
        numbers.extend(rng.randrange(-2**63,2**63) for _ in range(200))
        numbers.extend(rng.randrange(100000000) for _ in range(200))
        for number in numbers:
            result=subprocess.run(RUNNER+[str(binary),str(number)],capture_output=True,text=True,timeout=10)
            assert result.returncode==0 and result.stdout==str(number),(number,result.stdout,result.stderr)
    print(f'PASS short decimal parser: {len(vectors)} binary/sign/overflow/error-position vectors',flush=True)
    print(f'PASS owned integer formatting: {len(numbers)} signed/short/boundary/random vectors',flush=True)
if __name__=='__main__':main()
