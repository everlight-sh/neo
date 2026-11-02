#!/usr/bin/env python3
"""Loop record transfers preserve aliases and avoid copies of dead old fields."""
import os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 with tempfile.TemporaryDirectory(prefix='neo-loop-fields-') as t:
  binary=Path(t)/'probe';env={**os.environ,'NEO_ALLOC_STATS':'1'}
  r=subprocess.run(['python3','-m','neoc','build',str(ROOT/'tests/fixtures/loop_record_fields.neo'),'-o',str(binary)],cwd=ROOT,env=env,capture_output=True,text=True);assert r.returncode==0,(r.stdout[:2500],r.stderr[-2500:])
  checked=0
  for threads in ['1','4']:
   for n in [1,7,512,8192]:
    for rounds in [0,1,2,31,1000]:
     for mode in [0,1,2,3]:
      left=list(range(n));right=[-i for i in range(n)];salt=7
      for i in range(rounds):
       at=i%n
       if mode==3:right=list(left);left[at]=777;salt=sum(right)
       else:left[at]=i+7;right[at]=-i-7
      if mode==2:right=[]
      wanted=[sum(left),sum(right),n*(n-1)//2 if mode==1 else 0,salt]
      r=subprocess.run([str(binary),str(n),str(rounds),str(mode)],env={**os.environ,'NEO_THREADS':threads},capture_output=True,text=True,timeout=30);assert r.returncode==0,(n,rounds,mode,threads,r.stderr)
      got=list(map(int,r.stdout.split()));assert got[:4]==wanted,(n,rounds,mode,threads,got,wanted)
      if mode<3:
       assert got[4]<=3 and got[5]<=2*n*8+512,(n,rounds,mode,threads,got)
      else:assert got[4]<=rounds+2 and got[5]<=(rounds+1)*(n*8+128),(n,rounds,threads,got)
      checked+=1
 print(f'PASS {checked} independent loop record states: zero/body/exit lifetimes, field and whole-record yields, retained snapshots, overlapping call borrows, 1/4 workers and constant allocation bounds',flush=True)
if __name__=='__main__':main()
