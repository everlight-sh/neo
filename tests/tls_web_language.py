#!/usr/bin/env python3
"""TLS 1.3 cipher suites, groups and HelloRetryRequest against OpenSSL, then live sites.

OpenSSL s_server is restricted to AES-128-GCM, to P-256 (a HelloRetryRequest
naming P-256), to P-256 with a stateless cookie, and to a group the client does
not offer (which must fail cleanly). Each case checks the negotiated suite and
group the client reports. OpenSSL then sends KeyUpdate (requesting one back)
before its answer, with each suite. Live sites then use the system trust store, first
over std:tls directly (HTTP/1.1), then with std:https_client's HttpClient,
which offers h2 with ALPN and speaks HTTP/2 to the sites that choose it; their
results are printed, and with --require-live every one must answer both ways.

  python3 tests/tls_web_language.py [--require-live]
"""
import importlib.util
import os
from pathlib import Path
import select
import shlex
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = shlex.split(os.environ.get('NEO_RUNNER', ''))
SITES = ['example.com', 'www.google.com', 'www.wikipedia.org', 'en.wikipedia.org', 'github.com', 'www.cloudflare.com',
         'www.mozilla.org', 'letsencrypt.org', 'news.ycombinator.com', 'www.python.org', 'go.dev', 'www.rust-lang.org',
         'www.bbc.co.uk', 'www.lemonde.fr', 'stackoverflow.com', 'www.apple.com', 'www.microsoft.com', 'lightpanda.io']


