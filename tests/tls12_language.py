#!/usr/bin/env python3
"""TLS 1.2 client: OpenSSL s_server peers, a rewriting proxy for attacks, and handshake timings.

Positive cases negotiate TLS 1.2 from the normal TLS 1.3+1.2 ClientHello against
`openssl s_server -tls1_2`: every suite (ECDHE_ECDSA/ECDHE_RSA with AES-128-GCM and
ChaCha20-Poly1305) with RSA-2048, ECDSA P-256 and ECDSA P-384 leaves over X25519 and P-256,
each ServerKeyExchange signature scheme forced with -sigalgs, an optional CertificateRequest,
multi-record downloads, fragmented handshake records, and TLS 1.3 servers still choosing 1.3.

Negative cases: a server without extended master secret (OpenSSL configured with
Options = -ExtendedMasterSecret), and, through a TLS-aware proxy, a tampered
ServerKeyExchange signature or point, a server Finished re-encrypted with the real keys
(recovered from the server's key log) but wrong verify_data, a corrupted Finished record,
the RFC 8446 downgrade sentinel (a TLS 1.3-capable OpenSSL reached by a ClientHello with
supported_versions stripped, so OpenSSL itself writes DOWNGRD\\x01), an injected early
ChangeCipherSpec, renegotiation_info missing or non-empty, an echoed session id
(resumption), unsolicited extensions, truncated handshake/Finished/application records,
wrong hostnames and an unsupported suite. Every failure must be a clean `rejected:`
(or `read rejected:`) with the expected reason.

  python3 tests/tls12_language.py [--timing-runs N]
"""
import contextlib
import hashlib
import hmac
import importlib.util
import os
from pathlib import Path
import random
import shlex
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = shlex.split(os.environ.get('NEO_RUNNER', ''))
SUITES = {'ECDHE-ECDSA-AES128-GCM-SHA256': 49195, 'ECDHE-RSA-AES128-GCM-SHA256': 49199,
          'ECDHE-ECDSA-CHACHA20-POLY1305': 52393, 'ECDHE-RSA-CHACHA20-POLY1305': 52392}
GROUPS = {'X25519': 29, 'P-256': 23}


