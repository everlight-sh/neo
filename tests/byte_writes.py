#!/usr/bin/env python3
"""Value-semantic bounded buffer writes, including aliases and failures."""
import os,shlex,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'.kernel-build/byte-writes-tests';folder.mkdir(parents=True,exist_ok=True)
    binary=folder/'probe'
    run=subprocess.run(['python3','-m','neoc','build','tests/fixtures/byte_writes.neo','-o',str(binary)],cwd=ROOT,capture_output=True,text=True,env={**os.environ,'NEO_ALLOC_STATS':'1'})
    assert run.returncode==0,(run.stdout[-3000:],run.stderr[-3000:])
    assert not subprocess.check_output(['nm','-u',str(binary)],text=True).strip()
    runner=shlex.split(os.environ.get('NEO_RUNNER',''))
    for threads in ['1','4']:
        for count in [8,9,127,128,255,256,4096]:
            run=subprocess.run(runner+[str(binary),str(count)],capture_output=True,text=True,env={**os.environ,'NEO_THREADS':threads},timeout=30)
            assert run.returncode==0 and run.stdout=='byte writes OK\n',(threads,count,run.returncode,run.stdout,run.stderr)
    # Dynamic negative/oversized offsets and widths must trap in generated code.
    source=folder/'bad.neo';source.write_text('import "std:io"\neffect fn main(at:i64,width:i64) -> unit = let out=byte_write_le("12345678",at,42,width) in let printed=print_out(out) in noop()\n')
    subprocess.run(['python3','-m','neoc','build',str(source),'-o',str(folder/'bad')],cwd=ROOT,check=True,capture_output=True)
    for at,width in [(-1,1),(9,0),(1,8),(0,-1),(0,9),(2**63-1,1),(-2**63,1)]:
        run=subprocess.run(runner+[str(folder/'bad'),str(at),str(width)],capture_output=True,timeout=30)
        assert run.returncode!=0,(at,width,run.stdout)
    print('PASS byte writes: shared/static/sliced/overlapping buffers, source-field lifetime, signed little endian, empty spans, bounds/width traps; 1/4 workers')
if __name__=='__main__':main()
