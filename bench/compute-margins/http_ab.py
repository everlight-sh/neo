#!/usr/bin/env python3
"""Neo HTTP example before and after this change: /smooth/1000 and
/smooth/10000, whose handler runs the stencil comprehension and builds its
response with `cat` (both compile differently now), and GET / (a constant
response, unchanged code) as a control.

Method of bench/headline/run_headline.py: one worker (NEO_THREADS=1), the
server confined to SERVER_CPUS (default 0), wrk -t2 -c64 on CLIENT_CPUS
(default 2,3: the other physical core of a 4-vCPU box), a fresh server per
run, 2 s warm-up, 10 s measured, order alternating every round. Before the
rounds, each path must give byte-identical responses from both binaries.

usage: http_ab.py OUT.json ROUNDS BEFORE_BINARY AFTER_BINARY
"""
import json, os, re, socket, statistics, subprocess, sys, time
from pathlib import Path

PATHS = ['/', '/smooth/1000', '/smooth/10000']
SERVER_CPUS, CLIENT_CPUS = os.environ.get('SERVER_CPUS', '0'), os.environ.get('CLIENT_CPUS', '2,3')
PORT = 18090


def start(binary):
    p = subprocess.Popen(['taskset', '-c', SERVER_CPUS, binary, str(PORT)], env={**os.environ, 'NEO_THREADS': '1'},
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(200):
        try:
            socket.create_connection(('127.0.0.1', PORT), timeout=0.1).close(); return p
        except OSError: time.sleep(0.02)
    p.kill(); raise RuntimeError(f'{binary} did not listen')


def stop(p):
    p.terminate()
    try: p.wait(5)
    except subprocess.TimeoutExpired: p.kill(); p.wait()


def fetch(path):
    s = socket.create_connection(('127.0.0.1', PORT), timeout=5)
    s.sendall(f'GET {path} HTTP/1.1\r\nHost: x\r\n\r\n'.encode())
    data = b''
    while b'\r\n\r\n' not in data: data += s.recv(65536)
    head, body = data.split(b'\r\n\r\n', 1)
    length = int(re.search(rb'Content-Length: (\d+)', head).group(1))
    while len(body) < length: body += s.recv(65536)
    s.close(); return head + b'\r\n\r\n' + body


def wrk(path, seconds):
    out = subprocess.run(['taskset', '-c', CLIENT_CPUS, 'wrk', '-t2', '-c64', f'-d{seconds}s', f'http://127.0.0.1:{PORT}{path}'],
                         capture_output=True, text=True, check=True).stdout
    assert 'Non-2xx' not in out and 'Socket errors' not in out, out
    return float(re.search(r'Requests/sec:\s+([\d.]+)', out).group(1))


def main():
    out, rounds, before, after = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
    variants = {'Neo before': before, 'Neo after': after}
    responses = {}
    for name, binary in variants.items():
        p = start(binary)
        try: responses[name] = {path: fetch(path) for path in PATHS}
        finally: stop(p)
    for path in PATHS:
        assert responses['Neo before'][path] == responses['Neo after'][path], path
        assert responses['Neo after'][path].startswith(b'HTTP/1.1 200'), path
    data = {'rounds': rounds, 'server_cpus': SERVER_CPUS, 'client_cpus': CLIENT_CPUS, 'results': {}}
    for path in PATHS:
        runs = {name: [] for name in variants}
        for r in range(rounds):
            for name in (list(variants) if r % 2 == 0 else list(variants)[::-1]):
                p = start(variants[name])
                try:
                    wrk(path, 2); runs[name].append(wrk(path, 10))
                finally: stop(p)
        data['results'][path] = runs
        print(f'{path:16s} ' + '  '.join(f'{n} {statistics.median(v):10.0f} req/s ({min(v):.0f}-{max(v):.0f})' for n, v in runs.items()), flush=True)
        out.write_text(json.dumps(data, indent=1))


if __name__ == '__main__':
    main()
