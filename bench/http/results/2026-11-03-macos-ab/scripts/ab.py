#!/usr/bin/env python3
"""Quick interleaved A/B: NAME=BINARY[:ENV=V,...] servers, chosen scenarios, N rounds.

Reuses bench/http/compare.py's sampler, validation and wrk parsing."""
import argparse, json, statistics, sys, types, random, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'bench/http'))
import compare as C

p = argparse.ArgumentParser()
p.add_argument('servers', nargs='+')
p.add_argument('--scenarios', nargs='+', default=['hello-64'])
p.add_argument('--rounds', type=int, default=2)
p.add_argument('--duration', default='5s'); p.add_argument('--warmup', default='1s')
p.add_argument('--out', type=Path)
p.add_argument('--max-load', type=float, default=3.0)
a = p.parse_args()
servers = []
for spec in a.servers:
    name, rest = spec.split('=', 1)
    binary, _, envs = rest.partition(':')
    env = dict(kv.split('=', 1) for kv in envs.split(',') if kv)
    servers.append((name, Path(binary), env))
args = types.SimpleNamespace(duration=a.duration, warmup=a.warmup, repeats=1, threads=4)
refs = {'1000': C.checksum(1000), '10000': C.checksum(10000), 'nbody': C.nbody_reference()}
sampler = C.Sampler()
directory = Path(a.out or '/tmp/ab'); directory.mkdir(parents=True, exist_ok=True)
scen = {s[0]: s for s in C.SCENARIOS}
rows = {}
rng = random.Random(1)
for rnd in range(a.rounds):
    for sname in a.scenarios:
        order = list(servers); rng.shuffle(order)
        for name, binary, env in order:
            cmd = None
            if name.lower().startswith('bun'):
                cmd = lambda port: [str(binary), 'run', str(ROOT / 'bench/bun/server.ts'), str(port)]
            load = C.wait_load(a.max_load, 100)
            r = C.measure((name, binary), scen[sname], args, sampler, refs, directory, command_override=cmd, env_override=env, tag=f'-r{rnd}')
            run = r['runs'][0]
            rows.setdefault((sname, name), []).append(r)
            print(f"r{rnd} {sname:24s} {name:10s} {run['rps']:>10,.0f} req/s  CPU {run['cpu_us_per_request']:7.2f} us/req  p50 {run['wrk_reported_p50_us']:>8.0f}  p99 {run['wrk_reported_p99_us']:>8.0f}  cores {run['cpu_s']/run['wall_s']:.2f} procs {run['process_count']} err {run['errors']}/{run['non2xx']}  load {load[0]:.2f}", flush=True)
            time.sleep(.3)
print()
for (sname, name), rs in rows.items():
    runs = [r['runs'][0] for r in rs]
    print(f"{sname:24s} {name:10s} median {statistics.median(x['rps'] for x in runs):>10,.0f} req/s  CPU {sum(x['cpu_s'] for x in runs)*1e6/sum(x['requests'] for x in runs):7.2f} us/req  p99 med {statistics.median(x['wrk_reported_p99_us'] for x in runs):>8.0f}  errors {sum(x['errors'] for x in runs)}")
