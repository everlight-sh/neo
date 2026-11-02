#!/usr/bin/env python3
import os,shutil,subprocess,tempfile
from pathlib import Path
from agent_codecs import ROOT,build
from kernel_runtime_smoke import audit

def main():
    assert os.geteuid()==0 and not os.environ.get('NEO_RUNNER')
    out=ROOT/'.kernel-build/agent-core-readiness-2026-10-25/linux';out.mkdir(exist_ok=True)
    for fixture,name in [('resource_arena','arena'),('agent_libraries','libraries'),('agent_process','parent'),('pure_process_child','child'),('agent_utilities','utilities'),('agent_transport','transport')]:
        build('tests/fixtures/'+fixture+'.neo',out/name);audit(out/name)
    with tempfile.TemporaryDirectory(prefix='neo-agent-empty-root-') as tmp:
        root=Path(tmp)
        for name in ['arena','libraries','parent','child','utilities']:shutil.copy2(out/name,root/name)
        for name,arguments,data,expected in [('arena',['/arena'],None,b'1\n3\n2\narena OK\n'),('libraries',[],None,b'agent libraries OK\n'),('parent',['/child'],None,b'child process OK\n'),('utilities',['6','/state'],b'private state',b'stored'),('utilities',['2'],'Straße Σ'.encode(),'strasse σ'.encode())]:
            result=subprocess.run(['chroot',str(root),'/'+name,*arguments],input=data,capture_output=True,timeout=20)
            assert result.returncode==0 and result.stdout==expected,(name,result.returncode,result.stdout,result.stderr)
        assert (root/'state').read_bytes()==b'private state'
        assert {p.name for p in root.iterdir()}=={'arena','libraries','parent','child','utilities','state'}
    print('PASS empty root: callbacks, managed resource reuse, JSON/SSE/tasks, Unicode, atomic persistence, and Neo-to-Neo process I/O; no libraries, shell or devices',flush=True)
if __name__=='__main__':main()
