#!/usr/bin/env python3
"""Fetch benchmark: one HTTP or HTTPS GET at a time against a local server,
from Neo, Bun (fetch), Go (net/http) and Rust (reqwest).

    python3 bench/fetch/run.py [--rounds N] [--oneshot N] [--server-cpu N] [--key ec|rsa]
                               [--schemes http,https] [--clients TEXT,...]

Builds fetch.neo with ./neo, the Go programs with go and the Rust client with
cargo, makes a throwaway root and a localhost certificate with openssl, and
starts the target server (go/server), which serves HTTP and HTTPS (TLS 1.3,
HTTP/1.1). Every client runs on CPU 0, and so does the server unless
--server-cpu moves it: on a virtual machine a server on another CPU adds the
cost of waking that CPU twice per request, which varies a lot.

Each client makes COUNT sequential requests per round, on a new connection
each time or over one kept-alive connection. Neo's new-connection plain HTTP
client is http_request, the one-call API; its other modes use HttpClient from
std:https_client. "Neo, resumed" (HTTPS only) opens a new connection per request
from one HttpClient, so every TLS handshake after the first resumes the session
from a ticket, as the Rust client's does; "Neo" makes a new client, and so a
full handshake, for each request. --clients keeps the clients whose names
contain one of the given texts. Every response
must be a 200 with the whole body, and the server's connection count shows
whether a client reused its connection. A last table times whole processes
that make one request each: start, connect, read the response, exit. Results
go to bench/fetch/results/<timestamp>/ as JSON and Markdown.
"""
import argparse
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# path, body bytes, requests per round
SIZES = [('/hello', 13, 1000), ('/64k', 64 << 10, 1000), ('/1m', 1 << 20, 200)]


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port


def conns(port):
    """Connections the server has accepted before this call's own."""
    return int(urllib.request.urlopen(f'http://127.0.0.1:{port}/conns', timeout=5).read()) - 1


def certificates(out, key):
    """A root (ca.pem, ca.der) and a certificate for localhost and 127.0.0.1 (leaf.pem, leaf.key)."""
    def openssl(*argv): subprocess.run(['openssl', *map(str, argv)], cwd=out, check=True, capture_output=True)
    new = ['-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256'] if key == 'ec' else ['-newkey', 'rsa:2048']
    openssl('req', '-new', '-x509', *new, '-nodes', '-keyout', 'ca.key', '-out', 'ca.pem', '-subj', '/CN=Fetch Bench Root', '-days', '2',
            '-sha256', '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:0', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    openssl('req', '-new', *new, '-nodes', '-keyout', 'leaf.key', '-out', 'leaf.csr', '-subj', '/CN=localhost')
    (out / 'leaf.ext').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\n'
                                  'subjectAltName=DNS:localhost,IP:127.0.0.1\n')
    openssl('x509', '-req', '-in', 'leaf.csr', '-CA', 'ca.pem', '-CAkey', 'ca.key', '-CAcreateserial', '-out', 'leaf.pem', '-days', '1',
            '-sha256', '-extfile', 'leaf.ext')
    openssl('x509', '-in', 'ca.pem', '-outform', 'DER', '-out', 'ca.der')


def build(out):
    neo = subprocess.Popen([str(ROOT / 'neo'), 'build', str(HERE / 'fetch.neo'), '-o', str(out / 'fetch_neo')], cwd=ROOT,
                           stdout=subprocess.DEVNULL)
    rust = subprocess.Popen(['cargo', 'build', '--release', '--quiet'], cwd=HERE / 'rust')
    for name in ('client', 'server'):
        subprocess.run(['go', 'build', '-o', str(out / f'go_{name}'), f'./{name}'], cwd=HERE / 'go', check=True)
    if neo.wait() or rust.wait(): raise SystemExit('build failed')
    (out / 'rust_client').write_bytes((HERE / 'rust' / 'target' / 'release' / 'fetch-client').read_bytes())
    (out / 'rust_client').chmod(0o755)


