#!/usr/bin/env python3
"""Protocol edge cases against a running server on PORT: pipelining, a request
split across many tiny writes, a POST body that must be skipped, and
Connection: close."""
import re, socket, sys, time
def codes_in(buf): return re.findall(rb"HTTP/1\.1 (\d{3})", buf)   # bodies have no trailing CRLF, so scan, don't split
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 18080

def recv_responses(s, n, timeout=2.0, until_close=False):
    """Read until n status lines arrived (and, if until_close, until the peer closes). Returns (buf, closed)."""
    s.settimeout(timeout); buf = b""; t0 = time.time(); closed = False
    while time.time() - t0 < timeout:
        if buf.count(b"HTTP/1.1 ") >= n and not until_close:
            # drain whatever is already queued so the next test starts clean
            s.settimeout(0.2)
            try:
                while True:
                    chunk = s.recv(65536)
                    if not chunk: closed = True; break
                    buf += chunk
            except socket.timeout:
                pass
            return buf, closed
        try:
            chunk = s.recv(65536)
        except socket.timeout:
            break
        if not chunk: closed = True; break
        buf += chunk
    return buf, closed

ok = True
# 1. three pipelined requests in one write; last one closes
s = socket.create_connection(("127.0.0.1", PORT))
s.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n\r\nGET /a HTTP/1.1\r\nHost: x\r\n\r\nGET / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
r, closed = recv_responses(s, 3, until_close=True)
codes = codes_in(r)
print("pipelined   :", codes, "closed by server:", closed)
ok &= codes == [b"200", b"404", b"200"] and closed
s.close()
# 2. request delivered one byte at a time
s = socket.create_connection(("127.0.0.1", PORT))
for b in b"GET / HTTP/1.1\r\nHost: x\r\n\r\n":
    s.sendall(bytes([b])); time.sleep(0.001)
r, _ = recv_responses(s, 1)
print("byte-by-byte:", r.split(b"\r\n")[0], r.endswith(b"Hello, World!"))
ok &= r.endswith(b"Hello, World!")
# 3. POST with a body, then a GET on the same connection: body must not be parsed as a request
s.sendall(b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\n\r\nhelloGET / HTTP/1.1\r\nHost: x\r\n\r\n")
r, _ = recv_responses(s, 2)
codes = codes_in(r)
print("post+get    :", codes, "(first code is the server's choice for POST; second must be 200)")
ok &= len(codes) == 2 and codes[1] == b"200"
s.close()
# 4. many concurrent idle connections stay open while others are served
idle = [socket.create_connection(("127.0.0.1", PORT)) for _ in range(300)]
s = socket.create_connection(("127.0.0.1", PORT))
s.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
r, _ = recv_responses(s, 1)
print("300 idle    :", r.split(b"\r\n")[0])
ok &= r.startswith(b"HTTP/1.1 200")
for c in idle: c.close()
s.close()
print("ALL OK" if ok else "FAILURES")
sys.exit(0 if ok else 1)
