#!/usr/bin/env python3
"""Native callback transports against independent TCP/TLS/SSE peers."""
import contextlib, os, socket, ssl, subprocess, tempfile, threading, time
from pathlib import Path
from agent_codecs import ROOT,RUNNER,build
from tls_language import certificates

@contextlib.contextmanager
def peer(handler,context=None):
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(5);errors=[];stop=threading.Event()
    def serve():
        try:
            connection,_=listener.accept()
            with connection:
                connection.settimeout(5)
                if context:
                    with context.wrap_socket(connection,server_side=True) as secure:handler(secure,stop)
                else:handler(connection,stop)
        except Exception as exc:errors.append(exc)
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    try:yield listener.getsockname()[1]
    finally:
        stop.set();thread.join(8);listener.close();assert not thread.is_alive();assert not errors,errors

def main():
    with tempfile.TemporaryDirectory(prefix='neo-agent-net-') as tmp:
        root=Path(tmp);transport=root/'transport';cancellation=root/'cancel'
        build('tests/fixtures/agent_transport.neo',transport);build('tests/fixtures/socket_cancellation.neo',cancellation)
        def run(binary,args):
            p=subprocess.run(RUNNER+[str(binary),*map(str,args)],capture_output=True,timeout=12)
            assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
            return p.stdout
        def first(connection,stop):connection.sendall(b'first chunk');stop.wait(2)
        with peer(first) as port:assert run(cancellation,[port])==b'first chunk'
        def stalled(connection,stop):stop.wait(3)
        with peer(stalled) as port:
            before=time.monotonic();assert run(cancellation,[port,'cancel'])==b'error:125';assert time.monotonic()-before<1.5
        print('PASS first-read preservation and cross-process cancellation of stalled socket',flush=True)
        body='id: 1\r\ndata: héllo\r\n\r\nevent: tool\ndata: second\n\n'.encode()
        def http(connection,stop):
            request=b''
            while b'\r\n\r\n' not in request:request+=connection.recv(8192)
            header,payload=request.split(b'\r\n\r\n',1)
            assert b'POST /stream HTTP/1.1' in header and b'Authorization: Bearer test-token' in header and b'Content-Type: application/json' in header,header
            while len(payload)<15:payload+=connection.recv(8192)
            assert payload==b'{"question":42}',payload
            connection.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nTransfer-Encoding: chunked\r\n\r\n')
            for at in range(0,len(body),3):
                chunk=body[at:at+3];connection.sendall(('%x\r\n'%len(chunk)).encode()+chunk+b'\r\n')
            connection.sendall(b'0\r\n\r\n')
        with peer(http) as port:assert run(transport,[port])==body
        certificates(root)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_3;context.maximum_version=ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(str(root/'leaf.pem'),str(root/'leaf.key'));context.set_alpn_protocols(['http/1.1'])
        with peer(http,context) as port:assert run(transport,[port,root/'ca.der'])=='héllo\nsecond\n'.encode()
        print('PASS authorization/custom headers, bounded HTTP chunk decoding and fragmented SSE over TCP and authenticated TLS 1.3',flush=True)
if __name__=='__main__':main()
