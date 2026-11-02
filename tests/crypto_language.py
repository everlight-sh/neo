#!/usr/bin/env python3
"""Native primitives checked against OpenSSL, RFC vectors and Python hashlib.

OpenSSL is a test oracle, never linked into or called by a Neo executable.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import random
import shlex
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))


def openssl(*args,data=None):
    result=subprocess.run(['openssl',*args],input=data,capture_output=True,timeout=60)
    assert result.returncode==0,result.stderr
    return result.stdout


def main():
    with tempfile.TemporaryDirectory(prefix='neo-crypto-language-') as tmp:
        root=Path(tmp);binary=root/'crypto'
        built=subprocess.run(['python3','-m','neoc','build','tests/fixtures/language_crypto.neo','-o',str(binary),'--report'],cwd=ROOT,capture_output=True,text=True)
        assert built.returncode==0,(json.loads(built.stdout).get('errors'),built.stderr)
        assert json.loads(built.stdout)['undefined_symbols']==[]
        def run(mode,data,valid=True):
            r=subprocess.run(RUNNER+[str(binary),str(mode)],input=data,capture_output=True,timeout=30)
            assert r.returncode==(0 if valid else 2),(mode,r.returncode,r.stderr)
            if not valid:assert not r.stdout
            return r.stdout
        rng=random.Random(10358439)
        for size in [0,1,55,56,63,64,65,127,128,1000]:
            raw=bytes(i%256 for i in range(size));key=bytes(range(32))
            assert run(10,raw)==hashlib.sha1(raw).digest()
            assert run(11,key+raw)==hmac.digest(key,raw,'sha1')
        print('PASS legacy SHA-1/HMAC-SHA1 native boundary vectors for WebSocket/STUN interoperability',flush=True)
        for n in (0,1,3,15,16,17,31,32,55,56,63,64,65,127,128,129,1024,16384,1048576):
            message=rng.randbytes(n);assert run(0,message)==hashlib.sha256(message).digest(),n
            if n<1048576:
                key=rng.randbytes(32);assert run(1,key+message)==hmac.digest(key,message,'sha256'),n
        for n in (0,1,15,16,17,31,32,33,63,64,65,127,128,1024,4096,16384):
            key=rng.randbytes(32);nonce=rng.randbytes(12);aad=rng.randbytes(12);message=rng.randbytes(n)
            block=run(2,key+nonce+(1).to_bytes(4,'little'))
            expected=openssl('enc','-chacha20','-K',key.hex(),'-iv',((1).to_bytes(4,'little')+nonce).hex(),'-nosalt',data=bytes(64))
            assert block==expected,(n,'ChaCha block')
            tag=run(5,key+message);expected=bytes.fromhex(openssl('mac','-macopt','hexkey:'+key.hex(),'POLY1305',data=message).decode().strip())
            assert tag==expected,(n,'Poly1305')
            sealed=run(3,key+nonce+aad+message)
            expected_cipher=openssl('enc','-chacha20','-K',key.hex(),'-iv',((1).to_bytes(4,'little')+nonce).hex(),'-nosalt',data=message)
            assert sealed[:-16]==expected_cipher
            polykey=openssl('enc','-chacha20','-K',key.hex(),'-iv',(bytes(4)+nonce).hex(),'-nosalt',data=bytes(32))
            mac=aad+bytes((-len(aad))%16)+sealed[:-16]+bytes((-n)%16)+len(aad).to_bytes(8,'little')+n.to_bytes(8,'little')
            expected_tag=bytes.fromhex(openssl('mac','-macopt','hexkey:'+polykey.hex(),'POLY1305',data=mac).decode().strip())
            assert sealed[-16:]==expected_tag
            assert run(4,key+nonce+aad+sealed)==message
            damaged=sealed[:-1]+bytes([sealed[-1]^1]);run(4,key+nonce+aad+damaged,False)
        ikm=b'\x0b'*22;salt=bytes.fromhex('000102030405060708090a0b0c');info=bytes.fromhex('f0f1f2f3f4f5f6f7f8f9')
        prk=hmac.digest(salt,ikm,'sha256');assert run(7,prk+info)==bytes.fromhex('3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865')
        print('PASS native SHA-256/HMAC boundaries through 1 MiB, HKDF vector, and 16 ChaCha/Poly1305/AEAD cases against OpenSSL including tamper rejection',flush=True)
        for _ in range(16):
            secret=rng.randbytes(32);peer_secret=rng.randbytes(32)
            private=root/'private.der';peer_private=root/'peer.der';peer_public=root/'peer-public.der'
            private.write_bytes(bytes.fromhex('302e020100300506032b656e04220420')+secret)
            peer_private.write_bytes(bytes.fromhex('302e020100300506032b656e04220420')+peer_secret)
            public=openssl('pkey','-inform','DER','-in',str(peer_private),'-pubout','-outform','DER');peer_public.write_bytes(public)
            expected=openssl('pkeyutl','-derive','-inkey',str(private),'-keyform','DER','-peerkey',str(peer_public),'-peerform','DER')
            assert run(6,secret+public[-32:])==expected
        run(6,rng.randbytes(32)+bytes(32),False)
        print('PASS 16 X25519 exchanges against independent OpenSSL keys and low-order point rejection',flush=True)
        for bits in (2048,2049,2050,4096):
            key=root/'rsa.pem';message=root/'message';signature=root/'signature';message.write_bytes(rng.randbytes(93))
            openssl('genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:'+str(bits),'-out',str(key))
            hexmod=openssl('rsa','-in',str(key),'-noout','-modulus').decode().strip().split('=')[1]
            modulus=bytes.fromhex(('0' if len(hexmod)%2 else '')+hexmod)
            for mode in (8,9):
                options=['dgst','-sha256','-sign',str(key),'-out',str(signature)]
                if mode==9:options+=['-sigopt','rsa_padding_mode:pss','-sigopt','rsa_pss_saltlen:32']
                openssl(*options,str(message))
                signed=signature.read_bytes();payload=len(modulus).to_bytes(2,'big')+modulus+signed+message.read_bytes()
                assert run(mode,payload)==b'verified'
                run(mode,payload[:-1]+bytes([payload[-1]^1]),False)
                run(mode,len(modulus).to_bytes(2,'big')+modulus+modulus+message.read_bytes(),False)
            actual_bits=int.from_bytes(modulus,'big').bit_length()
            print(f'PASS RSA {actual_bits}-bit PKCS#1 SHA-256 and PSS SHA-256 signatures, tampering and noncanonical rejection',flush=True)


if __name__=='__main__':main()
