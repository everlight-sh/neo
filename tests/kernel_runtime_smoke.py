#!/usr/bin/env python3
"""Audit imports and exercise freestanding runtime primitives and fork results."""
import os
from pathlib import Path
import platform
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNNER = shlex.split(os.environ.get('NEO_RUNNER', ''))


def audit(binary):
    symbols = subprocess.check_output(['nm', '-u', str(binary)], text=True).strip()
    assert not symbols, symbols
    if platform.system() == 'Linux':
        headers = subprocess.check_output(['readelf', '-l', str(binary)], text=True)
        dynamic = subprocess.check_output(['readelf', '-d', str(binary)], text=True)
        assert 'INTERP' not in headers and 'NEEDED' not in dynamic
    print('Dependency audit: no undefined imports' + ('; static ELF, no interpreter/shared libraries' if platform.system() == 'Linux' else '; macOS loader still requires libSystem'), flush=True)


def main():
    with tempfile.TemporaryDirectory(prefix='neo-kernel-test-') as tmp:
        for name in ('kernel_runtime', 'parallel_runtime', 'memory_blocks'):
            binary = Path(tmp)/name
            subprocess.run(['python3', '-m', 'neoc', 'build', str(ROOT/'tests/fixtures'/f'{name}.neo'), '--no-cache', '-o', str(binary)], cwd=ROOT, check=True)
            audit(binary)
            for threads in ('1', '4'):
                n = 8192
                expected = 0 if name == 'memory_blocks' else 765+sum(i % 251 for i in range(n)) if name == 'kernel_runtime' else n*(3*(n-1)+2)//2
                r = subprocess.run(RUNNER+[str(binary), str(n)], capture_output=True, text=True, timeout=15,
                                   env=dict(os.environ, NEO_THREADS=threads), check=True)
                assert r.stdout.strip() == str(expected), (name, threads, r.stdout, r.stderr)
            print(name+': PASS (1 and 4 workers)', flush=True)


if __name__ == '__main__': main()