def openssl(*args, data=None):
    r = subprocess.run(['openssl', *map(str, args)], input=data, capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout


def certificates(root):
    spec = importlib.util.spec_from_file_location('tls_language', ROOT / 'tests' / 'tls_language.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.certificates(root)
    (root / 'extensions').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\n'
                                     'subjectAltName=DNS:localhost,IP:127.0.0.1\n')
    openssl('req', '-new', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-384', '-nodes', '-keyout', root / 'p384-leaf.key',
            '-out', root / 'p384-leaf.csr', '-subj', '/CN=localhost')
    openssl('x509', '-req', '-in', root / 'p384-leaf.csr', '-CA', root / 'ec-ca.pem', '-CAkey', root / 'ec-ca.key', '-CAcreateserial',
            '-out', root / 'p384-leaf.pem', '-days', '1', '-sha256', '-extfile', root / 'extensions')
    (root / 'noems.cnf').write_text('openssl_conf = openssl_init\n[openssl_init]\nssl_conf = ssl_sect\n[ssl_sect]\n'
                                    'system_default = system_default_sect\n[system_default_sect]\nOptions = -ExtendedMasterSecret\n')
    (root / 'www').mkdir()
    (root / 'www' / 'big.bin').write_bytes(random.Random(1205).randbytes(300000))
    return root


# leaf name -> (certificate, key, trust anchor)
LEAVES = {'rsa': ('leaf.pem', 'leaf.key', 'ca.der'), 'p256': ('ec-leaf.pem', 'ec-leaf.key', 'ec-ca.der'),
          'p384': ('p384-leaf.pem', 'p384-leaf.key', 'ec-ca.der')}


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port


@contextlib.contextmanager
def server(root, leaf, options, env=None, keylog=None, www='-www'):
    cert, key, _ = LEAVES[leaf]; port = free_port()
    extra = ['-keylogfile', str(keylog)] if keylog else []
    proc = subprocess.Popen(['openssl', 's_server', '-accept', str(port), '-cert', str(root / cert), '-key', str(root / key), www, '-quiet', *extra, *options],
                            cwd=root / 'www', stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env={**os.environ, **(env or {})})
    try:
        for _ in range(300):
            try:
                socket.create_connection(('127.0.0.1', port), timeout=0.2).close(); break
            except OSError:
                if proc.poll() is not None: raise RuntimeError('openssl s_server exited: ' + proc.stderr.read().decode(errors='replace'))
                time.sleep(0.02)
        else:
            raise RuntimeError('openssl s_server did not start')
        yield port
    finally:
        proc.terminate(); proc.wait()


def frame(kind, payload, size=16384, version=b'\x03\x03'):
    return b''.join(bytes([kind]) + version + len(payload[i:i + size]).to_bytes(2, 'big') + payload[i:i + size] for i in range(0, len(payload), size))


def read_record(sock, buf):
    while True:
        if len(buf) >= 5:
            size = int.from_bytes(buf[3:5], 'big')
            if len(buf) >= 5 + size: return buf[:5 + size], buf[5 + size:]
        try:
            data = sock.recv(65536)
        except OSError:
            data = b''
        if not data: return None, buf
        buf += data


def u24(value): return value.to_bytes(3, 'big')


def client_hello_extensions_at(message):
    at = 38; at += 1 + message[at]; at += 2 + int.from_bytes(message[at:at + 2], 'big'); at += 1 + message[at]; return at


def server_hello_extensions_at(message): return 39 + message[38] + 3


def extensions(message, at):
    end = at + 2 + int.from_bytes(message[at:at + 2], 'big'); p = at + 2; out = []
    while p < end:
        kind = int.from_bytes(message[p:p + 2], 'big'); size = int.from_bytes(message[p + 2:p + 4], 'big')
        out.append((kind, message[p + 4:p + 4 + size])); p += 4 + size
    return out


def rebuild(message, at, items):
    body = b''.join(k.to_bytes(2, 'big') + len(v).to_bytes(2, 'big') + v for k, v in items)
    inner = message[4:at] + len(body).to_bytes(2, 'big') + body
    return message[:1] + u24(len(inner)) + inner


def edit_extensions(message, at, edit):
    return rebuild(message, at, edit(extensions(message, at)))


class Proxy:
    """One TLS connection between the Neo client and an upstream server, rewritten in flight.

    hello(message) rewrites the ClientHello. flight(proxy, messages) gets the server's plaintext
    handshake messages up to ServerHelloDone and returns (wire bytes, close). record(proxy, index,
    record) sees each server record after its ChangeCipherSpec (index 0 is the Finished) and returns
    (wire bytes, close). With chunk, server bytes are written to the client in chunks of that size."""

    def __init__(self, upstream, hello=None, flight=None, record=None, chunk=0):
        self.upstream = upstream; self.hello = hello; self.flight = flight; self.record = record; self.chunk = chunk
        self.client_random = self.server_random = self.client_sid = None; self.errors = []; self.seen = []; self.gone = False
        self.listener = socket.socket(); self.listener.bind(('127.0.0.1', 0)); self.listener.listen(); self.listener.settimeout(15)
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self.run, daemon=True); self.thread.start()

    def send(self, sock, data):
        # The client may already have rejected the connection and closed it.
        step = self.chunk or len(data) or 1
        try:
            for at in range(0, len(data), step): sock.sendall(data[at:at + step])
        except OSError:
            self.gone = True
        return not self.gone

    def run(self):
        try:
            client, _ = self.listener.accept()
        except OSError as ex:
            self.errors.append('accept: ' + repr(ex)); return
        with client, socket.create_connection(('127.0.0.1', self.upstream), timeout=15) as up:
            client.settimeout(15)
            pump = threading.Thread(target=self.client_to_server, args=(client, up), daemon=True); pump.start()
            try:
                self.server_to_client(up, client)
            except Exception as ex:
                self.errors.append('server->client: ' + repr(ex))
            with contextlib.suppress(OSError): client.shutdown(socket.SHUT_RDWR)
            with contextlib.suppress(OSError): up.shutdown(socket.SHUT_RDWR)
            pump.join(5)

    def client_to_server(self, client, up):
        try:
            record, buf = read_record(client, b'')
            if record is None: return
            message = record[5:]; assert message[0] == 1, 'expected ClientHello'
            self.client_random = message[6:38]; self.client_sid = message[39:39 + message[38]]
            if self.hello: message = self.hello(message)
            up.sendall(frame(22, message, version=record[1:3]) + buf)
            while True:
                data = client.recv(65536)
                if not data: break
                up.sendall(data)
            with contextlib.suppress(OSError): up.shutdown(socket.SHUT_WR)
        except OSError:
            pass

    def server_to_client(self, up, client):
        buf = b''; handshake = b''; messages = []; encrypted = False; index = 0
        while True:
            record, buf = read_record(up, buf)
            if record is None: return
            kind = record[0]; self.seen.append(kind)
            if encrypted:
                wire, close = self.record(self, index, record) if self.record else (record, False); index += 1
                if not self.send(client, wire) or close: return
                continue
            if kind == 20:
                encrypted = True
                if not self.send(client, record): return
                continue
            if kind != 22:
                if not self.send(client, record): return
                continue
            handshake += record[5:]
            while len(handshake) >= 4 and len(handshake) >= 4 + int.from_bytes(handshake[1:4], 'big'):
                size = 4 + int.from_bytes(handshake[1:4], 'big'); message = handshake[:size]; handshake = handshake[size:]
                if message[0] == 2: self.server_random = message[6:38]
                messages.append(message)
                if message[0] == 14:
                    wire, close = self.flight(self, messages) if self.flight else (frame(22, b''.join(messages)), False)
                    messages = []
                    if not self.send(client, wire) or close: return

    def close(self):
        self.listener.close(); self.thread.join(20); assert not self.thread.is_alive(), 'proxy thread still running'


