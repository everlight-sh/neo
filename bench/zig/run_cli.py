#!/usr/bin/env python3
"""Vif vs Zig compute and JSON command-line workloads on a 2-vCPU Linux box.

compute: follows RESULTS-compute-db-x86-linux-2026-10-30.md (median
  complete-process ms, interleaved rounds after a warm-up; one worker pinned
  to CPU 0, two workers to CPUs 0-1 via NEO_THREADS / ZIG_THREADS) plus the
  bench/run.py sieve and 50M stencil sizes.
json: follows bench/json/run.py (every process pinned to CPU 0, NEO_THREADS=1,
  2 warm-ups then the measured runs, order shuffled each round with a fixed
  seed, wall time and GNU time peak RSS).
Every output is checked: integers exactly, nbody energies within 1e-9
(relative, as bench/run.py).

With BIN_BEFORE set, a 'Vif before' variant (the same programs built by an
earlier compiler/runtime) runs interleaved with the others.

usage: run_cli.py compute|json OUT.json ROUNDS
"""
import json, os, random, resource, statistics, subprocess, sys, time
from pathlib import Path

VIF = Path(os.environ.get('BIN', '/root/bin'))
ZIG = Path(os.environ.get('ZIGBIN', '/root/zig-baseline/bin'))
ZIGN = Path(os.environ.get('ZIGNATIVE', '/root/zig-native/bin'))
BEFORE = Path(os.environ['BIN_BEFORE']) if os.environ.get('BIN_BEFORE') else None

COMPUTE = [  # name, args, float output?
    ('mandel', ['1200', '1200', '300'], False),
    ('stencil', ['1000000', '20'], False),
    ('stencil', ['50000000', '20'], False),
    ('nbody', ['1024', '3'], True),
    ('nbody', ['4096', '10'], True),
    ('sieve', ['100000000'], False),
]
JSON = [  # case, {variant: argv}
    ('doc x1M', {'Vif': [VIF/'vif-library_bench', '0', '1000000'],
                 'Zig Value': [ZIG/'json', 'doc-value', '1000000'], 'Zig typed': [ZIG/'json', 'doc-typed', '1000000'],
                 'Zig Value arena': [ZIG/'json', 'doc-value-arena', '1000000'], 'Zig typed arena': [ZIG/'json', 'doc-typed-arena', '1000000'],
                 'Zig Value native': [ZIGN/'json', 'doc-value', '1000000'], 'Zig typed native': [ZIGN/'json', 'doc-typed', '1000000']}),
    ('orders 1000 x1000', {'Vif': [VIF/'vif-orders_json', '1000', '1000'],
                 'Zig Value': [ZIG/'json', 'orders-value', '1000'], 'Zig typed': [ZIG/'json', 'orders-typed', '1000'],
                 'Zig Value arena': [ZIG/'json', 'orders-value-arena', '1000'], 'Zig typed arena': [ZIG/'json', 'orders-typed-arena', '1000'],
                 'Zig Value native': [ZIGN/'json', 'orders-value', '1000'], 'Zig typed native': [ZIGN/'json', 'orders-typed', '1000']}),
]


def measure(argv, cpus, env):
    tf = '/tmp/cli.time'
    cmd = ['/usr/bin/time', '-f', '%M', '-o', tf, 'taskset', '-c', cpus, *map(str, argv)]
    before = resource.getrusage(resource.RUSAGE_CHILDREN); t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env={**os.environ, **env})
    wall = time.perf_counter() - t0; after = resource.getrusage(resource.RUSAGE_CHILDREN)
    assert r.returncode == 0, (cmd, r.returncode, r.stderr)
    return {'wall_ms': wall*1000, 'cpu_ms': (after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)*1000,
            'peak_rss_kib': int(open(tf).read().split()[-1]), 'out': r.stdout.strip()}


def same(outs, is_float):
    if is_float:
        vals = [float(o) for o in outs]
        return max(vals) - min(vals) <= 1e-9 * max(1.0, abs(vals[0]))
    return len(set(outs)) == 1


def compute(rounds):
    results = []
    for workers, cpus in ((1, '0'), (2, '0-1')):
        env = {'NEO_THREADS': str(workers), 'ZIG_THREADS': str(workers)}
        for prog, args, is_float in COMPUTE:
            variants = {'Vif': [VIF/f'vif-{prog}', *args], 'Zig': [ZIG/prog, *args], 'Zig native': [ZIGN/prog, *args]}
            if BEFORE: variants['Vif before'] = [BEFORE/f'vif-{prog}', *args]
            runs = {v: [] for v in variants}
            for r in range(rounds + 1):
                order = list(variants) if r % 2 == 0 else list(variants)[::-1]
                for v in order:
                    m = measure(variants[v], cpus, env)
                    if r > 0: runs[v].append(m)
            outs = [m['out'] for rs in runs.values() for m in rs]
            ok = same(outs, is_float)
            case = f"{prog}-{'-'.join(args)}"
            results.append({'case': case, 'workers': workers, 'cpus': cpus, 'outputs_agree': ok, 'runs': runs})
            line = '  '.join(f"{v} {statistics.median(m['wall_ms'] for m in rs):8.1f} ms" for v, rs in runs.items())
            print(f"{case:22s} w={workers}  {line}  {'ok' if ok else 'OUTPUT MISMATCH ' + str(set(outs))}", flush=True)
    return results


def json_suite(rounds):
    rng = random.Random(2026110117); results = []
    for case, variants in JSON:
        if BEFORE: variants = {**variants, 'Vif before': [BEFORE/Path(variants['Vif'][0]).name, *variants['Vif'][1:]]}
        runs = {v: [] for v in variants}
        for r in range(rounds + 2):
            order = list(variants); rng.shuffle(order)
            for v in order:
                m = measure(variants[v], '0', {'NEO_THREADS': '1'})
                if r >= 2: runs[v].append(m)
        outs = [m['out'] for rs in runs.values() for m in rs]
        ok = same(outs, False)
        results.append({'case': case, 'outputs_agree': ok, 'checksum': outs[0], 'runs': runs})
        line = '  '.join(f"{v} {statistics.median(m['wall_ms'] for m in rs):8.1f}" for v, rs in runs.items())
        print(f"{case:18s} {line}  {'ok' if ok else 'OUTPUT MISMATCH ' + str(set(outs))}", flush=True)
    return results


def main():
    suite, out, rounds = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
    data = {'suite': suite, 'rounds': rounds, 'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    data['results'] = compute(rounds) if suite == 'compute' else json_suite(rounds)
    data['finished'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    out.write_text(json.dumps(data, indent=1))


if __name__ == '__main__':
    main()
