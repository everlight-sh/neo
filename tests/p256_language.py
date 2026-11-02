#!/usr/bin/env python3
"""Native Montgomery arithmetic checked against independent Python integers."""
import random,subprocess,tempfile
from pathlib import Path
from agent_codecs import ROOT,RUNNER,build

def main():
    rng=random.Random(256)
    with tempfile.TemporaryDirectory(prefix='neo-p256-') as tmp:
        root=Path(tmp);source=root/'math.neo';binary=root/'math'
        source.write_text((ROOT/'stdlib/p256.neo').read_text()+'''\nimport "std:io"
effect(fs,process) fn main() -> unit
  = let input=file_read(0,1024) in check input.ok && len(input.value)==66 in
    let order=str_byte(input.value,0)!=0 in let mode=str_byte(input.value,1) in let mod=p256_mod(order) in
    let a=p256_montgomery(p256_words(str_slice(input.value,2,34)),mod) in let b=p256_montgomery(p256_words(str_slice(input.value,34,66)),mod) in
    let result=if mode==0 then p256_multiply(a,b,mod) else if mode==1 then p256_add(a,b,mod.modulus) else if mode==2 then p256_sub(a,b,mod.modulus) else p256_inverse(a,mod) in
    let output=file_write(1,p256_bytes(p256_normal(result,mod))) in check output.ok in noop()
''')
        build(str(source),binary)
        for order,mod in [(0,0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff),(1,0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551)]:
            pairs=[(0,0),(1,1),(mod-1,mod-1),(mod-2,2)]+[(rng.randrange(mod),rng.randrange(mod)) for _ in range(50)]
            for index,(a,b) in enumerate(pairs):
                for mode,expected in [(0,a*b%mod),(1,(a+b)%mod),(2,(a-b)%mod)]+([(3,pow(a,-1,mod))] if a and index<12 else []):
                    raw=bytes([order,mode])+a.to_bytes(32,'big')+b.to_bytes(32,'big')
                    p=subprocess.run(RUNNER+[str(binary)],input=raw,capture_output=True,timeout=30)
                    assert p.returncode==0,(order,mode,p.returncode,p.stderr)
                    assert p.stdout==expected.to_bytes(32,'big'),(order,mode,a,b,p.stdout.hex(),hex(expected))
        print('PASS P-256 field/order Montgomery add/sub/multiply/inverse vs Python integer oracle',flush=True)
if __name__=='__main__':main()
