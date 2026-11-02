#!/usr/bin/env python3
"""Independent native codec oracles; Python is only the test driver."""
import base64, json, math, os, random, shlex, struct, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))
def build(source,target):
    p=subprocess.run(['python3','-m','neoc','build',source,'-o',str(target),'--report'],cwd=ROOT,capture_output=True,text=True)
    assert p.returncode==0,({k:v for k,v in json.loads(p.stdout).items() if k in ('error','errors','ok')},p.stderr) if p.stdout.startswith('{') else (p.stdout[-1500:],p.stderr)
    report=json.loads(p.stdout);assert report['undefined_symbols']==[],report['undefined_symbols']
    return report

def main():
    rng=random.Random(4591)
    with tempfile.TemporaryDirectory(prefix='neo-codecs-') as tmp:
        binary=Path(tmp)/'codecs';build('tests/fixtures/agent_codecs.neo',binary)
        def run(mode,data):
            r=subprocess.run(RUNNER+[str(binary),str(mode)],input=data,capture_output=True,timeout=30)
            assert r.returncode==0,(mode,data[:200],r.returncode,r.stderr)
            return r.stdout
        def bits(value):return struct.unpack('q',struct.pack('d',value))[0]
        decimals=['0','-0','0.1','1.00000000000000011102230246251565404236316680908203125','1.00000000000000011102230246251565404236316680908203126','2.2250738585072014e-308','4.9406564584124654e-324','2.4703282292062327e-324','1.7976931348623157e308','-1e-400']
        for _ in range(180):decimals.append(str(rng.randrange(-10**32,10**32))+'e'+str(rng.randrange(-350,300)))
        for text in decimals:
            expected=float(text)
            got=run(0,text.encode())
            assert got==(str(bits(expected)).encode() if math.isfinite(expected) else b'error'),(text,got,expected)
        for text in ['','NaN','Infinity','1e9999','1e','--1','1.2.3',' 1','1 ','.','+']:
            assert run(0,text.encode())==b'error',text
        patterns=[0,1,-1,-(1<<63),0x0010000000000000,0x7fefffffffffffff]+[rng.randrange(-(1<<63),1<<63) for _ in range(180)]
        for pattern in patterns:
            value=struct.unpack('d',struct.pack('q',pattern))[0];encoded=run(1,str(pattern).encode())
            if not math.isfinite(value):assert encoded==b'error';continue
            assert bits(float(encoded))==pattern,(pattern,value,encoded)
            assert run(0,encoded)==str(pattern).encode(),(pattern,encoded)
        print('PASS exact decimal conversion and binary64 round trips (independent Python oracle)',flush=True)
        for size in list(range(35))+[63,64,65,127,256,1024]:
            payload=rng.randbytes(size)
            a=base64.b64encode(payload);b=base64.urlsafe_b64encode(payload).rstrip(b'=')
            assert run(2,payload)==a and run(3,a)==payload,(size,a)
            assert run(4,payload)==b and run(5,b)==payload,(size,b)
        for invalid in [b'A',b'====',b'AA=A',b'AA===',b'AB==',b'AAB=',b'AA\n=',b'AA-_']:
            assert run(3,invalid)==b'error',invalid
        for invalid in [b'A',b'AB',b'AAB',b'AA==',b'AA+/',b'AA\n']:
            assert run(5,invalid)==b'error',invalid
        print('PASS strict Base64 and unpadded Base64url binary/malformed vectors',flush=True)
if __name__=='__main__':main()
