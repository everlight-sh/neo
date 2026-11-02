#!/usr/bin/env python3
"""std:https_client's keep-alive HttpClient against a local HTTP/1.1 server,
over TCP and TLS 1.3: reuse, a server-requested close, an idle connection the
server closes without saying so (a GET is sent again on a new connection, a
POST is not), a body over the limit, and a chunked body."""
import socket, ssl, subprocess, tempfile, threading
from contextlib import contextmanager
from pathlib import Path
from agent_codecs import RUNNER, build
from tls_language import certificates

# status body, or error:CODE, then the connections the client has opened
EXPECTED = ['200 a 1', '200 b 1', '200 chunked! 1', '200 close 1', '200 a 2', '200 drop 2', '200 b 3', '200 drop 3',
            None, '200 3 4', 'error:27 4', '200 a 5']
# The POST over the silently closed connection fails at the write or at the read.
DEAD_POST = {'error:5 3', 'error:32 3', 'error:104 3'}


def read_request(connection, buffered):
    """(method, path, body, rest), or None when the client is gone."""
    try:
        while b'\r\n\r\n' not in buffered:
            chunk = connection.recv(65536)
            if not chunk: return None
            buffered += chunk
        head, rest = buffered.split(b'\r\n\r\n', 1)
        lines = head.decode().split('\r\n'); method, path, _ = lines[0].split(' ')
        length = next((int(line.split(':', 1)[1]) for line in lines[1:] if line.lower().startswith('content-length:')), 0)
        while len(rest) < length:
            chunk = connection.recv(65536)
            if not chunk: return None
            rest += chunk
        return method, path, rest[:length], rest[length:]
    except (ConnectionError, ssl.SSLError): return None


def reply(connection, body, extra=b''):
    connection.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: %d\r\n%s\r\n' % (len(body), extra) + body)


def handle(connection):
    buffered = b''
    with connection:
        while (request := read_request(connection, buffered)) is not None:
            method, path, body, buffered = request
            if path == '/chunked': connection.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n4\r\nchun\r\n4\r\nked!\r\n0\r\n\r\n')
            elif path == '/close': reply(connection, b'close', b'Connection: close\r\n'); return
            elif path == '/drop': reply(connection, b'drop'); return  # as an idle timeout would, with no warning
            elif path == '/big': reply(connection, b'x' * 5000)
            elif path == '/post': assert method == 'POST', method; reply(connection, str(len(body)).encode())
            else: reply(connection, path[1:].encode())


@contextmanager
def server(context):
    """(port, accepted connections)"""
    listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(); listener.settimeout(0.2)
    accepted, errors, stop = [], [], threading.Event()
    def run(connection):
        try: handle(context.wrap_socket(connection, server_side=True) if context else connection)
        except Exception as exc: errors.append(exc)
    def serve():
        while not stop.is_set():
            try: connection, _ = listener.accept()
            except TimeoutError: continue
            connection.settimeout(5); accepted.append(connection)
            threading.Thread(target=run, args=(connection,), daemon=True).start()
    thread = threading.Thread(target=serve, daemon=True); thread.start()
    try: yield listener.getsockname()[1], accepted
    finally:
        stop.set(); thread.join(2); listener.close(); assert not errors, errors


def main():
    with tempfile.TemporaryDirectory(prefix='neo-keepalive-') as tmp:
        root = Path(tmp); binary = root / 'keepalive'
        build('tests/fixtures/http_keepalive.neo', binary)
        certificates(root)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(str(root / 'leaf.pem'), str(root / 'leaf.key')); context.set_alpn_protocols(['http/1.1'])
        for name, tls, extra in [('TCP', None, []), ('TLS 1.3', context, [root / 'ca.der'])]:
            with server(tls) as (port, accepted):
                p = subprocess.run(RUNNER + [str(binary), str(port), *map(str, extra)], capture_output=True, timeout=60)
                assert p.returncode == 0, (p.returncode, p.stdout, p.stderr)
                lines = p.stdout.decode().splitlines()
                assert len(lines) == len(EXPECTED), lines
                for got, want in zip(lines, EXPECTED):
                    assert (got in DEAD_POST) if want is None else got == want, (got, want, lines)
                assert len(accepted) == 5, len(accepted)
            print(f'PASS keep-alive over {name}: 12 requests on 5 connections; reuse, server close, '
                  'silent close retried for GET and not for POST, body limit, chunked body', flush=True)


if __name__ == '__main__': main()
