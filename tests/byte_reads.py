#!/usr/bin/env python3
"""Independent byte order/range oracle, aliases and generated-code traps."""
import json,os,random,shlex,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build(source,binary):
 r=subprocess.run(['python3','-m','neoc','build',str(source),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);assert r.returncode==0,(r.stdout[-3000:],r.stderr[-3000:]);assert not subprocess.check_output(['nm','-u',str(binary)],text=True).strip()
def main():
 rng=random.Random(271027);cases=[];expected=[];runner=shlex.split(os.environ.get('NEO_RUNNER',''))
 for n in [8,9,15,16,17,31,32,33,63,64,65,127,128,129,511,512,8192]:
  for width in [1,2,4,8]:
   for sliced in [0,1]:
    for at in sorted({0,1,n-width,*[rng.randrange(n-width+1) for _ in range(4)]}):
     if at>n-width:continue
     seed=rng.randrange(256);data=bytes(((i+(3 if sliced else 0))*37+seed)%256 for i in range(n));changed=bytes([1])+data[1:]
     cases.append(dict(n=n,seed=seed,at=at,width=width,slice=sliced));expected.append([int.from_bytes(data[at:at+width],'little',signed=width==8),int.from_bytes(changed[at:at+width],'little',signed=width==8),sum(data)])
 for word in [-2**63,2**63-1,-1,0,1]:
  for width in [1,2,4,8]:
   data=bytes((word>>(8*i))&255 for i in range(width))+bytes((i*37+17)%256 for i in range(width,8));changed=bytes([1])+data[1:]
   cases.append(dict(n=8,seed=17,at=0,width=width,slice=0,word=word));expected.append([int.from_bytes(data[:width],'little',signed=width==8),int.from_bytes(changed[:width],'little',signed=width==8),sum(data)])
 with tempfile.TemporaryDirectory(prefix='neo-byte-reads-') as tmp:
  folder=Path(tmp);binary=folder/'reads';build('tests/fixtures/byte_reads.neo',binary)
  for threads in ['1','4']:
   for start in range(0,len(cases),120):
    payload=''.join(json.dumps(x).encode().hex()+'\n' for x in cases[start:start+120]);r=subprocess.run(runner+[str(binary)],input=payload,capture_output=True,text=True,timeout=45,env={**os.environ,'NEO_THREADS':threads});assert r.returncode==0,(start,threads,r.stderr)
    actual=[json.loads(x) for x in r.stdout.splitlines()];assert actual==expected[start:start+120],(start,threads,actual[:2],expected[start:start+2])
  source=folder/'bad.neo';source.write_text('import "std:io"\neffect(fs) fn main(at:i64,width:i64)->unit=let data=byte_slice("ABCDEFGHIJKLMNOP",4,12) in let value=byte_read_le(data,at,width) in let shown=print_out(int_text(value)) in noop()\n');build(source,folder/'bad')
  for at,width in [(-1,1),(8,1),(1,8),(7,2),(5,4),(0,-1),(0,0),(0,3),(0,5),(0,6),(0,7),(0,9),(-2**63,1),(2**63-1,1),(0,-2**63),(0,2**63-1)]:
   r=subprocess.run(runner+[str(folder/'bad'),str(at),str(width)],capture_output=True,timeout=20);assert r.returncode!=0,(at,width,r.stdout)
 print(f'PASS {len(cases)} independent little-endian word reads and scalar reductions, unaligned/sliced boundaries, signed 64-bit values, retained/mutated aliases, record/index/temporary source lifetimes and 16 invalid offset/width traps; 1/4 workers',flush=True)
if __name__=='__main__':main()
