#!/usr/bin/env python3
"""Native profile/cache isolation and checked-overflow regression test."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='neo-build-profiles-') as temporary:
        folder = Path(temporary)
        source = folder/'main.neo'
        source.write_text('fn twice(n:i64)->i64=n*2\nfn dead()->i64=999\nexport fn public_entry()->i64=42\nfn main(n:i64)->i64=let call=function(twice) in call(n)+1\n')
        keys = set()
        for level,budget in [(3,160),(0,160),(3,100),(0,100)]:
            binary = folder/f'app-{level}-{budget}'
            command = [sys.executable,'-m','neoc','build',str(source),'-o',str(binary),'--report','--opt-level',str(level)]
            env = {**os.environ,'NEO_INLINE_BUDGET':str(budget)}
            first = subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True)
            assert first.returncode == 0,first.stdout+first.stderr
            report = json.loads(first.stdout)
            assert report['build']['cache'] == 'miss' and not report['undefined_symbols']
            assert report['optimization']['level']==level and report['optimization']['inline_budget']==budget
            assert any(name.endswith('_dead__par') for name in report['omitted_internal_functions'])
            assert 'public_entry' in subprocess.check_output(['nm',str(binary)],text=True)
            assert report['cache_key'] not in keys
            keys.add(report['cache_key'])
            second = subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True)
            assert second.returncode == 0 and json.loads(second.stdout)['build']['cache'] == 'hit'
            run = subprocess.run([str(binary),'7'],capture_output=True,text=True)
            assert run.returncode == 0 and run.stdout == '15\n',run
            overflow = subprocess.run([str(binary),str((1<<63)-1)],capture_output=True,text=True)
            assert overflow.returncode != 0 and 'overflow' in overflow.stderr,overflow
        source.write_text('fn main(n:i64)->i64=n*3+1\n')
        changed = subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True)
        assert changed.returncode == 0 and json.loads(changed.stdout)['build']['cache'] == 'miss'
        assert subprocess.check_output([str(binary),'7'],text=True) == '22\n'
        source.write_text('fn main(n:i64{n>=0})->i64=let values=arr(i in 0..n) i in values[n]\n')
        for level in ('0','3'):
            rejected = subprocess.run([*command[:-1],level],cwd=ROOT,env=env,capture_output=True,text=True)
            assert rejected.returncode != 0 and 'unproven obligations' in rejected.stdout,rejected.stdout
    print('PASS dev/release and inline-budget cache isolation, source invalidation, checked overflow and no runtime imports')


if __name__ == '__main__':main()
