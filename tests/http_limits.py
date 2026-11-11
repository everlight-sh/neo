#!/usr/bin/env python3
"""The HTTP runtime's limits over real sockets, on every Linux backend:
refused requests (400, 413, 431) answered with Connection: close, 100-continue,
header, body and idle timeouts, the per-worker connection limit (503), worker
restarts, and client addresses (web_peer, web_client_ip, web_client_proto)."""
import argparse, os, platform, shlex, signal, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URING = sys.platform.startswith('linux') and platform.machine() == 'x86_64'


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]


class Server:
    def __init__(self, binary, backend, **env):
        self.port = free_port()
        environment = dict(os.environ, NEO_THREADS='1'); environment.update({k: str(v) for k, v in env.items()})
        if backend == 'epoll': environment['NEO_HTTP_URING'] = '0'
        if backend == 'poll': environment['NEO_HTTP_POLL'] = '1'
        if backend == 'io_uring': environment['NEO_HTTP_URING'] = '1'
        self.log = tempfile.TemporaryFile()
        self.process = subprocess.Popen(shlex.split(os.environ.get('NEO_RUNNER', '')) + [str(binary), str(self.port)],
                                        env=environment, stdout=self.log, stderr=self.log, start_new_session=True)
        for _ in range(100):
            assert self.process.poll() is None, 'server exited during startup'
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=.1): return
            except OSError: time.sleep(.05)
        raise AssertionError('server did not start')

    def connect(self, timeout=5):
        s = socket.create_connection(('127.0.0.1', self.port), timeout=timeout); return s

    def stop(self):
        try: os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: self.process.wait(timeout=3)
        except subprocess.TimeoutExpired: os.killpg(self.process.pid, signal.SIGKILL); self.process.wait()
        self.log.seek(0); return self.log.read().decode(errors='replace')

    def __enter__(self): return self
    def __exit__(self, *exc):
        output = self.stop()
        if exc[0] is not None: print(output, end='')


def until_closed(s, limit=10):
    """Everything the server sends before it closes; fails on a reset."""
    s.settimeout(limit); data = b''
    while chunk := s.recv(65536): data += chunk
    return data


def get(server, path, headers=b''):
    with server.connect() as s:
        s.sendall(b'GET ' + path.encode() + b' HTTP/1.1\r\nHost: x\r\nConnection: close\r\n' + headers + b'\r\n')
        wire = until_closed(s)
    head, _, body = wire.partition(b'\r\n\r\n')
    return int(head.split(b' ')[1]), body


def refusals(server):
    for headers, status in ((b'Content-Length: -1', 400), (b'Content-Length: 1\r\nContent-Length: 1', 400),
                            (b'Transfer-Encoding: gzip', 400), (b'Content-Length: 0\r\nTransfer-Encoding: chunked', 400),
                            (b'Content-Length: 16777217', 413), (b'Content-Length: 9999999999999999999999999', 413)):
        with server.connect() as s:
            s.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\n' + headers + b'\r\n\r\n')
            wire = until_closed(s)
            assert wire.startswith(b'HTTP/1.1 %d ' % status) and b'Connection: close\r\n' in wire, (headers, wire)
    # Headers over 16 KiB, with and without their end.
    for end in (b'', b'\r\n\r\n'):
        with server.connect() as s:
            s.sendall(b'GET / HTTP/1.1\r\nHost: x\r\nX-Big: ' + b'a' * 17000 + end)
            wire = until_closed(s)
            assert wire.startswith(b'HTTP/1.1 431 '), wire
    # A client still uploading a body over the limit reads the 413, not a reset.
    with server.connect() as s:
        s.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 20000000\r\n\r\n' + b'x' * 200000)
        wire = until_closed(s)
        assert wire.startswith(b'HTTP/1.1 413 '), wire
    # Bad chunked framing.
    with server.connect() as s:
        s.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\nzz\r\nhello\r\n0\r\n\r\n')
        assert until_closed(s).startswith(b'HTTP/1.1 400 ')
    # Pipelined: the good request is answered, then the bad one is refused.
    with server.connect() as s:
        s.sendall(b'GET / HTTP/1.1\r\nHost: x\r\n\r\nPOST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: x\r\n\r\n')
        wire = until_closed(s)
        assert wire.startswith(b'HTTP/1.1 200 ') and b'Hello, World!HTTP/1.1 400 ' in wire, wire
    print('  400, 413 and 431 with Connection: close, including mid-upload and pipelined: PASS', flush=True)


