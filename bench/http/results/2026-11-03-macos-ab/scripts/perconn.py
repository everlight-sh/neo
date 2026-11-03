#!/usr/bin/env python3
"""64 keep-alive connections, one request in flight each; per-connection latency. usage: perconn.py PORT PATH SECONDS"""
import selectors, socket, sys, time, statistics
port, path, seconds = int(sys.argv[1]), sys.argv[2], float(sys.argv[3])
req = f'GET {path} HTTP/1.1\r\nHost: x\r\n\r\n'.encode()
sel = selectors.DefaultSelector(); conns = []
for i in range(64):
    s = socket.create_connection(('127.0.0.1', port)); s.setblocking(False)
    conns.append(s); sel.register(s, selectors.EVENT_READ, [i, b'', time.monotonic(), []])
for s in conns:
    sel.get_key(s).data[2] = time.monotonic(); s.send(req)
end = time.monotonic() + seconds
while time.monotonic() < end:
    for key, _ in sel.select(1):
        st = key.data; st[1] += key.fileobj.recv(65536)
        h = st[1].find(b'\r\n\r\n')
        if h < 0: continue
        n = int([l for l in st[1][:h].split(b'\r\n') if l.lower().startswith(b'content-length')][0].split(b':')[1])
        if len(st[1]) < h + 4 + n: continue
        st[1] = st[1][h + 4 + n:]; now = time.monotonic(); st[3].append((now - st[2]) * 1000); st[2] = now; key.fileobj.send(req)
lat = [(key.data[0], key.data[3]) for key in sel.get_map().values()]
allv = sorted(v for _, l in lat for v in l)
print(f'requests {len(allv)}  p50 {allv[len(allv)//2]:.1f} ms  p99 {allv[int(len(allv)*.99)]:.1f} ms  max {allv[-1]:.1f} ms')
per = sorted(lat)
print('per connection (index: count, max ms):', '  '.join(f'{i}:{len(l)},{max(l):.0f}' for i, l in per if l))