def prf(secret, label, seed, count):
    out = b''; a = label + seed
    while len(out) < count:
        a = hmac.digest(secret, a, 'sha256'); out += hmac.digest(secret, a + label + seed, 'sha256')
    return out[:count]


def chacha(key, nonce, counter, data):
    return openssl('enc', '-chacha20', '-K', key.hex(), '-iv', (counter.to_bytes(4, 'little') + nonce).hex(), '-nosalt', data=data)


def chacha_seal(key, nonce, aad, plain):
    ciphertext = chacha(key, nonce, 1, plain); polykey = chacha(key, nonce, 0, bytes(32))
    mac = aad + bytes(-len(aad) % 16) + ciphertext + bytes(-len(ciphertext) % 16) + len(aad).to_bytes(8, 'little') + len(ciphertext).to_bytes(8, 'little')
    return ciphertext + bytes.fromhex(openssl('mac', '-macopt', 'hexkey:' + polykey.hex(), 'POLY1305', data=mac).decode().strip())


def master_secret(keylog, client_random):
    for _ in range(100):
        if keylog.exists():
            for line in keylog.read_text().splitlines():
                parts = line.split()
                if len(parts) == 3 and parts[0] == 'CLIENT_RANDOM' and parts[1] == client_random.hex(): return bytes.fromhex(parts[2])
        time.sleep(0.02)
    raise AssertionError('no CLIENT_RANDOM line in the server key log')


def finished_hook(keylog, forge):
    """Decrypts the server's ChaCha20-Poly1305 Finished with keys derived from the key log, then
    re-encrypts it unchanged (forge=False) or with altered verify_data (forge=True)."""
    def hook(proxy, index, record):
        if index != 0: return record, False
        block = prf(master_secret(keylog, proxy.client_random), b'key expansion', proxy.server_random + proxy.client_random, 88)
        key, iv = block[32:64], block[76:88]
        plain = chacha(key, iv, 1, record[5:-16])
        assert record[0] == 22 and plain[:4] == b'\x14\x00\x00\x0c', ('independent key derivation disagrees with OpenSSL', plain.hex())
        if forge: plain = plain[:4] + bytes(b ^ 0x5a for b in plain[4:])
        body = chacha_seal(key, iv, bytes(8) + b'\x16\x03\x03' + len(plain).to_bytes(2, 'big'), plain)
        return b'\x16\x03\x03' + len(body).to_bytes(2, 'big') + body, False
    return hook


def edit_message(kind, edit):
    def hook(proxy, messages):
        return frame(22, b''.join(edit(m) if m[0] == kind else m for m in messages)), False
    return hook


def flip_last(message): return message[:-1] + bytes([message[-1] ^ 1])


def flip_point(message): return message[:9] + bytes([message[9] ^ 1]) + message[10:]


def server_hello_edit(edit):
    return edit_message(2, lambda m: edit_extensions(m, server_hello_extensions_at(m), edit))


def echo_session(proxy, messages):
    def edit(message):
        sid = proxy.client_sid; old = message[38]
        inner = message[4:38] + bytes([len(sid)]) + sid + message[39 + old:]
        return message[:1] + u24(len(inner)) + inner
    return frame(22, b''.join(edit(m) if m[0] == 2 else m for m in messages)), False


