#!/usr/bin/env python3
"""Native AES/GCM vectors and differential oracle; Go is test-only."""
import json,os,random,subprocess,tempfile,time
from pathlib import Path
from agent_codecs import ROOT,RUNNER,build

def main():
    rng=random.Random(3826)
    with tempfile.TemporaryDirectory(prefix='neo-aes-') as tmp:
        root=Path(tmp);binary=root/'aes';build('tests/fixtures/language_aes.neo',binary)
        oracle=root/'oracle';subprocess.run(['go','build','-trimpath','-o',str(oracle),'tests/aes_oracle.go'],cwd=ROOT,env={**os.environ,'GOWORK':'off','CGO_ENABLED':'0'},capture_output=True,check=True)
        def run(mode,raw,valid=True):
            p=subprocess.run(RUNNER+[str(binary),str(mode)],input=raw,capture_output=True,timeout=30)
            assert p.returncode==(0 if valid else 2),(mode,p.returncode,p.stderr)
            if not valid:assert p.stdout==b''
            return p.stdout
        key=bytes(range(16));plain=bytes.fromhex('00112233445566778899aabbccddeeff')
        assert run(0,key+plain)==bytes.fromhex('69c4e0d86a7b0430d8cdb78070b4c55a')
        assert run(1,bytes(28)+bytes(4))==bytes.fromhex('58e2fccefa7e3061367f1d57a4e7455a')
        assert run(1,bytes(28)+bytes(4)+bytes(16))==bytes.fromhex('0388dace60b6a392f328c2b971b2fe78ab6e47d42cec13bdf53a67b21257bddf')
        cases=[]
        hardware=run(6,b'')==b'1'
        for size in [0,1,15,16,17,31,32,55,63,64,65,127,128,129,143,144,255,1000,4096,16385]:
            for _ in range(2):
                key=rng.randbytes(16);nonce=rng.randbytes(12);aad=rng.randbytes(rng.randrange(0,70));data=rng.randbytes(size)
                cases.append(dict(Mode=1,Key=key.hex(),Nonce=nonce.hex(),AAD=aad.hex(),Data=data.hex()))
        p=subprocess.run([str(oracle)],input=''.join(json.dumps(c)+'\n' for c in cases),capture_output=True,text=True,check=True)
        for case,expected in zip(cases,p.stdout.splitlines()):
            key=bytes.fromhex(case['Key']);nonce=bytes.fromhex(case['Nonce']);aad=bytes.fromhex(case['AAD']);plain=bytes.fromhex(case['Data']);wire=bytes.fromhex(json.loads(expected));prefix=key+nonce+len(aad).to_bytes(4,'big')+aad
            # Modes 1/2 are the portable code, 4/5 the AES-NI/PCLMULQDQ path (portable without them).
            for seal,open_ in ((1,2),(4,5)):
                assert run(seal,prefix+plain)==wire,(seal,len(plain),len(aad))
                assert run(open_,prefix+wire)==plain,(open_,len(plain),len(aad))
                for index in [0,len(wire)-17,len(wire)-1]:
                    if index<0:continue
                    damaged=bytearray(wire);damaged[index]^=1;run(open_,prefix+damaged,False)
                bad_prefix=key+nonce[:-1]+bytes([nonce[-1]^1])+len(aad).to_bytes(4,'big')+aad;run(open_,bad_prefix+wire,False)
        print(f'PASS AES-128 NIST block/GCM vectors; {len(cases)} Go-oracle GCM cases through the portable and fast paths (aes_hardware {hardware}), boundary sizes, round trips and no plaintext after tag/nonce corruption',flush=True)
if __name__=='__main__':main()
