#!/usr/bin/env python3
"""Regression for BSS-only ELF state pages and the x86 compatibility loader."""
import os,platform,shutil,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 if platform.system()!='Linux':print('SKIP ELF loader layout: Linux only');return
 native=platform.machine() in ('x86_64','amd64')
 if not native and not shutil.which('ld.lld'):print('SKIP cross-x86 ELF layout: ld.lld unavailable');return
 with tempfile.TemporaryDirectory(prefix='neo-elf-layout-') as t:
  p=Path(t);source=p/'probe.neo';source.write_text((ROOT/'tests/fixtures/data_sync.neo').read_text());binary=p/'probe'
  r=subprocess.run(['python3','-m','neoc','build',str(source),'--target','x86_64-unknown-linux-gnu','-o',str(binary)],cwd=ROOT,capture_output=True,text=True);assert r.returncode==0,(r.stdout[:3000],r.stderr[-3000:])
  raw=binary.read_bytes();assert raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',raw,18)[0]==62
  offset=struct.unpack_from('<Q',raw,32)[0];size,count=struct.unpack_from('<HH',raw,54);found=False
  for i in range(count):
   tag,flags,at,address,physical,files,memory,alignment=struct.unpack_from('<IIQQQQQQ',raw,offset+i*size)
   assert tag!=3,'Freestanding image must have no ELF interpreter'
   if tag==1 and flags&2 and files==0 and memory>0:assert address%4096==0,(address,files,memory);found=True
  assert found,'Expected a checked BSS-only runtime state segment'
  assert not subprocess.check_output(['nm','-u',str(binary)],text=True).strip()
  executed=native or os.environ.get('NEO_TEST_CROSS_X86')=='1'
  if executed:
   r=subprocess.run([str(binary),str(p/'data')],capture_output=True,text=True,timeout=30);assert r.returncode==0 and r.stdout=='ok\n',(r.returncode,r.stdout,r.stderr)
   assert (p/'data').read_bytes()==b'FIRST-second'
 print('PASS x86 freestanding ELF: page-aligned BSS state, no imports/interpreter'+('; data-sync execution passed'+(' natively' if native else ' through compatibility runner') if executed else ''),flush=True)
if __name__=='__main__':main()
