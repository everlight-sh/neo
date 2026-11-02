#!/usr/bin/env python3
"""A stopped HTTP server releases its port at once, so a restart can bind it.

For each Linux backend (io_uring with one and two workers, epoll): start the example server, hold
eight keep-alive connections open after one request each, stop it with
SIGTERM, then (1) measure how long until the port can be bound again and
(2) start a second server on that port immediately and check it serves.

  python3 tests/listener_release.py [path/to/http-server]

Without a path the example server (examples/http.neo) is built first.
"""
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKENDS = [("io_uring", {}), ("io_uring, 2 workers", {"NEO_THREADS": "2"}), ("epoll", {"NEO_HTTP_URING": "0"})]


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close(); return port


def start(binary, port, env):
    proc = subprocess.Popen([binary, str(port)], env={**os.environ, "NEO_THREADS": "1", **env},
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True)
    for _ in range(200):
        if proc.poll() is not None:
            return proc
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close(); return proc
        except OSError:
            time.sleep(0.02)
    return proc


def hold_connections(port, count=8):
    held = []
    for _ in range(count):
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        s.sendall(b"GET /page/3 HTTP/1.1\r\nHost: x\r\n\r\n")
        data = b""
        while b"\r\n\r\n" not in data:
            data += s.recv(65536)
        held.append(s)
    return held


def stop(proc):
    os.killpg(proc.pid, signal.SIGTERM); proc.wait()


def bindable_after(port, limit=10.0):
    started = time.monotonic()
    while time.monotonic() - started < limit:
        s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port)); s.listen(); return time.monotonic() - started
        except OSError:
            time.sleep(0.002)
        finally:
            s.close()
    return None


def restart_serves(binary, port, env):
    proc = start(binary, port, env)
    try:
        if proc.poll() is not None:
            return False, proc.stderr.read().decode(errors="replace").strip()[-120:]
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        s.sendall(b"GET /page/3 HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        data = b""
        while chunk := s.recv(65536):
            data += chunk
        return data.startswith(b"HTTP/1.1 200"), data[:40]
    except OSError as e:
        return False, repr(e)
    finally:
        if proc.poll() is None:
            stop(proc)


def main():
    binary = sys.argv[1] if len(sys.argv) > 1 else None
    if binary is None:
        binary = str(Path(tempfile.mkdtemp(prefix="listener-release-")) / "http")
        subprocess.run([str(ROOT / "neoc.sh"), "build", "examples/http.neo", "-o", binary], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL)
    failures = 0
    for name, env in BACKENDS:
        for trial in range(3):
            port = free_port(); proc = start(binary, port, env)
            held = hold_connections(port); stop(proc)
            free_in = bindable_after(port)
            for s in held: s.close()
            port2 = free_port(); proc = start(binary, port2, env)
            held = hold_connections(port2); stop(proc)
            served, detail = restart_serves(binary, port2, env)
            for s in held: s.close()
            ok = free_in is not None and free_in < 0.05 and served
            failures += not ok
            took = "never (10 s)" if free_in is None else f"{free_in * 1000:.1f} ms"
            print(f"{'PASS' if ok else 'FAIL'} {name} #{trial}: port bindable after {took}; restart serves: {served} {detail!r}", flush=True)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
