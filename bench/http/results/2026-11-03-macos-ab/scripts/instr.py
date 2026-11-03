#!/usr/bin/env python3
"""Instructions retired / cycles per request for a single-worker server (macOS /usr/bin/time -l).

usage: instr.py BINARY PATH N [ENV=V ...]   (PATH may be POST:/nbody)"""
import os, re, socket, subprocess, sys, time
binary, path, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
env = dict(os.environ, NEO_THREADS='1', AXON_THREADS='1', TOKIO_WORKER_THREADS='1', GOMAXPROCS='1')
for kv in sys.argv[4:]:
    k, v = kv.split('=', 1); env[k] = v
with socket.socket() as s:
    s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]
p = subprocess.Popen(['/usr/bin/time', '-l', binary, str(port)], env=env, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
for _ in range(200):
    try: c = socket.create_connection(('127.0.0.1', port)); break
    except OSError: time.sleep(.02)
if path.startswith('POST:'):
    body = b'{"n":256,"steps":4}'
    req = b'POST ' + path[5:].encode() + b' HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body
else: req = b'GET ' + path.encode() + b' HTTP/1.1\r\nHost: x\r\n\r\n'
buf = b''
def one():
    global buf
    c.sendall(req)
    while True:
        i = buf.find(b'\r\n\r\n')
        if i >= 0:
            m = re.search(rb'(?i)content-length:\s*(\d+)', buf[:i])
            need = i + 4 + int(m[1])
            if len(buf) >= need: buf = buf[need:]; return
        chunk = c.recv(65536)
        assert chunk
        buf += chunk
for _ in range(n): one()
c.close()
child = int(subprocess.run(['pgrep', '-P', str(p.pid)], capture_output=True, text=True).stdout.split()[0])
os.kill(child, 15); _, err = p.communicate()
ins = int(re.search(r'(\d+)\s+instructions retired', err)[1]); cyc = int(re.search(r'(\d+)\s+cycles elapsed', err)[1])
faults = int(re.search(r'(\d+)\s+page reclaims', err)[1]); u, sy = map(float, re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys', err).groups()[1:]); print(f'{os.path.basename(binary):12s} {path:16s} n={n}  instructions/req {ins/n:12,.0f}  cycles/req {cyc/n:12,.0f}  user {u*1e6/n:7.1f} us  sys {sy*1e6/n:6.1f} us  page reclaims/req {faults/n:7.1f}')
