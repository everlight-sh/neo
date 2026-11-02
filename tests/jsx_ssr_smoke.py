#!/usr/bin/env python3
"""Compare native TSX->Neo SSR with actual React on the same TSX source."""
import argparse
import json
import os
from pathlib import Path
import subprocess

import ssr_smoke as smoke
from kernel_runtime_smoke import audit

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--empty-root', action='store_true')
    args = parser.parse_args()
    binary = args.binary.resolve()
    audit(binary)
    env = dict(os.environ, NODE_ENV='production')
    output = subprocess.check_output(['bun', 'run', 'fixtures.ts'], cwd=ROOT/'examples/jsx-ssr', env=env, text=True)
    fixtures = {int(k): v.encode() for k, v in json.loads(output).items()}
    assert len(fixtures) == 1000
    assert b'&lt;script&gt;' in fixtures[13] and b'<script>' not in fixtures[13]
    assert 'café 🚀'.encode() in fixtures[13]
    assert b'Featured &amp; independent' in fixtures[2] and b'Featured &amp; independent' not in fixtures[3]
    smoke.reference = lambda n: fixtures[n]
    smoke.COUNTS = tuple(range(1, 1001))
    for workers in ('1', '4'):
        smoke.verify([str(binary)], dict(env, NEO_THREADS=workers), quiet=True)
        print(f'PASS: TSX->Neo vs React, all 1000 inputs, {workers} worker(s); concurrent + pipelined HTTP', flush=True)
    smoke.verify(['bun', 'run', str(ROOT/'examples/jsx-ssr/reference.tsx')], env, quiet=True)
    print('PASS: Bun/React reference HTTP routes', flush=True)
    if args.empty_root:
        import platform
        import shutil
        import tempfile
        assert platform.system() == 'Linux' and os.geteuid() == 0, '--empty-root needs Linux root'
        with tempfile.TemporaryDirectory(prefix='neo-jsx-empty-') as tmp:
            shutil.copy2(binary, Path(tmp)/'server')
            smoke.verify(['chroot', tmp, '/server'], dict(env, NEO_THREADS='4'), quiet=True)
        print('PASS: generated Neo server runs with only its binary in an empty root', flush=True)


if __name__ == '__main__':
    main()