NEW, KEEP, RESUME = 0, 1, 2  # a connection per request, keep-alive, a connection per request resuming TLS


def clients(out):
    """name -> (argv, mode, root certificate file)"""
    neo, bun, go, rust = [str(out / 'fetch_neo')], ['bun', str(HERE / 'fetch.ts')], [str(out / 'go_client')], [str(out / 'rust_client')]
    return {'Neo': (neo, NEW, 'ca.der'), 'Neo, keep-alive': (neo, KEEP, 'ca.der'), 'Neo, resumed': (neo, RESUME, 'ca.der'),
            'Bun fetch': (bun, NEW, 'ca.pem'), 'Bun fetch, keep-alive': (bun, KEEP, 'ca.pem'),
            'Go net/http': (go, NEW, 'ca.pem'), 'Go net/http, keep-alive': (go, KEEP, 'ca.pem'),
            'Rust reqwest': (rust, NEW, 'ca.pem'), 'Rust reqwest, keep-alive': (rust, KEEP, 'ca.pem')}


def command(argv, mode, port, path, count, size, ca):
    return ['taskset', '-c', '0', *argv, str(port), path, str(count), str(size), str(mode)] + ([str(ca)] if ca else [])


def run(cmd, mode, plain_port, count, size):
    """(nanoseconds for all requests, connections opened, each request's nanoseconds)"""
    before = conns(plain_port)
    lines = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, check=True).stdout.splitlines()
    opened = conns(plain_port) - before - 1
    ns, good = map(int, lines[0].split())
    if good != count: raise SystemExit(f'{" ".join(cmd)}: {good} of {count} responses were 200 with {size} bytes')
    if mode != KEEP and opened != count: raise SystemExit(f'{" ".join(cmd)}: {opened} connections for {count} requests')
    return ns, opened, [int(word) for word in lines[1].split()]


def percentile(values, p): return values[max(0, math.ceil(p * len(values)) - 1)]


