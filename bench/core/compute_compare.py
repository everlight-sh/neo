#!/usr/bin/env python3
"""Neo vs Rust, Go and Bun on the compute kernels, interleaved and pinned.

Follows RESULTS-core-regression-linux-2026-10-27.md: median complete-process
milliseconds, one warm-up round excluded, variant order shuffled every round
with a fixed seed, one worker pinned to CPU 0 and four workers to CPUs 0-3
(NEO_THREADS / RAYON_NUM_THREADS / GOMAXPROCS; Go sizes its pools from the
affinity mask). Bun is single-threaded and runs only in the one-worker rows.
Every output is checked: integers exactly, nbody energies within 1e-9
relative, as bench/run.py.

Neo variants are directories of executables named neo-<program>; pass one or
more as --variant NAME=DIR (the first is the headline column).

usage: compute_compare.py OUT.json ROUNDS --variant Neo=/root/bin [--variant ...]
         [--rust DIR] [--go DIR] [--bun] [--workers 1,4] [--cases mandel,stencil,...|all]
"""
import argparse, json, os, random, resource, statistics, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = [  # program, args, float output?
    ('mandel', ['1200', '1200', '300'], False),
    ('stencil', ['1000000', '20'], False),
    ('nbody', ['1024', '3'], True),
    ('nbody', ['4096', '10'], True),
]
# The x86-64 report's extra rows (RESULTS-zig-x86-linux-2026-11-02.md); --cases all adds them.
# Rust, Go and Bun have no sieve, so that row compares Neo variants only.
EXTRA = [
    ('stencil', ['50000000', '20'], False),
    ('sieve', ['100000000'], False),
]


def measure(argv, cpus, workers):
    tf = '/tmp/compute-compare.time'
    cmd = ['/usr/bin/time', '-f', '%M', '-o', tf, 'taskset', '-c', cpus, *map(str, argv)]
    env = {**os.environ, 'NEO_THREADS': str(workers), 'RAYON_NUM_THREADS': str(workers), 'GOMAXPROCS': str(workers)}
    before = resource.getrusage(resource.RUSAGE_CHILDREN); t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
    wall = time.perf_counter() - t0; after = resource.getrusage(resource.RUSAGE_CHILDREN)
    assert r.returncode == 0, (cmd, r.returncode, r.stderr)
    return {'wall_ms': wall * 1000, 'cpu_ms': (after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime) * 1000,
            'peak_rss_kib': int(open(tf).read().split()[-1]), 'out': r.stdout.strip()}


def agree(outs, is_float):
    if not is_float: return len(set(outs)) == 1
    vals = [float(o) for o in outs]
    return max(vals) - min(vals) <= 1e-9 * max(1.0, abs(vals[0]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('out', type=Path); p.add_argument('rounds', type=int)
    p.add_argument('--variant', action='append', default=[], help='NAME=DIR of neo-<program> executables')
    p.add_argument('--rust', type=Path, help='directory of Rust executables (bench/rust target/release)')
    p.add_argument('--go', type=Path, help='directory of Go executables <program>_bin (bench/go)')
    p.add_argument('--bun', action='store_true', help='include bench/core/compute.ts in one-worker rows')
    p.add_argument('--workers', default='1,4'); p.add_argument('--cases', default='')
    p.add_argument('--seed', type=int, default=20261103)
    a = p.parse_args()
    neo = [(v.split('=', 1)[0], Path(v.split('=', 1)[1])) for v in a.variant]
    wanted = a.cases.split(',') if a.cases and a.cases != 'all' else []
    cases = [c for c in CASES + EXTRA if (not wanted and (a.cases == 'all' or c in CASES)) or c[0] in wanted or f"{c[0]}-{'-'.join(c[1])}" in wanted]
    rng = random.Random(a.seed)
    data = {'rounds': a.rounds, 'warmups': 1, 'seed': a.seed, 'variants': {n: str(d) for n, d in neo},
            'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'results': []}
    for workers in map(int, a.workers.split(',')):
        cpus = '0' if workers == 1 else f'0-{workers - 1}'
        for prog, args, is_float in cases:
            variants = {name: [d / f'neo-{prog}', *args] for name, d in neo}
            if a.rust and (a.rust / prog).exists(): variants['Rust'] = [a.rust / prog, *args]
            if a.go and (a.go / f'{prog}_bin').exists(): variants['Go'] = [a.go / f'{prog}_bin', *args]
            if a.bun and workers == 1 and prog != 'sieve': variants['Bun'] = ['bun', ROOT / 'bench/core/compute.ts', prog, *args]
            runs = {v: [] for v in variants}
            for r in range(a.rounds + 1):
                order = list(variants); rng.shuffle(order)
                for v in order:
                    m = measure(variants[v], cpus, workers); m['round'] = r
                    if r > 0: runs[v].append(m)
            outs = [m['out'] for rs in runs.values() for m in rs]
            ok = agree(outs, is_float)
            case = f"{prog}-{'-'.join(args)}"
            data['results'].append({'case': case, 'workers': workers, 'cpus': cpus, 'outputs_agree': ok,
                                    'argv': {v: list(map(str, x)) for v, x in variants.items()}, 'runs': runs})
            line = '  '.join(f"{v} {statistics.median(m['wall_ms'] for m in rs):8.1f}" for v, rs in runs.items())
            print(f"{case:22s} w={workers}  {line}  {'ok' if ok else 'OUTPUT MISMATCH ' + str(sorted(set(outs)))}", flush=True)
            a.out.write_text(json.dumps(data, indent=1))
    data['finished'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    a.out.write_text(json.dumps(data, indent=1))


if __name__ == '__main__':
    main()
