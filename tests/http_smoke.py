#!/usr/bin/env python3
"""Build and exercise the Neo HTTP runtime. Optional --binary skips the build."""
import argparse
import concurrent.futures
import errno
import http.client
import json
import math
import os
from pathlib import Path
import platform
import resource
import selectors
import socket
import signal
import shlex
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def checksum(n):
    a = [(i * 2654435761) % 1000003 for i in range(n)]
    for _ in range(32):
        a = [a[i] if i == 0 or i + 1 == n else (a[i-1] + 2*a[i] + a[i+1]) % 1000003 for i in range(n)]
    return sum(a)


def descriptors(pid):
    # Connections may close while the directory is listed.
    links = set()
    for fd in Path(f'/proc/{pid}/fd').iterdir():
        try: links.add(os.readlink(fd))
        except FileNotFoundError: pass
    return links


def burst(port, n):
    """Starts n non-blocking connects at once, then one GET on each; returns how
    many were answered. A reset leaves a connection unanswered: the kernel resets
    what overflows the listen queue. Any other failure, such as a connection
    closed without a full response, fails the test."""
    sockets, answered = [], 0
    with selectors.DefaultSelector() as selector:
        try:
            for i in range(n):
                s = socket.socket(); s.setblocking(False); sockets.append(s)
                assert s.connect_ex(('127.0.0.1', port)) in (0, errno.EINPROGRESS)
                selector.register(s, selectors.EVENT_WRITE, [i, b''])
            deadline = time.monotonic() + 20
            while selector.get_map() and time.monotonic() < deadline:
                for key, mask in selector.select(1):
                    s, state = key.fileobj, key.data
                    try:
                        if mask & selectors.EVENT_WRITE:
                            error = s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                            if error: raise OSError(error, os.strerror(error))
                            s.sendall(b'GET / HTTP/1.1\r\nHost: x\r\n\r\n')
                            selector.modify(s, selectors.EVENT_READ, state); continue
                        chunk = s.recv(4096)
                        state[1] += chunk
                        if chunk and not state[1].endswith(b'Hello, World!'): continue
                        assert chunk, f'connection closed after {bytes(state[1][:80])!r}'
                        answered += 1
                    except (ConnectionResetError, BrokenPipeError): pass
                    selector.unregister(s)
        finally:
            for s in sockets: s.close()
    return answered


# x86-64 Linux serves with io_uring by default; NEO_HTTP_URING=0 selects epoll.
URING_DEFAULT = sys.platform.startswith('linux') and platform.machine() == 'x86_64'


