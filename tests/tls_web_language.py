#!/usr/bin/env python3
"""TLS 1.3 cipher suites, groups and HelloRetryRequest against OpenSSL, then live sites.

OpenSSL s_server is restricted to AES-128-GCM, to P-256 (a HelloRetryRequest
naming P-256), to P-256 with a stateless cookie, and to a group the client does
not offer (which must fail cleanly). Each case checks the negotiated suite and
group the client reports. Live sites then use the system trust store; their
results are printed, and with --require-live every one must answer.

  python3 tests/tls_web_language.py [--require-live]
"""
import importlib.util
import os
from pathlib import Path
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


def certificates(root):
    spec = importlib.util.spec_from_file_location('tls_language', ROOT / 'tests' / 'tls_language.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.certificates(root)


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


def client(binary, host, port, trust):
    r = subprocess.run(RUNNER + [str(binary), host, str(port), trust], capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout.strip().splitlines(), r.stderr.strip()


def main():
    require_live = '--require-live' in sys.argv
    with tempfile.TemporaryDirectory(prefix='neo-tls-web-') as tmp:
        root = certificates(Path(tmp)); binary = root / 'tls-web'
        r = subprocess.run(['python3', '-m', 'neoc', 'build', 'tests/fixtures/language_tls_web.neo', '-o', str(binary)],
                           cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout[-3000:], r.stderr[-2000:])
        cases = [('ChaCha20-Poly1305, X25519', [], 'suite=4867 group=29'),
                 ('AES-128-GCM only', ['-ciphersuites', 'TLS_AES_128_GCM_SHA256'], 'suite=4865 group=29'),
                 ('P-256 only: HelloRetryRequest', ['-groups', 'P-256'], 'suite=4867 group=23'),
                 ('P-256 and AES-128-GCM', ['-groups', 'P-256', '-ciphersuites', 'TLS_AES_128_GCM_SHA256'], 'suite=4865 group=23'),
                 ('stateless cookie, X25519', ['-stateless'], 'suite=4867 group=29'),
                 ('stateless cookie, P-256', ['-stateless', '-groups', 'P-256'], 'suite=4867 group=23')]
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
        failures = []
        for site in SITES:
            code, lines, err = client(binary, site, 443, 'system')
            line = lines[-1] if lines else err[-160:]
            ok = code == 0 and 'HTTP/1.1' in line and 'suite=' in line
            if not ok:
                failures.append(site)
            print(f'{"LIVE" if ok else "FAIL"} {site}: {line} ({lines[0] if lines else ""})', flush=True)
        print(f'live sites: {len(SITES) - len(failures)}/{len(SITES)} answered', flush=True)
        assert not (require_live and failures), failures


if __name__ == '__main__':
    main()
