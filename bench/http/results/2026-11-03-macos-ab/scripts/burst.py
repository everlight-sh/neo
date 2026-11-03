#!/usr/bin/env python3
"""Connect N sockets at once, then one request on each; count failures. usage: burst.py PORT N"""
import selectors, socket, sys, time, errno
port, n = int(sys.argv[1]), int(sys.argv[2])
socks = []
for _ in range(n):
    s = socket.socket(); s.setblocking(False)
    e = s.connect_ex(('127.0.0.1', port)); assert e in (0, errno.EINPROGRESS), e
    socks.append(s)
sel = selectors.DefaultSelector()
for i, s in enumerate(socks): sel.register(s, selectors.EVENT_WRITE, i)
buf = {i: b'' for i in range(n)}; done = set(); failed = {}; closed_data = []
deadline = time.time() + 20
while len(done) + len(failed) < n and time.time() < deadline:
    for key, ev in sel.select(1):
        i, s = key.data, key.fileobj
        if ev & selectors.EVENT_WRITE:
            err = s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if err: failed[i] = errno.errorcode.get(err, err); sel.unregister(s); continue
            try: s.send(b'GET / HTTP/1.1\r\nHost: x\r\n\r\n')
            except OSError as e: failed[i] = e.strerror; sel.unregister(s); continue
            sel.modify(s, selectors.EVENT_READ, i)
        else:
            try: chunk = s.recv(4096)
            except OSError as e: failed[i] = e.strerror; sel.unregister(s); continue
            if not chunk: failed[i] = 'closed'; closed_data.append(buf[i][:120]); sel.unregister(s); continue
            buf[i] += chunk
            if buf[i].endswith(b'Hello, World!'): done.add(i); sel.unregister(s)
print(f'ok {len(done)}/{n} failed {len(failed)} {sorted(set(failed.values()))} pending {n-len(done)-len(failed)}')
from collections import Counter
if failed: print('  kinds', dict(Counter(failed.values())), 'closed samples', Counter(closed_data).most_common(3))
for s in socks: s.close()
