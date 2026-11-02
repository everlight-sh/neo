#!/usr/bin/env python3
"""Self-contained native stdlib reactor/half-close/owner-generation checks."""
import tempfile,subprocess
from pathlib import Path
from agent_codecs import build,RUNNER

def main():
    with tempfile.TemporaryDirectory(prefix='neo-reactor-') as tmp:
        binary=Path(tmp)/'reactor';build('tests/fixtures/reactor.neo',binary)
        result=subprocess.run(RUNNER+[str(binary)],capture_output=True,timeout=10)
        assert result.returncode==0 and result.stdout==b'reactor OK\n',(result.returncode,result.stdout,result.stderr)
        binary=Path(tmp)/'datagram';build('tests/fixtures/datagram.neo',binary)
        result=subprocess.run(RUNNER+[str(binary)],capture_output=True,timeout=10)
        assert result.returncode==0 and result.stdout==b'UDP OK\n',(result.returncode,result.stdout,result.stderr)
        print('PASS scoped UDP zero-length datagrams, bounds, address/port, readiness and cancellation',flush=True)
        print('PASS multi-descriptor reactor, subprocess EOF, stale generations, deadline/cancellation and resource cleanup',flush=True)
if __name__=='__main__':main()