def continues(server):
    with server.connect() as s:
        s.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\nExpect: 100-continue\r\n\r\n')
        s.settimeout(5); interim = s.recv(4096)
        assert interim == b'HTTP/1.1 100 Continue\r\n\r\n', interim
        s.sendall(b'he'); time.sleep(.05); s.sendall(b'llo')
        reply = s.recv(4096)
        assert reply.startswith(b'HTTP/1.1 200 ') and reply.endswith(b'\r\n\r\n5'), reply
        # The next request on the connection gets its own 100 Continue.
        s.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 2\r\nExpect: 100-Continue\r\nConnection: close\r\n\r\n')
        assert s.recv(4096) == b'HTTP/1.1 100 Continue\r\n\r\n'
        s.sendall(b'ok'); assert until_closed(s).endswith(b'\r\n\r\n2')
    # Body sent with the headers: no interim response.
    with server.connect() as s:
        s.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 3\r\nExpect: 100-continue\r\nConnection: close\r\n\r\nabc')
        wire = until_closed(s); assert wire.startswith(b'HTTP/1.1 200 ') and wire.endswith(b'3'), wire
    # Over the limit: 413 at once, without 100 Continue.
    with server.connect() as s:
        s.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 16777217\r\nExpect: 100-continue\r\n\r\n')
        assert until_closed(s).startswith(b'HTTP/1.1 413 ')
    # HTTP/1.0 clients get no interim response.
    with server.connect() as s:
        s.sendall(b'POST /echo HTTP/1.0\r\nContent-Length: 2\r\nExpect: 100-continue\r\n\r\n')
        s.settimeout(.5)
        try: early = s.recv(4096)
        except TimeoutError: early = b''
        assert early == b'', early
        s.sendall(b'ok'); assert until_closed(s).endswith(b'\r\n\r\n2')
    print('  Expect: 100-continue: PASS', flush=True)


def timeouts(binary, backend):
    with Server(binary, backend, NEO_HTTP_HEADER_TIMEOUT_MS=1500, NEO_HTTP_BODY_TIMEOUT_MS=1500, NEO_HTTP_IDLE_TIMEOUT_MS=2000) as server:
        start = time.monotonic()
        slow = server.connect(); slow.sendall(b'GET / HTTP/1.1\r\nHost: x\r\n')
        body = server.connect(); body.sendall(b'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 10\r\n\r\nabc')
        idle = server.connect(); idle.sendall(b'GET / HTTP/1.1\r\nHost: x\r\n\r\n')
        idle.settimeout(5); assert idle.recv(4096).endswith(b'Hello, World!')
        # Slowloris: a byte a second keeps nothing alive past the header timeout.
        drip = server.connect(); drip.sendall(b'GET / HTTP/1.1\r\n')
        for _ in range(2): time.sleep(.6); drip.sendall(b'X')
        wire = until_closed(slow); took = time.monotonic() - start
        assert wire.startswith(b'HTTP/1.1 408 ') and 1.4 < took < 3.6, (wire, took)
        assert until_closed(drip).startswith(b'HTTP/1.1 408 ')
        assert until_closed(body) == b''; took = time.monotonic() - start
        assert 1.4 < took < 3.6, took
        assert until_closed(idle) == b''; took = time.monotonic() - start
        assert 1.9 < took < 4.1, took
        # An active keep-alive connection is not idle.
        with server.connect() as s:
            for _ in range(5):
                s.sendall(b'GET / HTTP/1.1\r\nHost: x\r\n\r\n'); assert s.recv(4096).endswith(b'Hello, World!'); time.sleep(.6)
        for s in (slow, body, idle, drip): s.close()
    print('  header (408), body and keep-alive idle timeouts: PASS', flush=True)


def limit(binary, backend):
    with Server(binary, backend, NEO_HTTP_CONNECTIONS=4) as server:
        # Let the startup probe's connection close first: it counts until then.
        assert get(server, '/') == (200, b'Hello, World!'); time.sleep(.2)
        held = [server.connect() for _ in range(4)]
        for s in held: s.sendall(b'GET / HTTP/1.1\r\nHost: x\r\n\r\n'); assert s.recv(4096).endswith(b'Hello, World!')
        with server.connect() as extra:
            wire = until_closed(extra); assert wire.startswith(b'HTTP/1.1 503 ') and b'Retry-After: 1' in wire, wire
        held.pop().close(); time.sleep(.2)
        assert get(server, '/') == (200, b'Hello, World!')
        for s in held: s.close()
    print('  NEO_HTTP_CONNECTIONS limit answers 503: PASS', flush=True)


