import socket, sys
port = int(sys.argv[1]); path = sys.argv[2] if len(sys.argv) > 2 else '/'
s = socket.create_connection(('127.0.0.1', port)); s.sendall(b'GET %s HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n' % path.encode())
data = b''
while b'\r\n\r\n' not in data: data += s.recv(65536)
h, rest = data.split(b'\r\n\r\n', 1)
cl = [int(l.split(b':')[1]) for l in h.split(b'\r\n') if l.lower().startswith(b'content-length')][0]
while len(rest) < cl: rest += s.recv(65536)
print(repr(h + b'\r\n\r\n'), len(h) + 4, 'header bytes +', cl, 'body')
