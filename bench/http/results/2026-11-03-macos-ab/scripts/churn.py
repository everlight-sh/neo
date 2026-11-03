#!/usr/bin/env python3
"""Connection churn: wrk with Connection: close; server process-tree CPU per request.
usage: churn.py ROUNDS NAME=BIN[:ENV=V,...] ..."""
import os, re, signal, socket, subprocess, sys, time, random, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'bench/http')); import compare as C
rounds = int(sys.argv[1]); servers = []
for spec in sys.argv[2:]:
    name, rest = spec.split('=', 1); binary, _, envs = rest.partition(':')
    servers.append((name, binary, dict(kv.split('=', 1) for kv in envs.split(',') if kv)))
sampler = C.Sampler(); rows = {}
for r in range(rounds):
    order = list(servers); random.shuffle(order)
    for name, binary, extra in order:
        with socket.socket() as s: s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if k not in ('NEO_THREADS', 'TOKIO_WORKER_THREADS')}; env.update(extra)
        p = subprocess.Popen([binary, str(port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            for _ in range(300):
                try: socket.create_connection(('127.0.0.1', port), timeout=.1).close(); break
                except OSError: time.sleep(.01)
            time.sleep(.3)
            before = sampler.snapshot(p.pid)
            out = subprocess.run(['wrk', '-t2', '-c16', '-d3s', '--latency', '-H', 'Connection: close', f'http://127.0.0.1:{port}/'], capture_output=True, text=True).stdout
            after = sampler.snapshot(p.pid)
            n = int(re.search(r'(\d+) requests in', out)[1]); rps = float(re.search(r'Requests/sec:\s+([\d.]+)', out)[1])
            errs = re.search(r'Socket errors: (.*)', out); p99 = re.search(r'99%\s+(\S+)', out)[1]
            cpu = (after['cpu_s'] - before['cpu_s']) * 1e6 / n
            rows.setdefault(name, []).append((rps, cpu))
            print(f'r{r} {name:8s} {rps:9,.0f} conn/s  server CPU {cpu:6.1f} us/conn  p99 {p99:>8s}  {errs[1] if errs else ""}', flush=True)
        finally:
            os.killpg(p.pid, signal.SIGTERM); p.wait()
        while int(subprocess.run('netstat -an -p tcp | grep -c TIME_WAIT', shell=True, capture_output=True, text=True).stdout) > 2000: time.sleep(2)
for name, xs in rows.items():
    print(f'{name:8s} median {statistics.median(x[0] for x in xs):9,.0f} conn/s  CPU {statistics.median(x[1] for x in xs):6.1f} us/conn')
