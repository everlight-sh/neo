#!/usr/bin/env python3
"""ab.py ROUNDS CPUS THREADS 'label=cmd args' ... : interleaved median wall/user/sys (ms)"""
import os, resource, statistics, subprocess, sys, time
rounds, cpus, threads = int(sys.argv[1]), sys.argv[2], sys.argv[3]
variants = [a.split('=', 1) for a in sys.argv[4:]]
env = {**os.environ, 'AXON_THREADS': threads, 'ZIG_THREADS': threads}
res = {l: [] for l, _ in variants}; outs = {l: set() for l, _ in variants}
for r in range(rounds + 1):
    order = variants if r % 2 == 0 else variants[::-1]
    for label, cmd in order:
        b = resource.getrusage(resource.RUSAGE_CHILDREN); t = time.perf_counter()
        p = subprocess.run(['taskset', '-c', cpus, *cmd.split()], capture_output=True, text=True, env=env)
        w = time.perf_counter() - t; a = resource.getrusage(resource.RUSAGE_CHILDREN)
        assert p.returncode == 0, (cmd, p.stderr)
        outs[label].add(p.stdout.strip())
        if r: res[label].append((w * 1000, (a.ru_utime - b.ru_utime) * 1000, (a.ru_stime - b.ru_stime) * 1000))
for label, rs in res.items():
    m = lambda k: statistics.median(x[k] for x in rs)
    print(f"{label:14s} wall {m(0):8.1f}  (min {min(x[0] for x in rs):8.1f} max {max(x[0] for x in rs):8.1f})  user {m(1):7.1f} sys {m(2):6.1f}  out {sorted(outs[label])}")
