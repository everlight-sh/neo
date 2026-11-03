#!/usr/bin/env python3
"""Content-Length bodies that std:https_client reads straight into one buffer,
over TCP, TLS 1.3 (AES-128-GCM and ChaCha20-Poly1305) and TLS 1.2: sizes on
either side of a TLS record, a body sent in many small writes, a server that
closes mid-body, and one that sends more than it announced."""
import socket, ssl, subprocess, tempfile, threading
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from agent_codecs import RUNNER, build
from http_keepalive import read_request
from tls_language import certificates

SIZES = [1, 100, 16383, 16384, 16385, 49152, 100000, 1048576]
PATHS = [f'/n/{n}' for n in SIZES] + ['/split/300000', '/n/16384', '/short/50000', '/n/70000', '/excess/70000']


@cache
def body(size):
    return bytes((i * 31 + (i >> 8)) & 255 for i in range(size))


@cache
def fnv(size):
    h = 0xcbf29ce484222325
    for b in body(size): h = ((h ^ b) * 0x100000001b3) & 0xffffffffffffffff
    return h - (1 << 64) if h >= 1 << 63 else h


def expected(tls):
    """Each line the client prints: the excess bytes fail a TLS read; over TCP
    they stay unread on the socket after the announced body."""
    ok = lambda n, c: f'200 {n} {fnv(n)} {c}'
    return [ok(n, 1) for n in SIZES] + [ok(300000, 1), ok(16384, 1), 'error:5 1', ok(70000, 2),
                                        'error:27 2' if tls else ok(70000, 2)]


def handle(connection):
    buffered = b''
    with connection:
        while (request := read_request(connection, buffered)) is not None:
            _, path, _, buffered = request
            kind, size = path[1:].split('/'); size = int(size)
            head = b'HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n' % size
            if kind == 'n': connection.sendall(head + body(size))
            elif kind == 'excess': connection.sendall(head + body(size) + b'0123456789')
            elif kind == 'short': connection.sendall(head + body(size)[:size // 2]); return
            else:
                connection.sendall(head)
                for at in range(0, size, 997): connection.sendall(body(size)[at:at + 997])


@contextmanager
def server(context):
    """(port, accepted connections, negotiated TLS suites)"""
    listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(); listener.settimeout(0.2)
    accepted, suites, errors, stop = [], [], [], threading.Event()
    def run(connection):
        try:
            if context:
                connection = context.wrap_socket(connection, server_side=True); suites.append(connection.cipher()[0])
            handle(connection)
        except Exception as exc: errors.append(exc)
    def serve():
        while not stop.is_set():
            try: connection, _ = listener.accept()
            except TimeoutError: continue
            connection.settimeout(10); accepted.append(connection)
            threading.Thread(target=run, args=(connection,), daemon=True).start()
    thread = threading.Thread(target=serve, daemon=True); thread.start()
    try: yield listener.getsockname()[1], accepted, suites
    finally:
        stop.set(); thread.join(2); listener.close(); assert not errors, errors


def main():
    with tempfile.TemporaryDirectory(prefix='neo-large-body-') as tmp:
        root = Path(tmp); binary = root / 'large_body'
        build('tests/fixtures/http_large_body.neo', binary)
        certificates(root)
        def context(version, server_order):
            c = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); c.minimum_version = c.maximum_version = version
            c.load_cert_chain(str(root / 'leaf.pem'), str(root / 'leaf.key')); c.set_alpn_protocols(['http/1.1'])
            # OpenSSL's own TLS 1.3 order puts ChaCha20 before the client's AES-128.
            if server_order: c.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
            else: c.options &= ~ssl.OP_CIPHER_SERVER_PREFERENCE
            return c
        negotiated = set()
        for name, tls in [('TCP', None), ('TLS 1.3 (client order)', context(ssl.TLSVersion.TLSv1_3, False)),
                          ('TLS 1.3 (server order)', context(ssl.TLSVersion.TLSv1_3, True)), ('TLS 1.2', context(ssl.TLSVersion.TLSv1_2, False))]:
            with server(tls) as (port, accepted, suites):
                p = subprocess.run(RUNNER + [str(binary), str(port), str(root / 'ca.der') if tls else '-', *PATHS], capture_output=True, timeout=120)
                assert p.returncode == 0, (p.returncode, p.stdout, p.stderr)
                lines = p.stdout.decode().splitlines()
                assert lines == expected(tls), (name, lines, expected(tls))
                assert len(accepted) == 2, len(accepted)
            negotiated.update(suites)
            print(f'PASS large bodies over {name}{" " + "/".join(sorted(set(suites))) if suites else ""}: '
                  f'{len(PATHS)} requests, 1 B to 1 MiB, small writes, early close, excess bytes', flush=True)
        # With the CPU's AES instructions the client offers AES-128-GCM first, so
        # both TLS 1.3 paths ran: opened in place, and opened then copied.
        if ' aes' in Path('/proc/cpuinfo').read_text():
            assert {'TLS_AES_128_GCM_SHA256', 'TLS_CHACHA20_POLY1305_SHA256'} <= negotiated, negotiated


if __name__ == '__main__': main()
