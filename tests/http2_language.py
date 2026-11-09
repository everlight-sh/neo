#!/usr/bin/env python3
"""HTTP/2 over TLS (ALPN h2) with std:https_client's HttpClient.

Go's net/http (tests/http2_server.go) serves small and 1 MiB bodies, a large
header set that fills and evicts HPACK's dynamic table with Huffman-coded
values, a header block split over CONTINUATION frames, a streamed body without
Content-Length, a 3 MB upload that needs the server's WINDOW_UPDATEs, and
GOAWAY; requests run one after another on one connection, and a disconnected
client resumes its TLS session. The same server restricted to http/1.1, and
OpenSSL s_server without ALPN, check the fallback to HTTP/1.1 with the same
headers. A scripted HTTP/2 server then sends what Go does not: PING and
SETTINGS mid-exchange, padded and prioritized HEADERS, padded DATA, trailers,
an informational response, dynamic table size updates, RST_STREAM (an error,
REFUSED_STREAM a retry), GOAWAY before and after a stream, a connection error
and malformed response fields. HPACK itself is tested by tests/hpack_test.neo
(RFC 7541 Appendix C).

  python3 tests/http2_language.py
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import shlex
import socket
import ssl
import struct
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = shlex.split(os.environ.get('NEO_RUNNER', ''))


def tls_language():
    spec = importlib.util.spec_from_file_location('tls_language', ROOT / 'tests' / 'tls_language.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def pattern(n, mod):
    return bytes(i % mod for i in range(n))


def header_value(i):
    return 'v%03d-%s' % (i, chr(ord('a') + i % 26) * (20 + i % 40))


def ascii_value():
    out = ''
    for c in range(0x21, 0x7f):
        out += chr(c)
        if c % 16 == 0:
            out += ' '
    return out


BIG = ''.join('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'[(i * 7) % 62] for i in range(30000))
HEADERS = {**{'x-neo-h%03d' % i: header_value(i) for i in range(100)}, 'x-neo-ascii': ascii_value()}
BODIES = {'/hello': b'Hello, World!', '/1m': pattern(1 << 20, 253), '/headers': b'headers', '/big-headers': b'big',
          '/stream': pattern(10000, 241) * 50, '/goaway': b'bye'}


def sha(body):
    return hashlib.sha256(body).hexdigest()


def run(binary, port, trust, *steps, host='localhost', address='127.0.0.1'):
    r = subprocess.run(RUNNER + [str(binary), host, str(port), str(trust), address, *steps], capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, (steps, r.returncode, r.stdout[-3000:], r.stderr[-3000:])
    results = []
    for line in r.stdout.splitlines():
        if line.startswith('  '):
            name, _, value = line[2:].partition(': ')
            results[-1]['headers'][name] = value
            continue
        request, _, outcome = line.partition(' -> ')
        method, _, path = request.partition(' ')
        fields = outcome.split(' ')
        result = {'method': method, 'path': path, 'line': line, 'headers': {}}
        if fields[0] == 'error':
            result.update(error=int(fields[1]), message=' '.join(fields[2:]))
        else:
            result.update(status=int(fields[0]), protocol=fields[1], **{k: v for k, v in (f.split('=', 1) for f in fields[2:])})
        results.append(result)
    assert len(results) == sum(1 for s in steps if ':' in s), (steps, r.stdout[-3000:])
    return results


def expect(result, status, protocol, body=None, connections=None, resumptions=None):
    assert 'error' not in result, result['line']
    assert result['status'] == status and result['protocol'] == protocol, result['line']
    if body is not None:
        assert int(result['body']) == len(body) and result['sha256'] == sha(body), result['line']
    if connections is not None:
        assert int(result['connections']) == connections, result['line']
    if resumptions is not None:
        assert int(result['resumptions']) == resumptions, result['line']


def start_go(server, root, *options):
    proc = subprocess.Popen([str(server), '-cert', str(root / 'leaf.pem'), '-key', str(root / 'leaf.key'), *options],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc, int(proc.stdout.readline())


def go_cases(binary, server, root):
    ca = root / 'ca.der'
    proc, port = start_go(server, root)
    try:
        authenticated=run(binary,port,ca,'POST:/request-headers:4')[0]
        expect(authenticated,200,'h2',b'Bearer fixture-token|application/x-www-form-urlencoded')
        steps = ['GET:/hello', 'GET:/1m', 'GET:/headers', 'GET:/headers', 'GET:/big-headers', 'GET:/headers', 'GET:/stream',
                 'POST:/echo:3000000', 'HEAD:/1m', 'GET:/missing', 'PUT:/echo:0', 'GET:/hello']
        results = run(binary, port, ca, *steps)
        for step, result in zip(steps, results):
            method, path = step.split(':')[:2]
            body = pattern(3000000, 251) if step == 'POST:/echo:3000000' else b'' if method in ('HEAD', 'PUT') else BODIES.get(path)
            expect(result, 404 if path == '/missing' else 200, 'h2', body, connections=1)
        assert results[0]['headers'] == {'x-neo-proto': 'HTTP/2.0'}, results[0]
        for index in (2, 3, 5):
            assert results[index]['headers'] == HEADERS, (index, sorted(set(HEADERS.items()) ^ set(results[index]['headers'].items()))[:4])
        assert results[4]['headers'] == {'x-neo-big': BIG}, len(results[4]['headers'].get('x-neo-big', ''))
        assert results[7]['headers'] == {'x-neo-method': 'POST'} and results[10]['headers'] == {'x-neo-method': 'PUT'}
        print(f'PASS h2: {len(steps)} requests on one connection (1 MiB, 101 Huffman/dynamic-table headers, '
              f'CONTINUATION, streamed body, 3 MB upload, HEAD, 404)', flush=True)
        results = run(binary, port, ca, 'GET:/goaway', 'GET:/hello', 'GET:/conns')
        expect(results[0], 200, 'h2', b'bye', connections=1)
        expect(results[1], 200, 'h2', BODIES['/hello'], connections=2)
        print(f'PASS h2 GOAWAY after Connection: close, next request reconnects: {results[1]["line"]}', flush=True)
        results = run(binary, port, ca, 'GET:/hello', 'disconnect', 'GET:/hello', 'disconnect', 'GET:/1m', 'close', 'GET:/hello')
        for result, (connections, resumptions) in zip(results, [(1, 0), (2, 1), (3, 2), (4, 2)]):
            expect(result, 200, 'h2', BODIES[result['path']], connections, resumptions)
        print('PASS h2 with TLS resumption: resumptions 0, 1, 2, then 2 after http_client_close', flush=True)
    finally:
        proc.terminate(); proc.wait()
    proc, port = start_go(server, root, '-h1')
    try:
        authenticated=run(binary,port,ca,'POST:/request-headers:4')[0]
        expect(authenticated,200,'http/1.1',b'Bearer fixture-token|application/x-www-form-urlencoded')
        steps = ['GET:/hello', 'GET:/1m', 'GET:/headers', 'GET:/stream', 'POST:/echo:1000', 'HEAD:/1m', 'GET:/hello']
        results = run(binary, port, ca, *steps)
        for step, result in zip(steps, results):
            method, path = step.split(':')[:2]
            body = pattern(1000, 251) if method == 'POST' else b'' if method == 'HEAD' else BODIES[path]
            expect(result, 200, 'http/1.1', body, connections=1)
        assert results[0]['headers'] == {'x-neo-proto': 'HTTP/1.1'} and results[2]['headers'] == HEADERS, results[0]
        print(f'PASS fallback to HTTP/1.1 (server ALPN http/1.1 only): {len(steps)} keep-alive requests, same headers', flush=True)
    finally:
        proc.terminate(); proc.wait()
    port = free_port()
    proc = subprocess.Popen(['openssl', 's_server', '-accept', str(port), '-cert', str(root / 'leaf.pem'), '-key', str(root / 'leaf.key'),
                             '-tls1_3', '-www', '-quiet'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_port(port)
        results = run(binary, port, ca, 'GET:/', 'GET:/')
        expect(results[0], 200, 'http/1.1', connections=1); expect(results[1], 200, 'http/1.1', connections=2)
        print(f'PASS fallback to HTTP/1.1 (server without ALPN): {results[0]["line"]}', flush=True)
    finally:
        proc.terminate(); proc.wait()


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port


def wait_port(port):
    for _ in range(200):
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.2).close(); return
        except OSError:
            time.sleep(0.02)
    raise RuntimeError(f'nothing listens on {port}')


# A scripted HTTP/2 server: frames written by hand, requests decoded with the part of
# HPACK the client uses (static indices and literals without Huffman coding).
STATIC = {1: (':authority', ''), 2: (':method', 'GET'), 3: (':method', 'POST'), 4: (':path', '/'), 5: (':path', '/index.html'),
          6: (':scheme', 'http'), 7: (':scheme', 'https'), 28: ('content-length', '')}


def frame(kind, flags, stream, payload=b''):
    return struct.pack('>I', len(payload))[1:] + bytes([kind, flags]) + struct.pack('>I', stream) + payload


def literal(name, value, prefix=0x00):
    name, value = name.encode(), value.encode()
    assert len(name) < 127 and len(value) < 127
    return bytes([prefix, len(name)]) + name + bytes([len(value)]) + value


def hpack_int(block, at, prefix):
    mask = (1 << prefix) - 1; value = block[at] & mask; at += 1
    if value < mask:
        return value, at
    shift = 0
    while True:
        byte = block[at]; at += 1; value += (byte & 127) << shift; shift += 7
        if byte < 128:
            return value, at


def hpack_string(block, at):
    assert not block[at] & 0x80, 'the client does not Huffman-code'
    size, at = hpack_int(block, at, 7)
    return block[at:at + size].decode(), at + size


def decode_request(block):
    fields, at = [], 0
    while at < len(block):
        byte = block[at]
        if byte & 0x80:
            index, at = hpack_int(block, at, 7); fields.append(STATIC[index])
        else:
            assert byte & 0xe0 == 0, 'the client sends literals without indexing'
            index, at = hpack_int(block, at, 4)
            name = STATIC[index][0] if index else None
            if name is None:
                name, at = hpack_string(block, at)
            value, at = hpack_string(block, at)
            fields.append((name, value))
    return fields


class Connection:
    def __init__(self, server, tls):
        self.server, self.tls, self.buffer = server, tls, b''

    def read(self, n):
        while len(self.buffer) < n:
            chunk = self.tls.recv(65536)
            if not chunk:
                raise EOFError
            self.buffer += chunk
        out, self.buffer = self.buffer[:n], self.buffer[n:]
        return out

    def frame(self):
        head = self.read(9)
        size = int.from_bytes(head[:3], 'big')
        return head[3], head[4], int.from_bytes(head[5:9], 'big') & 0x7fffffff, self.read(size)

    def send(self, *frames):
        self.tls.sendall(b''.join(frames))

    def wait_for(self, done):
        """Reads frames, acknowledging SETTINGS, until done(kind, flags, payload) holds."""
        while True:
            kind, flags, stream, payload = self.frame()
            if kind == 4 and not flags & 1:
                self.send(frame(4, 1, 0))
            if done(kind, flags, payload):
                return

    def serve(self):
        assert self.read(24) == b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'
        self.send(frame(4, 0, 0, struct.pack('>HI', 3, 100)))
        requests = {}
        while True:
            kind, flags, stream, payload = self.frame()
            if kind == 4 and not flags & 1:
                settings = dict(struct.unpack('>HI', payload[i:i + 6]) for i in range(0, len(payload), 6))
                assert settings.get(2) == 0 and settings.get(4) == 16777216, settings
                self.send(frame(4, 1, 0))
            elif kind == 1:
                assert flags & 4 and stream % 2 == 1, 'one HEADERS frame per request'
                requests[stream] = (dict(decode_request(payload)), [])
                if flags & 1:
                    self.respond(stream, *requests.pop(stream))
            elif kind == 0 and stream in requests:
                requests[stream][1].append(payload)
                if flags & 1:
                    self.respond(stream, *requests.pop(stream))
            elif kind == 7:
                return

    def respond(self, stream, fields, chunks):
        body = b''.join(chunks); path = fields[':path']
        self.server.requests.append((fields[':method'], path))
        summary = ' '.join([fields[':method'], path, fields[':authority'], fields[':scheme'], fields.get('content-length', '-')])
        ok = b'\x88' + literal('x-neo-request', summary)
        if path == '/ping':
            self.send(frame(4, 0, 0, struct.pack('>HI', 4, 1 << 20)), frame(6, 0, 0, b'neo-ping'))
            acks = set()

            def acknowledged(kind, flags, payload):
                if flags & 1 and (kind == 4 or kind == 6 and payload == b'neo-ping'):
                    acks.add(kind)
                return acks == {4, 6}
            self.wait_for(acknowledged)
            self.send(frame(1, 4, stream, ok + literal('x-neo-ping', 'acked')), frame(0, 1, stream, b'pong'))
        elif path == '/padded':
            block = ok + literal('x-neo-padded', 'yes')
            self.send(frame(1, 8 | 32, stream, bytes([10]) + struct.pack('>IB', 0, 15) + block[:5] + bytes(10)),
                      frame(9, 0, stream, block[5:12]), frame(9, 4, stream, block[12:]),
                      frame(0, 8, stream, bytes([3]) + b'abc' + bytes(3)), frame(0, 0, stream, b''),
                      frame(0, 8 | 1, stream, bytes([200]) + b'defgh' + bytes(200)))
        elif path == '/trailers':
            self.send(frame(1, 4, stream, ok), frame(0, 0, stream, b'body'), frame(1, 5, stream, literal('x-neo-trailer', 'yes')))
        elif path == '/early':
            self.send(frame(1, 4, stream, b'\x00\x07:status\x03103' + literal('link', '</a.css>; rel=preload')),
                      frame(1, 4, stream, ok + literal('x-neo-final', 'yes')), frame(0, 1, stream, b'final'))
        elif path == '/size-update':
            self.send(frame(1, 5, stream, b'\x20\x3f\xe1\x1f' + ok + literal('x-neo-indexed', 'first', 0x40)))
        elif path == '/size-again':
            self.send(frame(1, 5, stream, ok + b'\xbe'))
        elif path == '/rst':
            self.send(frame(3, 0, stream, struct.pack('>I', 2)))
        elif path == '/refuse' and self.server.count(path) == 1:
            self.send(frame(3, 0, stream, struct.pack('>I', 7)))
        elif path == '/goaway-zero' and self.server.count(path) == 1:
            self.send(frame(7, 0, 0, struct.pack('>II', 0, 0))); raise EOFError
        elif path == '/goaway-after':
            self.send(frame(1, 5, stream, ok), frame(7, 0, 0, struct.pack('>II', stream, 0))); raise EOFError
        elif path == '/bad-frame':
            self.send(frame(0, 0, 0, b'x'))
        elif path == '/uppercase':
            self.send(frame(1, 5, stream, ok + literal('X-Neo-Upper', 'no')))
        else:
            self.send(frame(1, 4, stream, ok), frame(0, 1, stream, body or b'plain'))


class Scripted:
    def __init__(self, root):
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(str(root / 'leaf.pem'), str(root / 'leaf.key'))
        self.context.set_alpn_protocols(['h2'])
        self.listener = socket.create_server(('127.0.0.1', 0)); self.port = self.listener.getsockname()[1]
        self.requests, self.connections, self.errors = [], 0, []
        threading.Thread(target=self.accept, daemon=True).start()

    def count(self, path):
        return sum(1 for _, p in self.requests if p == path)

    def accept(self):
        while True:
            conn, _ = self.listener.accept(); self.connections += 1
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()

    def handle(self, conn):
        try:
            with self.context.wrap_socket(conn, server_side=True) as tls:
                assert tls.selected_alpn_protocol() == 'h2'
                Connection(self, tls).serve()
        except (EOFError, ConnectionError, ssl.SSLError, OSError):
            pass
        except AssertionError as error:
            self.errors.append(repr(error))


def scripted_cases(binary, root):
    server = Scripted(root); ca = root / 'ca.der'; port = server.port

    def check(name, steps, outcomes, connections=None):
        results = run(binary, port, ca, *steps)
        for result, outcome in zip(results, outcomes):
            if isinstance(outcome, int):
                assert result.get('error') == outcome, (name, result['line'])
            else:
                status, body = outcome
                expect(result, status, 'h2', body)
                method, path = result['method'], result['path']
                assert result['headers'].get('x-neo-request', '').startswith(f'{method} {path} localhost:{port} https'), (name, result)
        if connections is not None:
            assert int(results[-1]['connections']) == connections, (name, results[-1]['line'])
        assert not server.errors, server.errors
        print(f'PASS {name}: ' + ' | '.join(r['line'] for r in results), flush=True)
        return results

    results = check('PING, SETTINGS, padding, priority, CONTINUATION, trailers, 103, size updates',
                    ['GET:/ping', 'GET:/padded', 'GET:/trailers', 'GET:/early', 'GET:/size-update', 'GET:/size-again', 'POST:/plain:5000', 'GET:/plain'],
                    [(200, b'pong'), (200, b'abcdefgh'), (200, b'body'), (200, b'final'), (200, b''), (200, b''), (200, pattern(5000, 251)), (200, b'plain')], 1)
    assert results[0]['headers'].get('x-neo-ping') == 'acked' and results[1]['headers'].get('x-neo-padded') == 'yes', results[:2]
    assert results[3]['headers'].get('x-neo-final') == 'yes' and 'x-neo-trailer' not in results[2]['headers']
    assert results[4]['headers'].get('x-neo-indexed') == 'first' and results[5]['headers'].get('x-neo-indexed') == 'first', results[4:6]
    assert results[6]['headers']['x-neo-request'].endswith(' 5000'), results[6]
    check('RST_STREAM fails the request and keeps the connection', ['GET:/plain', 'GET:/rst', 'GET:/plain'], [(200, b'plain'), 104, (200, b'plain')], 1)
    check('REFUSED_STREAM retries a POST', ['POST:/refuse:10'], [(200, pattern(10, 251))])
    assert server.count('/refuse') == 2
    check('GOAWAY before the stream retries on a new connection', ['POST:/goaway-zero:0'], [(200, b'plain')], 2)
    check('GOAWAY after the stream: the next request reconnects', ['GET:/goaway-after', 'GET:/plain'], [(200, b''), (200, b'plain')], 2)
    check('connection error (DATA on stream 0), then a new connection', ['GET:/bad-frame', 'GET:/plain'], [71, (200, b'plain')], 2)
    check('malformed response field fails the stream only', ['GET:/uppercase', 'GET:/plain'], [71, (200, b'plain')], 1)


def main():
    with tempfile.TemporaryDirectory(prefix='neo-http2-') as tmp:
        root = tls_language().certificates(Path(tmp)); binary = root / 'http2'; server = root / 'http2-server'
        r = subprocess.run(['python3', '-m', 'neoc', 'build', 'tests/fixtures/language_http2.neo', '-o', str(binary)], cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout[-3000:], r.stderr[-2000:])
        r = subprocess.run(['go', 'build', '-trimpath', '-o', str(server), 'tests/http2_server.go'], cwd=ROOT,
                           env={**os.environ, 'GOWORK': 'off', 'CGO_ENABLED': '0'}, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-2000:]
        go_cases(binary, server, root)
        scripted_cases(binary, root)


if __name__ == '__main__':
    main()
