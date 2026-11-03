#!/usr/bin/env python3
"""TLS 1.3 session resumption (PSK tickets) against OpenSSL and Go.

tests/fixtures/language_tls_resume.neo chains connections, each offering the
ticket of an earlier one: a full handshake that receives a ticket, a resumed
one (no Certificate: the client reports resumed=1, and OpenSSL's -www page
says Reused), a tampered ticket and an expired one (both fall back to a full
handshake), a ticket offered to another host name (not offered) and to the
same name spelled differently (resumed), and a wrong PSK, whose binder the
server must reject. OpenSSL variants: no tickets, three tickets per
connection, a HelloRetryRequest for P-256 (the binder is recomputed over the
new transcript), a stateless cookie, and AES-128-GCM. Go's net/http then runs
the same chain, and an HttpClient resumes on every reconnect until
http_client_close forgets its ticket.

  python3 tests/tls_resume_language.py
"""
import importlib.util
import os
from pathlib import Path
import shlex
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = shlex.split(os.environ.get('NEO_RUNNER', ''))


def tls_language():
    spec = importlib.util.spec_from_file_location('tls_language', ROOT / 'tests' / 'tls_language.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port


def openssl(root, options):
    port = free_port()
    proc = subprocess.Popen(['openssl', 's_server', '-accept', str(port), '-cert', str(root / 'leaf.pem'), '-key', str(root / 'leaf.key'),
                             '-tls1_3', '-www', '-quiet', *options], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for _ in range(200):
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.2).close(); return proc, port
        except OSError:
            time.sleep(0.02)
    proc.kill(); raise RuntimeError('openssl s_server did not start: ' + proc.stderr.read().decode(errors='replace'))


def fixture(binary, port, ca, mode, path):
    r = subprocess.run(RUNNER + [str(binary), str(port), str(ca), mode, path], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, (mode, r.returncode, r.stdout[-3000:], r.stderr[-3000:])
    return r.stdout.strip().splitlines()


def chain(binary, port, ca, path):
    hops = {}
    for line in fixture(binary, port, ca, 'tls', path):
        label, _, rest = line.partition(' ')
        if rest.startswith('rejected:'):
            hops[label] = {'rejected': rest}
        else:
            fields = rest.split(' ')
            hops[label] = {**dict(f.split('=', 1) for f in fields[:5]), 'line': rest}
    assert len(hops) == 7, hops
    return hops


def check_chain(name, hops, server_view, suite=None, group=None):
    view = (lambda expected: expected) if server_view else (lambda expected: '-')
    expected = {'full': ('0', 'new'), 'resumed': ('1', 'reused'), 'tampered': ('0', 'new'), 'expired': ('0', 'new'),
                'other-host': ('0', 'new'), 'same-host': ('1', 'reused')}
    for label, (resumed, seen) in expected.items():
        hop = hops[label]
        assert 'rejected' not in hop, (name, label, hop)
        assert hop['resumed'] == resumed and hop['server'] == view(seen) and hop['ticket'] == '1', (name, label, hop)
        assert ' 200 ' in hop['line'], (name, label, hop)
        assert suite is None or hop['suite'] == str(suite), (name, label, hop)
        assert group is None or hop['group'] == str(group), (name, label, hop)
    assert 'rejected' in hops['wrong-psk'], (name, hops['wrong-psk'])
    print(f'PASS {name}: resumed {hops["resumed"]["line"]}; tampered, expired fall back; wrong PSK {hops["wrong-psk"]["rejected"][:60]}', flush=True)


def check_client(name, lines):
    expected = [(1, 0), (2, 1), (3, 2), (4, 3), (5, 3), (6, 4)]
    assert len(lines) == len(expected), (name, lines)
    for line, (connections, resumptions) in zip(lines, expected):
        assert line == f'200 connections={connections} resumptions={resumptions}', (name, lines)
    print(f'PASS {name}: resumptions {", ".join(l.split("resumptions=")[1] for l in lines)} (the 5th request follows http_client_close)', flush=True)


def main():
    with tempfile.TemporaryDirectory(prefix='neo-tls-resume-') as tmp:
        root = tls_language().certificates(Path(tmp)); binary = root / 'tls-resume'; ca = root / 'ca.der'
        r = subprocess.run(['python3', '-m', 'neoc', 'build', 'tests/fixtures/language_tls_resume.neo', '-o', str(binary)],
                           cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout[-3000:], r.stderr[-2000:])
        cases = [('OpenSSL, default tickets', [], None, 29),
                 ('OpenSSL, three tickets per connection', ['-num_tickets', '3'], None, 29),
                 ('OpenSSL, P-256 only: HelloRetryRequest with a PSK', ['-groups', 'P-256'], None, 23),
                 ('OpenSSL, stateless cookie', ['-stateless'], None, 29),
                 ('OpenSSL, AES-128-GCM', ['-ciphersuites', 'TLS_AES_128_GCM_SHA256'], 4865, 29),
                 ('OpenSSL, ChaCha20-Poly1305', ['-ciphersuites', 'TLS_CHACHA20_POLY1305_SHA256'], 4867, 29)]
        for name, options, suite, group in cases:
            proc, port = openssl(root, options)
            try:
                hops = chain(binary, port, ca, '/')
            finally:
                proc.terminate(); proc.wait()
            check_chain(name, hops, True, suite, group)
        proc, port = openssl(root, ['-num_tickets', '0'])
        try:
            hops = chain(binary, port, ca, '/')
        finally:
            proc.terminate(); proc.wait()
        assert hops['full']['ticket'] == '0' and hops['resumed']['resumed'] == '0' and hops['resumed']['server'] == 'new', hops
        print(f'PASS OpenSSL without tickets: every connection is a full handshake: {hops["resumed"]["line"]}', flush=True)
        proc, port = openssl(root, [])
        try:
            check_client('HttpClient against OpenSSL', fixture(binary, port, ca, 'client', '/'))
        finally:
            proc.terminate(); proc.wait()
        server = root / 'http2-server'
        r = subprocess.run(['go', 'build', '-trimpath', '-o', str(server), 'tests/http2_server.go'], cwd=ROOT,
                           env={**os.environ, 'GOWORK': 'off', 'CGO_ENABLED': '0'}, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-2000:]
        for options, label in (['-h1'], 'HTTP/1.1'), ([], 'h2'):
            proc = subprocess.Popen([str(server), '-cert', str(root / 'leaf.pem'), '-key', str(root / 'leaf.key'), *options],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                port = int(proc.stdout.readline())
                if label == 'HTTP/1.1':
                    check_chain('Go net/http', chain(binary, port, ca, '/hello'), False)
                check_client(f'HttpClient against Go net/http ({label})', fixture(binary, port, ca, 'client', '/hello'))
            finally:
                proc.terminate(); proc.wait()


if __name__ == '__main__':
    main()
