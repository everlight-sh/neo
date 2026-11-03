import socket, sys, time, threading
port, delay = int(sys.argv[1]), float(sys.argv[2])
l = socket.socket(); l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); l.bind(('127.0.0.1', port)); l.listen(1024)
time.sleep(delay)
resp = b'HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\nHello, World!'
def serve(c):
    try:
        data = b''
        while b'\r\n\r\n' not in data:
            chunk = c.recv(4096)
            if not chunk: return
            data += chunk
        c.sendall(resp); time.sleep(5)
    except OSError: pass
while True:
    c, _ = l.accept(); threading.Thread(target=serve, args=(c,), daemon=True).start()
