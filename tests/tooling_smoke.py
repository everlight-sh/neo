#!/usr/bin/env python3
"""Native project workflow, cache invalidation/tampering and concurrent builds."""
import concurrent.futures
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))

def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);source=root/'main.neo';lib=root/'lib.neo';binary=root/'app'
        source.write_text('import "lib.neo" fn main () -> i64 = answer()\n')
        lib.write_text('fn answer () -> i64 = 1\n')
        command=[sys.executable,'-m','neoc','build',str(source),'-o',str(binary),'--report']
        def build():
            r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
            assert r.returncode==0,r.stdout+r.stderr
            return json.loads(r.stdout)
        first=build();second=build()
        assert first['build']['cache']=='miss' and second['build']['cache']=='hit'
        assert subprocess.check_output(RUNNER+[str(binary)]).strip()==b'1'
        lib.write_text('fn answer () -> i64 = 2\n');changed=build()
        assert changed['build']['cache']=='miss' and changed['cache_key']!=first['cache_key']
        assert subprocess.check_output(RUNNER+[str(binary)]).strip()==b'2'
        cached=root/'.neo-build'/(changed['cache_key']+'.bin');cached.write_bytes(b'tampered')
        assert build()['build']['cache']=='miss'
        lib.write_text('fn answer () -> i64 = 3\n')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:build(),range(2)))
        assert subprocess.check_output(RUNNER+[str(binary)]).strip()==b'3'
        source.write_text('fn main () -> i64 = missing(\n')
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        assert result.returncode!=0 and json.loads(result.stdout)['ok'] is False and 'Traceback' not in result.stdout+result.stderr
        if sys.platform=='linux' and not os.environ.get('NEO_RUNNER'):
            import hashlib
            hashes=[]
            for directory in ('relocated-a','relocated-b'):
                project=root/directory;project.mkdir()
                (project/'neo.toml').write_text('[package]\nname="reproducible"\nversion="0.1.0"\n')
                file=project/'main.neo';file.write_text('fn identity<T>(value:T) -> T = value fn main(x:i64) -> i64 = identity(x)')
                app=project/'app'
                r=subprocess.run([sys.executable,'-m','neoc','build',str(file),'-o',str(app),'--report'],cwd=ROOT,capture_output=True,text=True)
                assert r.returncode==0,r.stdout+r.stderr;hashes.append(hashlib.sha256(app.read_bytes()).hexdigest())
            assert hashes[0]==hashes[1],hashes
            print('PASS identical native Linux binaries across project relocation',flush=True)
    print('PASS project cache: warm hit, imported edits, tamper detection, concurrent atomic publication and structured diagnostics',flush=True)

if __name__=='__main__':main()
