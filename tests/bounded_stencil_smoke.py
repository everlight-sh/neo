#!/usr/bin/env python3
"""Differential native tests: optimized/unoptimized code and a wrapping-i64 oracle."""
import json
import os
from pathlib import Path
import random
import shlex
import subprocess
import tempfile

from kernel_runtime_smoke import audit

ROOT = Path(__file__).resolve().parents[1]


def wrap(x):
    return (x + (1 << 63)) % (1 << 64) - (1 << 63)


def rem(x, divisor=1000003):
    return (abs(x) % divisor) * (-1 if x < 0 else 1)


def reference(n, seed, passes):
    a = [rem(wrap(wrap(i * seed) + seed)) for i in range(n)]
    for _ in range(passes):
        a = [a[i] if i == 0 or i + 1 == n else rem(wrap(a[i-1] + 2*a[i] + a[i+1])) for i in range(n)]
    wide = rem(rem(seed, 1000000000003) * 7, 1000000000003)
    small = rem(rem(seed, 17) * 7, 17)
    unknown = rem(wrap(wrap(seed * 3) + 1))
    return wrap(sum(a) + wide + small + unknown)


def main():
    rng = random.Random(20261023)
    seeds = [0, 1, -1, 1000002, -1000003, 2654435761, -(1 << 63), (1 << 63)-1]
    seeds += [rng.randrange(-(1 << 63), 1 << 63) for _ in range(8)]
    sizes = [1, 2, 3, 7, 8, 9, 15, 16, 17, 31, 32, 33, 129]
    cases = [(n, seed, passes) for n in sizes for seed in seeds for passes in (0, 1, 2, 7, 32)]
    with tempfile.TemporaryDirectory(prefix='neo-bounded-stencil-') as tmp:
        for optimize in ('0', '1'):
            binary = Path(tmp)/('stencil-'+optimize)
            build = subprocess.run(['python3', '-m', 'neoc', 'build', 'tests/fixtures/bounded_stencil.neo', '--no-cache', '--report', '-o', str(binary)],
                                   cwd=ROOT, env=dict(os.environ, NEO_RANGE=optimize), capture_output=True, text=True, check=True)
            report = json.loads(build.stdout)
            assert bool(report['bounded_remainders']) == (optimize == '1'), report['bounded_remainders']
            if optimize == '1':
                assert {r['width'] for r in report['bounded_remainders']} == {32, 64}
                assert all(r['fn'] != 'unknown' for r in report['bounded_remainders'])
            audit(binary)
            for n, seed, passes in cases:
                r = subprocess.run(shlex.split(os.environ.get('NEO_RUNNER', ''))+[str(binary), str(n), str(seed), str(passes)], check=True, capture_output=True, text=True,
                                   timeout=10, env=dict(os.environ, NEO_THREADS='1'))
                assert int(r.stdout) == reference(n, seed, passes), (optimize, n, seed, passes, r.stdout)
            print(f'NEO_RANGE={optimize}: {len(cases)} signed/overflow/tail/iteration cases PASS', flush=True)


if __name__ == '__main__': main()