def tls_language():
    spec = importlib.util.spec_from_file_location('tls_language', ROOT / 'tests' / 'tls_language.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def certificates(root):
    return tls_language().certificates(root)


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port


def server(root, options):
    port = free_port()
    proc = subprocess.Popen(['openssl', 's_server', '-accept', str(port), '-cert', str(root / 'leaf.pem'), '-key', str(root / 'leaf.key'),
                             '-tls1_3', '-www', '-quiet', *options], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for _ in range(200):
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.2).close(); return proc, port
        except OSError:
            time.sleep(0.02)
    proc.kill(); raise RuntimeError('openssl s_server did not start: ' + proc.stderr.read().decode(errors='replace'))


def key_update(binary, root, suite):
    """OpenSSL s_server sends KeyUpdate (its K command, requesting one back), then two lines (the client reads twice)."""
    port = free_port()
    proc = subprocess.Popen(['openssl', 's_server', '-accept', str(port), '-cert', str(root / 'leaf.pem'), '-key', str(root / 'leaf.key'),
                             '-tls1_3', '-ciphersuites', suite, '-naccept', '1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        time.sleep(0.5)
        neo = subprocess.Popen(RUNNER + [str(binary), '127.0.0.1', str(port), str(root / 'ca.der')], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        seen, end = b'', time.time() + 6
        while b'GET / ' not in seen and time.time() < end:  # s_server echoes the request it receives
            if select.select([proc.stdout], [], [], 0.2)[0]:
                seen += os.read(proc.stdout.fileno(), 65536)
        try:
            for command in (b'K\n', b'HTTP/1.0 200 after KeyUpdate\r\n', b'second line\r\n'):  # one stdin read and record each
                proc.stdin.write(command); proc.stdin.flush(); time.sleep(0.3)
        except BrokenPipeError:
            pass  # the server ended the connection: the client reports why
        out, err = neo.communicate(timeout=30)
        return neo.returncode, out.strip().splitlines(), err.strip()
    finally:
        proc.kill(); proc.wait()


def client(binary, host, port, trust):
    r = subprocess.run(RUNNER + [str(binary), host, str(port), trust], capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout.strip().splitlines(), r.stderr.strip()


def main():
    require_live = '--require-live' in sys.argv
    with tempfile.TemporaryDirectory(prefix='neo-tls-web-') as tmp:
        root = certificates(Path(tmp)); binary = root / 'tls-web'; http2 = root / 'http2'
        for source, target in (('tests/fixtures/language_tls_web.neo', binary), ('tests/fixtures/language_http2.neo', http2)):
            r = subprocess.run(['python3', '-m', 'neoc', 'build', source, '-o', str(target)], cwd=ROOT, capture_output=True, text=True)
            assert r.returncode == 0, (source, r.stdout[-3000:], r.stderr[-2000:])
        # OpenSSL follows the client's order: AES-128-GCM first with the CPU's AES instructions, else ChaCha20-Poly1305.
        first = tls_language().default_suite(); name = 'AES-128-GCM' if first == 4865 else 'ChaCha20-Poly1305'
        cases = [(f'{name}, X25519', [], f'suite={first} group=29'),
                 ('AES-128-GCM only', ['-ciphersuites', 'TLS_AES_128_GCM_SHA256'], 'suite=4865 group=29'),
                 ('ChaCha20-Poly1305 only', ['-ciphersuites', 'TLS_CHACHA20_POLY1305_SHA256'], 'suite=4867 group=29'),
                 ('P-256 only: HelloRetryRequest', ['-groups', 'P-256'], f'suite={first} group=23'),
                 ('P-256 and AES-128-GCM', ['-groups', 'P-256', '-ciphersuites', 'TLS_AES_128_GCM_SHA256'], 'suite=4865 group=23'),
                 ('stateless cookie, X25519', ['-stateless'], f'suite={first} group=29'),
                 ('stateless cookie, P-256', ['-stateless', '-groups', 'P-256'], f'suite={first} group=23')]
        for name, options, expected in cases:
            proc, port = server(root, options)
            try:
                code, lines, err = client(binary, '127.0.0.1', port, str(root / 'ca.der'))
            finally:
                proc.terminate(); proc.wait()
            assert code == 0 and lines and lines[-1].startswith(expected) and 'HTTP/1.0 200' in lines[-1], (name, code, lines, err)
            print(f'PASS {name}: {lines[-1]}', flush=True)
        proc, port = server(root, ['-groups', 'X448'])
        try:
            code, lines, err = client(binary, '127.0.0.1', port, str(root / 'ca.der'))
        finally:
            proc.terminate(); proc.wait()
        assert code == 0 and lines and lines[-1].startswith('rejected:'), ('unsupported group', code, lines, err)
        print(f'PASS unsupported group (X448 only) fails cleanly: {lines[-1]}', flush=True)
        for suite, number in (('TLS_AES_128_GCM_SHA256', 4865), ('TLS_CHACHA20_POLY1305_SHA256', 4867)):
            code, lines, err = key_update(binary, root, suite)
            assert code == 0 and lines and lines[-1] == f'suite={number} group=29 HTTP/1.0 200 after KeyUpdate', (suite, code, lines, err)
            print(f'PASS KeyUpdate with {suite}: {lines[-1]}', flush=True)
        failures, h2 = [], 0
        for site in SITES:
            code, lines, err = client(binary, site, 443, 'system')
            line = lines[-1] if lines else err[-160:]
            ok = code == 0 and 'HTTP/1.1' in line and 'suite=' in line
            r = subprocess.run(RUNNER + [str(http2), site, '443', 'system', '-', 'GET:/'], capture_output=True, text=True, timeout=60)
            fetched = r.stdout.strip().splitlines()[0] if r.returncode == 0 and r.stdout.strip() else r.stderr.strip()[-160:]
            ok = ok and r.returncode == 0 and ' -> ' in fetched and ' -> error' not in fetched
            h2 += ' h2 ' in fetched
            if not ok:
                failures.append(site)
            print(f'{"LIVE" if ok else "FAIL"} {site}: {line} ({lines[0] if lines else ""}); HttpClient: {fetched.split(" sha256=")[0]}', flush=True)
        print(f'live sites: {len(SITES) - len(failures)}/{len(SITES)} answered, {h2} over h2', flush=True)
        assert not (require_live and failures), failures


if __name__ == '__main__':
    main()