def verify(binary, workers=4, backend=None):
    # The burst holds 512 client sockets, and a single worker as many (macOS defaults to 256).
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    wanted = 4096 if hard == resource.RLIM_INFINITY else min(hard, 4096)
    if soft != resource.RLIM_INFINITY and soft < wanted: resource.setrlimit(resource.RLIMIT_NOFILE, (wanted, hard))
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    env = dict(os.environ, NEO_THREADS=str(workers))
    if backend: env['NEO_HTTP_URING'] = '1' if backend == 'io_uring' else '0'
    serving = backend or ('io_uring' if URING_DEFAULT else 'default')
    print(f'== {serving} backend{"" if backend else " (default)"}, {workers} worker(s)', flush=True)
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(shlex.split(os.environ.get('NEO_RUNNER', ''))+[str(binary), str(port)], stderr=log, stdout=log,
                                   start_new_session=True, env=env)
        try:
            for _ in range(100):
                if process.poll() is not None: raise AssertionError('server exited during startup')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.1): pass
                    break
                except OSError: time.sleep(.05)
            else: raise AssertionError('server did not start')

            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)

            def request(method, path, body=None):
                connection.request(method, path, body=body)
                response = connection.getresponse()
                data = response.read()
                assert int(response.getheader('Content-Length')) == len(data)
                return response.status, data

            assert request('GET', '/') == (200, b'Hello, World!')
            for n in (1, 10, 1000):
                status, data = request('GET', f'/smooth/{n}')
                assert status == 200 and json.loads(data) == {'n': n, 'passes': 32, 'checksum': checksum(n)}
            status, data = request('POST', '/nbody', '{"n":10,"steps":2}')
            value = json.loads(data)
            assert status == 200 and value['n'] == 10 and value['steps'] == 2 and math.isfinite(value['energy'])
            for n in (3, 1000):
                status, data = request('GET', f'/page/{n}')
                assert status == 200 and data.startswith(b'<!DOCTYPE html>') and data.count(b'<tr class=') == n
            assert request('GET', '/missing') == (404, b'Not Found')
            assert request('POST', '/', 'hello') == (405, b'')
            for path in ('/smooth/0', '/page/0'):
                assert request('GET', path)[0] == 400
            connection.close()
            print('Endpoints, framing, keep-alive, reference checksum, large HTML: PASS', flush=True)

            def hello(_):
                c = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                try:
                    c.request('GET', '/')
                    r = c.getresponse()
                    assert (r.status, r.read()) == (200, b'Hello, World!')
                finally: c.close()
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
                list(pool.map(hello, range(100)))
            print('100 concurrent requests: PASS', flush=True)

            # Connect far more sockets at once than macOS's listen queue holds
            # (kern.ipc.somaxconn, 128 by default). Every accepted connection
            # must be answered. While the machine is busy enough that no worker
            # runs during the burst, the kernel resets the overflow, for any
            # server; those connections are retried.
            unanswered = 512
            for attempt in range(5):
                unanswered -= burst(port, unanswered)
                if unanswered == 0: break
                time.sleep(.2)
            assert unanswered == 0, f'{unanswered} of 512 simultaneous connections unanswered after 5 attempts'
            print(f'512 simultaneous connections: PASS ({attempt} retries)', flush=True)

            slow = []
            try:
                for _ in range(8):
                    s = socket.create_connection(('127.0.0.1', port), timeout=5)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2048)
                    s.sendall(b'GET /page/1000 HTTP/1.1\r\nHost: x\r\n\r\n')
                    slow.append(s)
                time.sleep(.05)
                hello(0)
            finally:
                for s in slow: s.close()
            print('Slow readers do not block other clients: PASS', flush=True)

            # A fragmented POST body followed by a pipelined GET must preserve
            # both the body boundary and the next request on the same socket.
            with socket.create_connection(('127.0.0.1', port), timeout=5) as s:
                body = b'{"n":10,"steps":2}'
                s.sendall(b'POST /nbody HTTP/1.1\r\nHost: x\r\ncontent-length: ' + str(len(body)).encode() + b'\r\n\r\n')
                for byte in body:
                    s.sendall(bytes([byte])); time.sleep(.001)
                s.sendall(b'GET / HTTP/1.1\r\nHost: x\r\nConnection: Keep-Alive, Close\r\n\r\n')
                stream = s.makefile('rb')
                for expected in (b'energy', b'Hello, World!'):
                    assert stream.readline().startswith(b'HTTP/1.1 200')
                    headers = {}
                    while (line := stream.readline()) != b'\r\n':
                        assert line
                        k, v = line.split(b':', 1); headers[k.lower()] = v.strip()
                    assert expected in stream.read(int(headers[b'content-length']))
                assert stream.read(1) == b''
                stream.close()
            print('Fragmented POST, case-insensitive headers, pipelined GET and close: PASS', flush=True)

            # Exceed the per-event batching limit. Buffered complete requests
            # must keep progressing even when no new socket bytes arrive.
            with socket.create_connection(('127.0.0.1', port), timeout=10) as s:
                requests = [b'GET / HTTP/1.1\r\nHost: x\r\n\r\n'] * 511
                requests.append(b'GET / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n')
                s.sendall(b''.join(requests))
                stream = s.makefile('rb')
                for _ in requests:
                    assert stream.readline().startswith(b'HTTP/1.1 200')
                    length = None
                    while (line := stream.readline()) != b'\r\n':
                        assert line
                        if line.lower().startswith(b'content-length:'): length = int(line.split(b':', 1)[1])
                    assert length is not None and stream.read(length) == b'Hello, World!'
                assert stream.read(1) == b''
                stream.close()
            print('512 pipelined responses cross batch limits and preserve close/order: PASS', flush=True)

            def read_response(stream):
                assert stream.readline().startswith(b'HTTP/1.1 200')
                length = None
                while (line := stream.readline()) != b'\r\n':
                    assert line
                    if line.lower().startswith(b'content-length:'):
                        length = int(line.split(b':', 1)[1])
                assert length is not None
                body = stream.read(length)
                assert len(body) == length
                return body

            # Closing half a ready batch moves surviving dense slots. Refill
            # those slots repeatedly to catch stale event tokens / fd reuse.
            clients = []
            try:
                for turn in range(16):
                    while len(clients) < 80:
                        sock = socket.create_connection(('127.0.0.1', port), timeout=10)
                        clients.append((sock, sock.makefile('rb')))
                    for i, (sock, _) in enumerate(clients):
                        n = 3 + (i + turn) % 2
                        close = b'Connection: close\r\n' if i % 2 == turn % 2 else b''
                        sock.sendall(f'GET /page/{n} HTTP/1.1\r\nHost: x\r\n'.encode() + close + b'\r\n')
                    survivors = []
                    for i, (sock, stream) in enumerate(clients):
                        body = read_response(stream)
                        assert body.count(b'<tr class=') == 3 + (i + turn) % 2
                        if i % 2 == turn % 2:
                            assert stream.read(1) == b''
                            stream.close(); sock.close()
                        else: survivors.append((sock, stream))
                    clients = survivors
            finally:
                for sock, stream in clients: stream.close(); sock.close()
            print('Ready-batch close, slot compaction and descriptor reuse: PASS', flush=True)

            # More output than the socket can queue forces write readiness.
            # Verify every byte after draining it, then a different final reply.
            with socket.create_connection(('127.0.0.1', port), timeout=15) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32768)
                s.sendall(b'GET /page/1000 HTTP/1.1\r\nHost: x\r\n\r\n' * 80 +
                          b'GET / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n')
                time.sleep(.1)
                hello(0)
                stream = s.makefile('rb')
                expected = read_response(stream)
                assert expected.count(b'<tr class=') == 1000
                for _ in range(79): assert read_response(stream) == expected
                assert read_response(stream) == b'Hello, World!'
                assert stream.read(1) == b''
                stream.close()
            print('Backpressure drains 80 large responses, resumes buffered work and closes: PASS', flush=True)

            # Unsupported/ambiguous framing is rejected by closing the connection.
            for headers in (b'Content-Length: -1', b'Content-Length: 1\r\nContent-Length: 1', b'Transfer-Encoding: chunked', b'Content-Length: 9999999999999999999999999'):
                with socket.create_connection(('127.0.0.1', port), timeout=3) as s:
                    s.sendall(b'POST / HTTP/1.1\r\nHost: x\r\n' + headers + b'\r\n\r\n')
                    assert s.recv(1) == b''
            print('Invalid, duplicate, overflowing and unsupported body framing: PASS', flush=True)
            subprocess.run(['python3', str(ROOT / 'bench/http/protocol_test.py'), str(port)], check=True, timeout=20)
            assert process.poll() is None
            # Worker 0 has served by now, so its ring exists exactly when io_uring is in use.
            if sys.platform.startswith('linux') and not os.environ.get('NEO_RUNNER'):
                ring = 'anon_inode:[io_uring]' in descriptors(process.pid)
                assert ring == (serving == 'io_uring'), f'expected the {serving} backend, io_uring ring open: {ring}'
        finally:
            os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
            log.seek(0)
            print(log.read().decode(), end='')
            print('Test server stopped.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    # Where io_uring is the default, every case also runs on epoll and with one worker.
    runs = [(args.workers, None)] + ([(args.workers, 'epoll'), (1, None)] if URING_DEFAULT else [])
    if args.binary:
        for workers, backend in runs: verify(args.binary.resolve(), workers, backend)
        return
    with tempfile.TemporaryDirectory(prefix='neo-http-test-') as tmp:
        binary = Path(tmp) / 'http'
        subprocess.run([str(ROOT / 'neoc.sh'), 'build', 'examples/http.neo', '--no-cache', '-o', str(binary)], cwd=ROOT, check=True)
        for workers, backend in runs: verify(binary, workers, backend)


if __name__ == '__main__': main()
