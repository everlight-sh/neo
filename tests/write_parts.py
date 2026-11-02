#!/usr/bin/env python3
"""Multipart writes preserve concatenation and cumulative short-write errors."""
import os,resource,signal,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'.kernel-build/write-parts';folder.mkdir(exist_ok=True,parents=True);binary=folder/'probe'
    run=subprocess.run(['python3','-m','neoc','build','tests/fixtures/write_parts.neo','-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
    assert run.returncode==0,(run.stdout[-3000:],run.stderr[-3000:])
    run=subprocess.run([str(binary),'0'],capture_output=True,timeout=30);assert run.returncode==0 and run.stdout==b'abcdefghij',(run.returncode,run.stdout,run.stderr)
    def limit():
        signal.signal(signal.SIGXFSZ,signal.SIG_IGN);resource.setrlimit(resource.RLIMIT_FSIZE,(7,7))
    with tempfile.TemporaryFile() as output:
        run=subprocess.run([str(binary),'1'],stdout=output,stderr=subprocess.PIPE,preexec_fn=limit,timeout=30)
        output.seek(0);assert run.returncode==0 and run.stderr==b'partial 7\n' and output.read()==b'abcdefg',(run.returncode,run.stderr)
    print('PASS multipart file writes: empty spans, exact content/count, real short write and cumulative error offset')
if __name__=='__main__':main()
