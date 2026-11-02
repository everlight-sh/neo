#!/usr/bin/env python3
"""Run the actual measured map executable in a root containing only that file."""
import argparse,os,shutil,subprocess,tempfile,sys
from pathlib import Path
from kernel_runtime_smoke import audit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bench/maps'))
from run import PHASES,expected

def main():
 p=argparse.ArgumentParser();p.add_argument('--binary',required=True,type=Path);a=p.parse_args();assert os.geteuid()==0 and not os.environ.get('NEO_RUNNER');audit(a.binary.resolve())
 with tempfile.TemporaryDirectory(prefix='neo-map-empty-') as tmp:
  root=Path(tmp);shutil.copy2(a.binary,root/'map')
  for mode in ['0','1']:
   process=subprocess.Popen(['chroot',str(root),'/map','1000000',mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   try:
    for phase in PHASES:
     line=process.stdout.readline().split();assert len(line)==4,(phase,line)
     actual,ns,checksum,count=line;assert actual==phase and (int(checksum),int(count))==expected(phase,1000000),(phase,line)
     process.stdin.write('x');process.stdin.flush()
    assert process.wait(timeout=10)==0,process.stderr.read()
   finally:
    if process.poll() is None:process.kill();process.wait()
  assert [v.name for v in root.iterdir()]==['map']
 print('PASS measured 1M-entry map in growing/preallocated modes: insert, lookup, update, deletion and miss checks; executable only, no libraries/files/devices',flush=True)
if __name__=='__main__':main()