def version(cmd):
    try: return subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[0]
    except (OSError, IndexError): return 'unknown'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rounds', type=int, default=5); ap.add_argument('--oneshot', type=int, default=100)
    ap.add_argument('--server-cpu', type=int, default=0); ap.add_argument('--key', choices=['ec', 'rsa'], default='ec')
    ap.add_argument('--schemes', default='http,https'); ap.add_argument('--clients', default='')
    args = ap.parse_args()
    schemes = [s for s in ('http', 'https') if s in args.schemes.split(',')]
    wanted = [text for text in args.clients.split(',') if text]
    out = HERE / 'results' / time.strftime('%Y-%m-%d-%H%M%S'); out.mkdir(parents=True)
    certificates(out, args.key); build(out)
    port, tls_port = free_port(), free_port()
    server = subprocess.Popen(['taskset', '-c', str(args.server_cpu), str(out / 'go_server'), str(port), str(tls_port),
                               str(out / 'leaf.pem'), str(out / 'leaf.key')])
    try:
        for _ in range(100):
            try: conns(port); socket.create_connection(('127.0.0.1', tls_port), timeout=1).close(); break
            except OSError: time.sleep(0.05)
        table = {name: client for name, client in clients(out).items() if not wanted or any(text in name for text in wanted)}
        data = {'server_cpu': args.server_cpu, 'key': args.key, 'rounds': args.rounds, 'http': {}, 'https': {}, 'oneshot': {}}
        for scheme in schemes:
            for path, size, count in SIZES:
                here = {name: client for name, client in table.items() if client[1] != RESUME or scheme == 'https'}
                rows = {name: {'mean': [], 'times': []} for name in here}; opened = {}
                for r in range(args.rounds + 1):  # round 0 warms up
                    for name, (argv, mode, ca) in here.items():
                        cmd = command(argv, mode, tls_port if scheme == 'https' else port, path, count, size,
                                      out / ca if scheme == 'https' else None)
                        ns, opened[name], times = run(cmd, mode, port, count, size)
                        if r: rows[name]['mean'].append(ns / count); rows[name]['times'] += times
                result = {}
                for name, row in rows.items():
                    times = sorted(row['times'])
                    result[name] = {'mean_ns': statistics.median(row['mean']), 'round_means_ns': row['mean'], 'p50_ns': percentile(times, 0.5),
                                    'p90_ns': percentile(times, 0.9), 'p99_ns': percentile(times, 0.99), 'max_ns': times[-1],
                                    'connections': opened[name]}
                data[scheme][path] = {'bytes': size, 'requests': count, 'clients': result}
                print(scheme, path, {name: round(c['p50_ns'] / 1000, 1) for name, c in result.items()}, flush=True)
        for name, (argv, mode, ca) in table.items():
            if mode != NEW: continue  # one request per process can neither keep nor resume a connection
            for scheme in schemes:
                walls = []
                for k in range(args.oneshot + 2):
                    cmd = command(argv, mode, tls_port if scheme == 'https' else port, '/hello', 1, 13, out / ca if scheme == 'https' else None)
                    start = time.perf_counter(); subprocess.run(cmd, capture_output=True, check=True)
                    if k >= 2: walls.append(time.perf_counter() - start)
                data['oneshot'].setdefault(name, {})[scheme] = sorted(walls)
            print('one request per process', name, {s: round(statistics.median(w) * 1000, 2) for s, w in data['oneshot'][name].items()}, flush=True)
    finally: server.kill()
    cpu = next((line.split(':', 1)[1].strip() for line in open('/proc/cpuinfo') if line.startswith('model name')), platform.machine())
    machine = data['machine'] = {'cpu': cpu, 'cores': os.cpu_count(), 'kernel': platform.release(), 'bun': version(['bun', '--version']),
                                 'go': version(['go', 'version']), 'rustc': version(['rustc', '--version']), 'clang': version(['clang', '--version'])}
    (out / 'results.json').write_text(json.dumps(data, indent=1))
    key = 'ECDSA P-256' if args.key == 'ec' else 'RSA 2048'
    lines = [f'# Fetch benchmark, {time.strftime("%Y-%m-%d")}', '',
             f'{cpu}, {os.cpu_count()} vCPU, Linux {platform.release()}. Bun {machine["bun"]}, {machine["go"]}, {machine["rustc"]}, {machine["clang"]}.',
             f'Server: Go net/http on CPU {args.server_cpu}; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, {key} certificates.',
             f'Mean is the median over {args.rounds} rounds after a warm-up; percentiles are over every request of those rounds.', '']
    for scheme in ('http', 'https'):
        for path, entry in data[scheme].items():
            lines += [f'## {scheme.upper()} GET {path} ({entry["bytes"]} bytes), {entry["requests"]} sequential requests per round', '',
                      '| Client | mean µs | p50 µs | p99 µs | requests/s | connections |', '|---|---:|---:|---:|---:|---:|']
            for name, c in entry['clients'].items():
                lines.append(f'| {name} | {c["mean_ns"] / 1000:.1f} | {c["p50_ns"] / 1000:.1f} | {c["p99_ns"] / 1000:.1f} | '
                             f'{1e9 / c["mean_ns"]:,.0f} | {c["connections"]} |')
            lines.append('')
    if data['oneshot']:
        lines += [f'## One request per process (GET /hello), median of {args.oneshot}', '',
                  '| Client | ' + ' | '.join(f'{s.upper()} ms' for s in schemes) + ' |', '|---|' + '---:|' * len(schemes)]
        for name, walls in data['oneshot'].items():
            lines.append(f'| {name} | ' + ' | '.join(f'{statistics.median(walls[s]) * 1000:.2f}' for s in schemes) + ' |')
    (out / 'results.md').write_text('\n'.join(lines) + '\n')
    print((out / 'results.md').read_text())


if __name__ == '__main__': main()
