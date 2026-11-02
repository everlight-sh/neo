#!/usr/bin/env python3
"""Check runtime/parallel compatibility against outputs from the original runtime."""
import math
import os
import shlex
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNNER = shlex.split(os.environ.get('NEO_RUNNER', ''))
CASES = {
    'hello': ([], 'Hello, World!'),
    'greet': (['7'], 'Hello, 7!'),
    'mandel': (['200', '200', '100'], '842053'),
    'stencil': (['1000', '3'], '499223042'),
    'sieve': (['10000'], '1229'),
    'nbody': (['100', '10'], '-0.88644769431012838'),
}


def main():
    with tempfile.TemporaryDirectory(prefix='neo-compute-test-') as tmp:
        for name, (args, expected) in CASES.items():
            binary = str(Path(tmp) / name)
            subprocess.run(['python3', '-m', 'neoc', 'build', f'examples/{name}.neo', '--no-cache', '-o', binary], cwd=ROOT, check=True)
            for threads in ('1', '4'):
                r = subprocess.run(RUNNER+[binary, *args], env=dict(os.environ, NEO_THREADS=threads), capture_output=True, text=True, timeout=20, check=True)
                actual = r.stdout.strip()
                assert actual == expected or (name == 'nbody' and math.isclose(float(actual), float(expected), rel_tol=1e-9)), (name, threads, actual)
            print(f'{name}: PASS (1 and 4 workers)', flush=True)
        for args, code in [([], 2), (['bad', '3'], 2), (['0', '3'], 3), (['99999999999999999999999', '3'], 2)]:
            r = subprocess.run(RUNNER+[str(Path(tmp) / 'stencil'), *args], capture_output=True, timeout=3)
            assert r.returncode == code, (args, r.returncode)
        print('argv parsing and refinement boundaries: PASS', flush=True)


if __name__ == '__main__': main()