def early_ccs(proxy, messages):
    return frame(22, messages[0]) + b'\x14\x03\x03\x00\x01\x01' + frame(22, b''.join(messages[1:])), False


def truncate_flight(proxy, messages):
    wire = frame(22, b''.join(messages)); return wire[:len(wire) // 2], True


def truncate_record(at):
    def hook(proxy, index, record):
        return (record[:len(record) // 2], True) if index == at else (record, False)
    return hook


def corrupt_finished(proxy, index, record):
    return (record[:-3] + bytes([record[-3] ^ 1]) + record[-2:], False) if index == 0 else (record, False)


def fragmented(proxy, messages):
    return frame(22, b''.join(messages), size=7), False


def strip_client_extension(kind):
    return lambda m: edit_extensions(m, client_hello_extensions_at(m), lambda items: [(k, v) for k, v in items if k != kind])


def main():
    runs = int(sys.argv[sys.argv.index('--timing-runs') + 1]) if '--timing-runs' in sys.argv else 15
    with tempfile.TemporaryDirectory(prefix='neo-tls12-') as tmp:
        root = certificates(Path(tmp)); binary = root / 'tls12'
        r = subprocess.run(['python3', '-m', 'neoc', 'build', 'tests/fixtures/language_tls12.neo', '-o', str(binary)], cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout[-3000:], r.stderr[-2000:])
        passed = 0

        def client(port, leaf, host='localhost', path='/', trust=None):
            trust = trust or LEAVES[leaf][2]
            r = subprocess.run(RUNNER + [str(binary), host, str(port), str(root / trust), path, '127.0.0.1'], capture_output=True, text=True, timeout=30)
            assert r.returncode == 0, (r.returncode, r.stdout, r.stderr[-2000:])
            lines = r.stdout.strip().splitlines(); assert lines, r.stderr[-2000:]
            return lines[-1]

        def fields(line):
            return dict(part.split('=', 1) for part in line.split() if '=' in part)

        def expect_ok(name, line, version=771, suite=None, group=None):
            nonlocal passed
            f = fields(line)
            assert line.startswith('version=') and f['version'] == str(version) and 'HTTP/1.0 200 ok' in line and 'read rejected' not in line, (name, line)
            if suite is not None: assert f['suite'] == str(suite), (name, line)
            if group is not None: assert f['group'] == str(group), (name, line)
            passed += 1; print(f'PASS {name}: {line}', flush=True)

        def expect_rejected(name, line, reason, prefix='rejected:'):
            nonlocal passed
            assert (line.startswith(prefix) or prefix in line) and reason in line, (name, reason, line)
            passed += 1; print(f'PASS {name}: {line}', flush=True)

        # Suites x leaf keys x groups.
        for leaf in ('rsa', 'p256', 'p384'):
            for cipher, suite in SUITES.items():
                if ('RSA' in cipher) != (leaf == 'rsa'): continue
                for group, number in GROUPS.items():
                    with server(root, leaf, ['-tls1_2', '-cipher', cipher, '-groups', group]) as port:
                        expect_ok(f'{leaf} {cipher} {group}', client(port, leaf), suite=suite, group=number)
        # ServerKeyExchange signature schemes forced on the server.
        for leaf, sigalgs in [('rsa', 'RSA+SHA256'), ('rsa', 'RSA+SHA384'), ('rsa', 'RSA+SHA512'), ('rsa', 'rsa_pss_rsae_sha256'), ('rsa', 'rsa_pss_rsae_sha384'),
                              ('p256', 'ECDSA+SHA256'), ('p256', 'ECDSA+SHA384'), ('p384', 'ECDSA+SHA384'), ('p384', 'ECDSA+SHA256')]:
            with server(root, leaf, ['-tls1_2', '-sigalgs', sigalgs]) as port:
                expect_ok(f'{leaf} ServerKeyExchange signed with {sigalgs}', client(port, leaf))
        # Optional client authentication: an empty client Certificate.
        with server(root, 'rsa', ['-tls1_2', '-verify', '1', '-CAfile', str(root / 'ca.pem')]) as port:
            expect_ok('CertificateRequest answered with an empty Certificate', client(port, 'rsa'))
        # Many records each way of the download, both AEADs.
        expected = (root / 'www' / 'big.bin').read_bytes(); total = 0
        for b in expected: total = (total * 31 + b) % 1000000007
        for cipher in ('ECDHE-RSA-AES128-GCM-SHA256', 'ECDHE-RSA-CHACHA20-POLY1305'):
            with server(root, 'rsa', ['-tls1_2', '-cipher', cipher], www='-WWW') as port:
                line = client(port, 'rsa', path='/big.bin')
                assert f'body={len(expected)} sum={total}' in line, (cipher, line, len(expected), total)
                expect_ok(f'300 kB download over {cipher}', line, suite=SUITES[cipher])
        # TLS 1.3 servers still negotiate TLS 1.3 from the same ClientHello.
        for leaf in ('rsa', 'p256'):
            with server(root, leaf, []) as port:
                expect_ok(f'{leaf} TLS 1.3-capable server', client(port, leaf), version=772, suite=4867, group=29)
        with server(root, 'rsa', ['-ciphersuites', 'TLS_AES_128_GCM_SHA256', '-groups', 'P-256']) as port:
            expect_ok('TLS 1.3 with HelloRetryRequest to P-256', client(port, 'rsa'), version=772, suite=4865, group=23)

        # Peers that must fail.
        with server(root, 'rsa', ['-tls1_2'], env={'OPENSSL_CONF': str(root / 'noems.cnf')}) as port:
            expect_rejected('server without extended master secret (OpenSSL -ExtendedMasterSecret)', client(port, 'rsa'), 'extended master secret')
        with server(root, 'rsa', ['-tls1_2', '-cipher', 'ECDHE-RSA-AES256-GCM-SHA384']) as port:
            expect_rejected('no shared TLS 1.2 suite', client(port, 'rsa'), 'alert 40')
        # secp384r1 is offered only for TLS 1.2 ECDSA certificate curves; key exchange on it fails cleanly.
        with server(root, 'rsa', ['-tls1_2', '-groups', 'P-384']) as port:
            expect_rejected('TLS 1.2 server insisting on secp384r1 key exchange', client(port, 'rsa'), 'secp384r1 key exchange')
        with server(root, 'rsa', ['-groups', 'P-384']) as port:
            expect_rejected('TLS 1.3 server insisting on secp384r1 (HelloRetryRequest)', client(port, 'rsa'), 'HelloRetryRequest')
        for host in ('evil.test', 'localhost.evil.test'):
            with server(root, 'rsa', ['-tls1_2']) as port:
                expect_rejected(f'wrong hostname {host}', client(port, 'rsa', host=host), 'hostname rejected')
        with server(root, 'p256', ['-tls1_2']) as port:
            expect_rejected('leaf issued by an untrusted root', client(port, 'p256', trust='ca.der'), 'hostname rejected')

        def proxied(name, leaf, options, reason, prefix='rejected:', keylog=None, success=None, **hooks):
            with server(root, leaf, options, keylog=keylog) as port:
                proxy = Proxy(port, **hooks)
                try:
                    line = client(proxy.port, leaf)
                finally:
                    proxy.close()
                assert not proxy.errors, (name, proxy.errors)
                if success is not None: expect_ok(name, line, **success)
                else: expect_rejected(name, line, reason, prefix)
                return proxy

        proxied('unmodified proxy, 1-byte TCP writes, 7-byte handshake records', 'rsa', ['-tls1_2'], None, success={}, flight=fragmented, chunk=1)
        proxied('unmodified proxy, 3-byte TCP writes, ECDSA P-384', 'p384', ['-tls1_2'], None, success={}, chunk=3)
        # Downgrade: a TLS 1.3-capable server sees no supported_versions, negotiates TLS 1.2 and
        # marks ServerHello.random with DOWNGRD\x01; the same rewrite against a TLS 1.2-only
        # server has no sentinel and fails only later, when the transcripts disagree.
        downgraded = proxied('downgrade sentinel from a TLS 1.3-capable OpenSSL', 'rsa', [], 'downgrade detected', hello=strip_client_extension(43))
        assert downgraded.server_random[-8:] == b'DOWNGRD\x01', downgraded.server_random.hex()
        control = proxied('same rewrite, TLS 1.2-only server: no sentinel, transcript mismatch', 'rsa', ['-tls1_2'], 'alert', hello=strip_client_extension(43))
        assert control.server_random[-8:] != b'DOWNGRD\x01'
        proxied('ClientHello without extended master secret reaches the server', 'rsa', ['-tls1_2'], 'extended master secret', hello=strip_client_extension(23))
        for leaf in ('rsa', 'p256', 'p384'):
            proxied(f'{leaf} tampered ServerKeyExchange signature', leaf, ['-tls1_2'], 'ServerKeyExchange signature rejected', flight=edit_message(12, flip_last))
        proxied('tampered ServerKeyExchange point', 'rsa', ['-tls1_2'], 'ServerKeyExchange signature rejected', flight=edit_message(12, flip_point))
        proxied('server Finished re-encrypted unchanged (key-log control)', 'rsa', ['-tls1_2', '-cipher', 'ECDHE-RSA-CHACHA20-POLY1305'], None,
                keylog=root / 'keys-control', success={'suite': 52392}, record=finished_hook(root / 'keys-control', False))
        proxied('server Finished with wrong verify_data, validly encrypted', 'rsa', ['-tls1_2', '-cipher', 'ECDHE-RSA-CHACHA20-POLY1305'], 'TLS Finished rejected',
                keylog=root / 'keys-forged', record=finished_hook(root / 'keys-forged', True))
        for cipher in ('ECDHE-RSA-AES128-GCM-SHA256', 'ECDHE-RSA-CHACHA20-POLY1305'):
            proxied(f'corrupted Finished record ({cipher})', 'rsa', ['-tls1_2', '-cipher', cipher], 'record authentication failed', record=corrupt_finished)
        proxied('ChangeCipherSpec injected after ServerHello', 'rsa', ['-tls1_2'], 'unexpected TLS change-cipher-spec', flight=early_ccs)
        proxied('renegotiation_info removed', 'rsa', ['-tls1_2'], 'secure renegotiation', flight=server_hello_edit(lambda items: [(k, v) for k, v in items if k != 0xff01]))
        proxied('renegotiation_info not empty', 'rsa', ['-tls1_2'], 'invalid TLS 1.2 ServerHello extensions',
                flight=server_hello_edit(lambda items: [(k, b'\x0c' + bytes(12) if k == 0xff01 else v) for k, v in items]))
        proxied('extended_master_secret removed from ServerHello', 'rsa', ['-tls1_2'], 'extended master secret',
                flight=server_hello_edit(lambda items: [(k, v) for k, v in items if k != 23]))
        proxied('unsolicited session_ticket extension', 'rsa', ['-tls1_2'], 'invalid TLS 1.2 ServerHello extensions',
                flight=server_hello_edit(lambda items: items + [(35, b'')]))
        proxied('server echoes the client session id (resumption)', 'rsa', ['-tls1_2'], 'session resumption', flight=echo_session)
        proxied('truncated server flight', 'rsa', ['-tls1_2'], 'transport closed', flight=truncate_flight)
        proxied('truncated Finished record', 'rsa', ['-tls1_2'], 'transport closed', record=truncate_record(0))
        proxied('truncated application record', 'rsa', ['-tls1_2'], 'transport closed', prefix='read rejected:', record=truncate_record(1))
        print(f'PASS TLS 1.2: {passed} cases', flush=True)

        # Handshake timings: tls_connect from first ClientHello byte to an established session.
        print(f'timing ({runs} runs each, microseconds, tls_connect over loopback):', flush=True)
        for name, leaf, options in [('TLS 1.2 ECDHE-RSA-CHACHA20 X25519, RSA-2048', 'rsa', ['-tls1_2', '-cipher', 'ECDHE-RSA-CHACHA20-POLY1305', '-groups', 'X25519']),
                                    ('TLS 1.2 ECDHE-RSA-AES128-GCM P-256, RSA-2048', 'rsa', ['-tls1_2', '-cipher', 'ECDHE-RSA-AES128-GCM-SHA256', '-groups', 'P-256']),
                                    ('TLS 1.2 ECDHE-ECDSA-AES128-GCM X25519, P-256', 'p256', ['-tls1_2', '-cipher', 'ECDHE-ECDSA-AES128-GCM-SHA256', '-groups', 'X25519']),
                                    ('TLS 1.2 ECDHE-ECDSA-CHACHA20 X25519, P-384', 'p384', ['-tls1_2', '-cipher', 'ECDHE-ECDSA-CHACHA20-POLY1305', '-groups', 'X25519']),
                                    ('TLS 1.3 CHACHA20 X25519, RSA-2048 (comparison)', 'rsa', []),
                                    ('TLS 1.3 CHACHA20 X25519, P-256 (comparison)', 'p256', [])]:
            samples = []
            with server(root, leaf, options) as port:
                for _ in range(runs):
                    samples.append(int(fields(client(port, leaf))['handshake_us']))
            print(f'  {name}: median {statistics.median(samples):.0f}  min {min(samples)}  max {max(samples)}', flush=True)


if __name__ == '__main__':
    main()
