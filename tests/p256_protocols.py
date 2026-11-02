#!/usr/bin/env python3
"""Native P-256 ECDH/ECDSA vs RFC6979 and independent standard Go crypto."""
import json,os,random,subprocess,tempfile
from pathlib import Path
from agent_codecs import ROOT,RUNNER,build
ORDER=0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551

def der(r,s):
    def integer(x):
        b=x.to_bytes((x.bit_length()+7)//8 or 1,'big')
        if b[0]&128:b=b'\0'+b
        return b'\x02'+bytes([len(b)])+b
    b=integer(r)+integer(s)
    return b'\x30'+bytes([len(b)])+b

def main():
    rng=random.Random(6979)
    with tempfile.TemporaryDirectory(prefix='neo-p256-protocols-') as tmp:
        root=Path(tmp);binary=root/'p256';build('tests/fixtures/language_p256.neo',binary)
        oracle=root/'oracle';subprocess.run(['go','build','-trimpath','-o',str(oracle),'tests/p256_oracle.go'],cwd=ROOT,env={**os.environ,'GOWORK':'off','CGO_ENABLED':'0'},capture_output=True,check=True)
        def run(mode,raw,valid=True):
            p=subprocess.run(RUNNER+[str(binary),str(mode)],input=raw,capture_output=True,timeout=60)
            assert p.returncode==(0 if valid else 2),(mode,p.returncode,p.stderr)
            if not valid:assert not p.stdout
            return p.stdout
        def go(mode,**fields):
            p=subprocess.run([str(oracle)],input=json.dumps(dict(Mode=mode,**{k:v.hex() for k,v in fields.items()}))+'\n',capture_output=True,text=True,check=True)
            return bytes.fromhex(json.loads(p.stdout))
        def verify(public,message,sig):return run(3,public+bytes([len(sig)])+sig+message)==b'yes'
        # RFC6979 Appendix A.2.5, SHA-256 sample and test. Exact DER including
        # leading positive-integer zero and a 31-byte scalar encoding.
        secret=bytes.fromhex('c9afa9d845ba75166b5c215767b1d6934e50c3db36e89b127b8a622b120f6721')
        public=bytes.fromhex('0460fed4ba255a9d31c961eb74c6356d68c049b8923b61fa6ce669622e60f29fb67903fe1008b8bc99a41ae9e95628bc64f2f1b20c2d7e9f5177a3c294d4462299')
        assert run(0,secret)==public
        for message,r,s in [
          (b'sample','efd48b2aacb6a8fd1140dd9cd45e81d69d2c877b56aaf991c34d0ea84eaf3716','f7cb1c942d657c41d436c7a1b6e29f65f3e900dbb9aff4064dc4ab2f843acda8'),
          (b'test','f1abb023518351cd71d881567b1ea663ed3efcf6c5132b354f28d3b0b7d38367','019f4113742a2b14bd25926b49c649155f267e60d3814b4c0cc84250e46f0083')]:
            sig=der(int(r,16),int(s,16));assert run(2,secret+message)==sig;assert verify(public,message,sig)
            assert go(3,Public=public,Data=message,Signature=sig)==b'yes'
        keys=[1,2,ORDER-1]+[rng.randrange(1,ORDER) for _ in range(5)]
        for i,d in enumerate(keys):
            secret=d.to_bytes(32,'big');public=run(0,secret);assert public==go(0,Key=secret)
            assert run(4,public)==b'yes'
            peer=keys[-1-i].to_bytes(32,'big');peer_public=go(0,Key=peer)
            shared=run(1,secret+peer_public);assert shared==go(1,Key=secret,Public=peer_public)
            assert shared==run(1,peer+public)
            message=rng.randbytes([0,1,31,32,63,64,128,1024][i]);sig=run(2,secret+message)
            assert go(3,Public=public,Data=message,Signature=sig)==b'yes'
            other=go(2,Key=secret,Data=message);assert verify(public,message,other)
            assert not verify(public,message+b'x',sig)
            damaged=sig[:-1]+bytes([sig[-1]^1]);assert not verify(public,message,damaged)
        for invalid in [b'',bytes(31),bytes(32),ORDER.to_bytes(32,'big'),bytes([255])*32]:run(0,invalid,False)
        badkeys=[b'',public[1:],bytes(65),b'\x03'+public[1:],public[:-1]+bytes([public[-1]^1]),b'\x04'+bytes([255])*32+public[33:]]
        for invalid in badkeys:
            assert run(4,invalid)==b'no';run(1,(1).to_bytes(32,'big')+invalid,False)
        for invalid in [b'',b'\x30\0',der(0,1),der(1,0),der(ORDER,1),der(1,ORDER),sig+b'\0',b'\x30\x06\x02\x01\xff\x02\x01\x01',b'\x30\x07\x02\x02\x00\x01\x02\x01\x01']:
            assert not verify(public,message,invalid),invalid.hex()
        print('PASS P-256 ECDH/public keys against Go; ECDSA RFC6979 exact vectors and bidirectional Go interop; invalid keys/DER/range/tampering rejected',flush=True)
if __name__=='__main__':main()
