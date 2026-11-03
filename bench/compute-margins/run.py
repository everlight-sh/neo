#!/usr/bin/env python3
"""Neo vs Zig and Rust compute rows on x86-64 Linux, under both transparent
huge page settings.

Follows bench/zig/run_cli.py: median complete-process wall time over
interleaved rounds after one warm-up round (order reversed every other
round), every process pinned with taskset (1 worker on CPU 0, W workers on
CPUs 0..W-1, via NEO_THREADS / ZIG_THREADS / RAYON_NUM_THREADS), GNU time for
peak RSS and minor faults, every output checked (integers exactly, nbody
within 1e-9 relative). Each THP setting is written to
/sys/kernel/mm/transparent_hugepage/enabled before its rounds (root needed);
the original setting is restored at the end.

usage: run.py OUT.json ROUNDS WORKERS[,WORKERS...] THP[,THP...] [CASE ...]
  CASE is prog:arg:arg (default: the rows below). Binaries:
  $NEO_AFTER/neo-PROG, $NEO_BEFORE/neo-PROG, $ZIG/PROG, $ZIG_NATIVE/PROG,
  $RUST/PROG; a variant whose binary is missing is skipped.
"""
import json, os, resource, statistics, subprocess, sys, time
from pathlib import Path

DEFAULT = ['stencil:1000000:20', 'stencil:50000000:20', 'sieve:100000000',
           'mandel:1200:1200:300', 'nbody:1024:3', 'nbody:4096:10']
FLOAT = {'nbody'}
THP = Path('/sys/kernel/mm/transparent_hugepage/enabled')


def variants(prog):
    dirs = [('Neo after', 'NEO_AFTER', f'neo-{prog}'), ('Neo before', 'NEO_BEFORE', f'neo-{prog}'),
            ('Zig', 'ZIG', prog), ('Zig native', 'ZIG_NATIVE', prog), ('Rust', 'RUST', prog)]
    out = {}
    for name, var, exe in dirs:
        if os.environ.get(var) and (Path(os.environ[var]) / exe).exists(): out[name] = str(Path(os.environ[var]) / exe)
    return out


def measure(argv, cpus, env):
    tf = '/tmp/margins.time'
    cmd = ['/usr/bin/time', '-f', '%M %R', '-o', tf, 'taskset', '-c', cpus, *argv]
    before = resource.getrusage(resource.RUSAGE_CHILDREN); t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env={**os.environ, **env})
    wall = time.perf_counter() - t0; after = resource.getrusage(resource.RUSAGE_CHILDREN)
    assert r.returncode == 0, (cmd, r.returncode, r.stderr)
    rss, faults = open(tf).read().split()[-2:]
    return {'wall_ms': wall * 1000, 'user_ms': (after.ru_utime - before.ru_utime) * 1000,
            'sys_ms': (after.ru_stime - before.ru_stime) * 1000, 'peak_rss_kib': int(rss),
            'minor_faults': int(faults), 'out': r.stdout.strip()}


def same(outs, is_float):
    if is_float:
        vals = [float(o) for o in outs]
        return max(vals) - min(vals) <= 1e-9 * max(1.0, abs(vals[0]))
    return len(set(outs)) == 1


def vmstat(key):
    for line in open('/proc/vmstat'):
        name, value = line.split()
        if name == key: return int(value)
    return None


def main():
    out, rounds = Path(sys.argv[1]), int(sys.argv[2])
    worker_counts = [int(w) for w in sys.argv[3].split(',')]
    thps = sys.argv[4].split(',')
    cases = sys.argv[5:] or DEFAULT
    original = THP.read_text().split('[')[1].split(']')[0]
    data = {'rounds': rounds, 'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'thp_original': original, 'defrag': THP.with_name('defrag').read_text().strip(), 'results': []}
    try:
        for thp in thps:
            THP.write_text(thp)
            for workers in worker_counts:
                cpus = '0' if workers == 1 else f'0-{workers - 1}'
                env = {'NEO_THREADS': str(workers), 'ZIG_THREADS': str(workers), 'RAYON_NUM_THREADS': str(workers)}
                for spec in cases:
                    prog, *args = spec.split(':')
                    vs = variants(prog)
                    runs = {v: [] for v in vs}
                    thp_before = vmstat('thp_fault_alloc')
                    for r in range(rounds + 1):
                        order = list(vs) if r % 2 == 0 else list(vs)[::-1]
                        for v in order:
                            m = measure([vs[v], *args], cpus, env)
                            if r > 0: runs[v].append(m)
                    outs = [m['out'] for rs in runs.values() for m in rs]
                    ok = same(outs, prog in FLOAT)
                    case = f"{prog}-{'-'.join(args)}"
                    data['results'].append({'case': case, 'workers': workers, 'cpus': cpus, 'thp': thp,
                                            'thp_fault_alloc': vmstat('thp_fault_alloc') - thp_before,
                                            'outputs_agree': ok, 'runs': runs})
                    line = '  '.join(f"{v} {statistics.median(m['wall_ms'] for m in rs):8.1f}" for v, rs in runs.items())
                    print(f"thp={thp:7s} {case:22s} w={workers}  {line}  {'ok' if ok else 'OUTPUT MISMATCH ' + str(set(outs))}", flush=True)
                    out.write_text(json.dumps(data, indent=1))
    finally:
        THP.write_text(original)
    data['finished'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    out.write_text(json.dumps(data, indent=1))


if __name__ == '__main__':
    main()
