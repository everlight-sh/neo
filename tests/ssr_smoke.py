#!/usr/bin/env python3
"""Compare standalone Neo and production Bun/React SSR against a Python oracle."""
import argparse
import concurrent.futures
import html
import http.client
import os
from pathlib import Path
import platform
import shutil
import signal
import socket
import subprocess
import tempfile
import time

from kernel_runtime_smoke import audit

ROOT = Path(__file__).resolve().parents[1]
WORDS = ['Widget', 'Gadget', 'Gizmo', 'Doohickey', 'Sprocket', 'Flange', 'Bracket', 'Grommet']
ADJECTIVES = ['Deluxe', 'Basic', 'Pro', 'Mini', 'Ultra', 'Classic', 'Eco', 'Max']
COUNTS = (1, 2, 3, 7, 17, 50, 99, 100, 1000)


def reference(n):
    rows = []
    cents = 0
    for i in range(n):
        dollars = i * 37 % 1000
        cents += dollars * 100 + 99
        note = html.escape('Ben & Jerry\'s "Special" <limited>') if i % 5 == 0 else '-'
        rows.append(f'<tr class="{"odd" if i % 2 else "even"}"><td>{i}</td><td>{WORDS[i % 8]} {ADJECTIVES[i * 7 % 8]}</td><td>${dollars}.99</td><td>{i * 13 % 50}</td><td>{note}</td></tr>')
    return ('<!DOCTYPE html><html lang="en"><head><title>Catalog</title></head><body><header><h1>Catalog</h1>'
            f'<p>{n} items</p></header><main><table><thead><tr><th>ID</th><th>Name</th><th>Price</th><th>Stock</th><th>Note</th></tr></thead>'
            '<tbody>' + ''.join(rows) + f'</tbody></table></main><footer>Total: ${cents // 100}.{cents % 100:02d}</footer></body></html>').encode()


def validate(port, _refs=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
    try:
        for n in COUNTS:
            c.request('GET', f'/page/{n}')
            r = c.getresponse(); body = r.read()
            assert r.status == 200 and body == reference(n), (port, n, r.status, body[:200])
            assert r.getheader('Content-Type').lower() == 'text/html; charset=utf-8'
            assert len(body) == int(r.getheader('Content-Length'))
            assert b'<script' not in body
        for path in ('/', '/?view=default'):
            c.request('GET', path); r = c.getresponse()
            assert r.status == 200 and r.read() == reference(3)
        c.request('GET', '/page/50?view=table'); r = c.getresponse()
        assert r.status == 200 and r.read() == reference(50)
        for path in ('/page/0', '/page/1001', '/page/x', '/page/-1', '/page/1x', '/page/1/', '/page/1234567890123'):
            c.request('GET', path); r = c.getresponse()
            assert (r.status, r.read()) == (400, b'usage: /page/N, 1 <= N <= 1000'), path
        c.request('GET', '/missing'); r = c.getresponse()
        assert (r.status, r.read()) == (404, b'Not Found')
        c.request('POST', '/', body='test'); r = c.getresponse()
        assert (r.status, r.read()) == (405, b'')
    finally: c.close()


def verify(command, env, *, quiet=False):
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]
    with tempfile.TemporaryFile() as log:
        p = subprocess.Popen([*command, str(port)], env=env, start_new_session=True, stdout=log, stderr=log)
        try:
            for _ in range(100):
                assert p.poll() is None, 'Server exited during startup'
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.1): pass
                    break
                except OSError: time.sleep(.05)
            else: raise TimeoutError('Server did not start')
            validate(port)
            def request(i):
                c = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
                try:
                    n = 3 if i % 2 else 50
                    c.request('GET', f'/page/{n}'); r = c.getresponse()
                    assert r.status == 200 and r.read() == reference(n)
                finally: c.close()
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
                list(pool.map(request, range(100)))
            with socket.create_connection(('127.0.0.1', port), timeout=10) as s:
                counts = [3, 50] * 64 + [1000]
                s.sendall(b''.join(f'GET /page/{n} HTTP/1.1\r\nHost: localhost\r\n'.encode() +
                                  (b'Connection: close\r\n' if i + 1 == len(counts) else b'') + b'\r\n'
                                  for i, n in enumerate(counts)))
                stream = s.makefile('rb')
                for n in counts:
                    assert stream.readline().startswith(b'HTTP/1.1 200')
                    headers = {}
                    while (line := stream.readline()) != b'\r\n':
                        assert line
                        k, v = line.split(b':', 1); headers[k.lower()] = v.strip()
                    assert stream.read(int(headers[b'content-length'])) == reference(n)
                assert stream.read(1) == b''
                stream.close()
            if not quiet:
                print('SSR PASS: exact HTML for 1..1000 sampled rows, escaping, routing, keep-alive, 100 concurrent requests, 129 ordered pipelined pages, close and large response.', flush=True)
        finally:
            try: os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            try: p.wait(timeout=3)
            except subprocess.TimeoutExpired: os.killpg(p.pid, signal.SIGKILL); p.wait()
            log.seek(0); print(log.read().decode(), end='', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--neo-only', action='store_true')
    parser.add_argument('--empty-root', action='store_true')
    args = parser.parse_args()
    binary = args.binary.resolve(); audit(binary)
    env = dict(os.environ, NODE_ENV='production')
    if args.empty_root:
        assert platform.system() == 'Linux' and os.geteuid() == 0
        with tempfile.TemporaryDirectory(prefix='neo-ssr-root-') as tmp:
            root = Path(tmp); shutil.copy2(binary, root/'ssr')
            assert [p.name for p in root.iterdir()] == ['ssr']
            verify(['chroot', str(root), '/ssr'], dict(env, NEO_THREADS='4'))
        print('SSR PASS from an empty Linux root containing only the executable.', flush=True)
    else:
        for workers in ('1', '4'):
            verify([str(binary)], dict(env, NEO_THREADS=workers))
        if not args.neo_only:
            verify([shutil.which('bun'), 'run', str(ROOT/'examples/ssr-react/server.tsx')], env)


if __name__ == '__main__': main()