def addresses(binary, backend):
    with Server(binary, backend) as server:
        assert get(server, '/peer') == (200, b'127.0.0.1 127.0.0.1 http')
        assert get(server, '/peer', b'X-Forwarded-For: 203.0.113.9\r\nX-Forwarded-Proto: https\r\n') == (200, b'127.0.0.1 127.0.0.1 http')
    with Server(binary, backend, NEO_TRUSTED_PROXIES='127.0.0.1, 10.0.0.0/8,fd00::/8') as server:
        cases = [(b'', b'127.0.0.1 127.0.0.1 http'),
                 (b'X-Forwarded-For: 203.0.113.9\r\nX-Forwarded-Proto: https\r\n', b'127.0.0.1 203.0.113.9 https'),
                 # The right-most untrusted entry; spoofed entries to its left are ignored.
                 (b'X-Forwarded-For: 1.1.1.1, 203.0.113.9, 10.1.2.3\r\nX-Forwarded-Proto: http, https, http\r\n', b'127.0.0.1 203.0.113.9 https'),
                 (b'X-Forwarded-For: 1.1.1.1\r\nX-Forwarded-For: 198.51.100.7:4711, fd00::1\r\n', b'127.0.0.1 198.51.100.7 http'),
                 (b'X-Forwarded-For: [2001:DB8:0:0:0:0:0:1]:443\r\n', b'127.0.0.1 2001:db8::1 http'),
                 (b'X-Forwarded-For: ::ffff:192.0.2.1\r\n', b'127.0.0.1 192.0.2.1 http'),
                 # Every entry trusted: the left-most. An unreadable entry: the hop to its right.
                 (b'X-Forwarded-For: 10.0.0.1, 10.0.0.2\r\n', b'127.0.0.1 10.0.0.1 http'),
                 (b'X-Forwarded-For: 203.0.113.9, garbage, 10.0.0.2\r\nX-Forwarded-Proto: https\r\n', b'127.0.0.1 10.0.0.2 https')]
        for headers, expected in cases:
            got = get(server, '/peer', headers); assert got == (200, expected), (headers, got)
    print('  web_peer, web_client_ip and web_client_proto behind NEO_TRUSTED_PROXIES: PASS', flush=True)


def children(pid):
    try: return [int(p) for p in Path(f'/proc/{pid}/task/{pid}/children').read_text().split()]
    except FileNotFoundError: return []


def settled_children(pid, count, seconds=3):
    """The listener opens before the workers fork, so wait for them."""
    deadline = time.monotonic() + seconds
    while len(found := children(pid)) != count and time.monotonic() < deadline: time.sleep(.02)
    return found


def restarts(binary, backend):
    with Server(binary, backend, NEO_THREADS=2) as server:
        workers = settled_children(server.process.pid, 2)
        assert len(workers) == 2, workers
        for round in range(6):
            with server.connect() as s:
                s.sendall(b'GET /crash HTTP/1.1\r\nHost: x\r\nX-Crash: yes\r\n\r\n')
                assert until_closed(s) == b''
            # Every request is answered while the dead worker is replaced.
            for _ in range(8): assert get(server, '/') == (200, b'Hello, World!')
        time.sleep(1.2)
        now = settled_children(server.process.pid, 2)
        assert len(now) == 2 and set(now) != set(workers), (workers, now)
        output = server.stop()
        assert output.count('neo: an HTTP worker exited; starting another') == 6, output
    print('  crashed workers are replaced and the accept turn moves on: PASS', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='neo-http-limits-') as tmp:
        binary = args.binary
        if binary is None:
            binary = Path(tmp) / 'limits'
            subprocess.run([str(ROOT / 'neoc.sh'), 'build', 'tests/fixtures/http_limits.neo', '--no-cache', '-o', str(binary)], cwd=ROOT, check=True)
        backends = (['io_uring'] if URING else []) + (['epoll', 'poll'] if sys.platform.startswith('linux') else ['kqueue'])
        for backend in backends:
            print(f'== {backend}', flush=True)
            with Server(binary, backend) as server:
                refusals(server); continues(server)
            timeouts(binary, backend); limit(binary, backend); addresses(binary, backend)
            if sys.platform.startswith('linux'): restarts(binary, backend)


if __name__ == '__main__': main()
