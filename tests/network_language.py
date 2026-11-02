#!/usr/bin/env python3
"""Independent UDP/TCP protocol peers; no network service or TLS library runtime."""
import contextlib
import json
import os
from pathlib import Path
import shlex
import socket
import struct
import subprocess
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))


def dns_answer(query,case):
    question=query[12:];count=2 if case=='cname' else 1
    header=query[:2]+b'\x81\x80'+struct.pack('!HHHH',1,count,0,0)
    owner=b'\xc0\x0c'
    if case=='cycle':owner=struct.pack('!H',0xc000+12+len(question))
    answer=owner+struct.pack('!HHIH',1,1,60,4)+bytes([203,0,113,7])
    if case=='cname':
        name=b'\x05alias\xc0\x0c';offset=12+len(question)+12
        answer=b'\xc0\x0c'+struct.pack('!HHIH',5,1,60,len(name))+name+struct.pack('!H',0xc000+offset)+answer[2:]
    wire=header+question+answer
    if case=='id':wire=bytes([wire[0]^1])+wire[1:]
    if case=='question':wire=wire.replace(b'test',b'evil',1)
    return wire


@contextlib.contextmanager
def dns_peer(case):
    tcp=socket.socket();tcp.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);tcp.bind(('127.0.0.1',0));tcp.listen();tcp.settimeout(3)
    udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);port=tcp.getsockname()[1];udp.bind(('127.0.0.1',port));udp.settimeout(3);errors=[]
    def serve():
        try:
            query,peer=udp.recvfrom(16384);wire=dns_answer(query,case)
            if case=='timeout':return
            if case.startswith('tcp'):
                udp.sendto(query[:2]+b'\x83\x80'+struct.pack('!HHHH',1,0,0,0)+query[12:],peer)
                conn,_=tcp.accept()
                with conn:
                    conn.settimeout(2);request=b''
                    while len(request)<2 or len(request)<int.from_bytes(request[:2],'big')+2:request+=conn.recv(4096)
                    assert request[2:]==query
                    response=struct.pack('!H',len(wire))+wire
                    if case=='tcp-close':response=response[:20]
                    if case=='tcp-timeout':time.sleep(.5);return
                    for at in range(0,len(response),3):conn.sendall(response[at:at+3]);time.sleep(.0002)
            else:udp.sendto(wire,peer)
        except Exception as ex:errors.append(ex)
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    try:yield port
    finally:
        thread.join(4);udp.close();tcp.close();assert not thread.is_alive();assert not errors,errors


@contextlib.contextmanager
def http_peer(wire,method='GET',hold=False,gate=None,body=None):
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(3);errors=[]
    def serve():
        try:
            conn,_=listener.accept()
            with conn:
                conn.settimeout(3);request=b''
                while b'\r\n\r\n' not in request:request+=conn.recv(4096)
                head,payload=request.split(b'\r\n\r\n',1)
                assert head.startswith(method.encode()+b' /test HTTP/1.1\r\n'),head
                while len(payload)<7:payload+=conn.recv(4096)
                assert payload==b'payload'
                try:
                    if body is not None:
                        conn.sendall(wire)
                        for at in range(0,len(body),8192):conn.sendall(body[at:at+8192])
                    elif gate is not None:
                        # Force coalesced first data: acknowledgement must be
                        # emitted before attempting the next blocking read.
                        conn.sendall(wire)
                    else:
                        for at in range(0,len(wire),3):conn.sendall(wire[at:at+3]);time.sleep(.0001)
                    if gate is not None:
                        assert gate.wait(2),'client buffered the whole streaming response before returning a chunk'
                        conn.sendall(b'last')
                    if hold:time.sleep(.5)
                except (BrokenPipeError,ConnectionResetError):pass
        except Exception as ex:errors.append(ex)
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    try:yield listener.getsockname()[1]
    finally:
        thread.join(4);listener.close();assert not thread.is_alive();assert not errors,errors


def main():
    with tempfile.TemporaryDirectory(prefix='neo-net-language-') as tmp:
        binaries={}
        for name in ('dns','http'):
            binary=Path(tmp)/name
            result=subprocess.run(['python3','-m','neoc','build','tests/fixtures/language_'+name+'.neo','-o',str(binary),'--report'],cwd=ROOT,capture_output=True,text=True)
            assert result.returncode==0,(json.loads(result.stdout).get('errors'),result.stderr);binaries[name]=binary
        def run(name,args):
            start=time.monotonic();r=subprocess.run(RUNNER+[str(binaries[name]),*map(str,args)],capture_output=True,text=True,timeout=5)
            assert r.returncode==0,(r.stdout,r.stderr);return r.stdout,time.monotonic()-start
        for case,expected in [('valid','203.0.113.7'),('cname','203.0.113.7'),('id','error:1'),('question','error:1'),('cycle','error:2'),('tcp','203.0.113.7'),('tcp-close','error:5'),('tcp-timeout','error:110'),('timeout','error:110')]:
            with dns_peer(case) as port:
                result,elapsed=run('dns',[port]);assert result.strip()==expected,(case,result);assert elapsed<2,(case,elapsed)
        print('PASS DNS: UDP, compressed CNAME, ID/question validation, pointer cycles, fragmented TCP fallback, truncation and monotonic deadlines',flush=True)
        for method in ('GET','POST','PUT','PATCH','DELETE','OPTIONS','HEAD'):
            wire=b'HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\n'+(b'' if method=='HEAD' else b'hello')
            with http_peer(wire,method,hold=True) as port:
                result,elapsed=run('http',[port,0,method]);assert result==('200 \n' if method=='HEAD' else '200 hello\n'),(method,result)
                assert elapsed<.45,('waited for EOF despite response framing',method,elapsed)
        cases=[(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2\r\nhe\r\n3\r\nllo\r\n0\r\nX-T: a\r\n\r\n','200 hello\n'),
            (b'HTTP/1.0 200 OK\r\n\r\nhello','200 hello\n'),
            (b'HTTP/1.1 100 Continue\r\n\r\nHTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello','200 hello\n'),
            (b'HTTP/1.1 200 OK\r\nContent-Length: 9\r\n\r\nhello','error:5\n'),
            (b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n','error:1\n'),
            (b'HTTP/1.1 200 OK\r\nBad Header: a\r\n\r\n','error:1\n'),
            (b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabcXX0\r\n\r\n','error:1\n')]
        for wire,expected in cases:
            with http_peer(wire) as port:assert run('http',[port,0])[0]==expected,(wire,expected)
        body=bytes(range(256))*16384
        with http_peer(b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n',body=body) as port:
            assert run('http',[port,1])[0]==f'200 {len(body)} {sum(body)}\n'
        gate=threading.Event()
        with http_peer(b'HTTP/1.1 200 OK\r\nContent-Length: 9\r\n\r\nfirst',gate=gate) as port:
            child=subprocess.Popen(RUNNER+[str(binaries['http']),str(port),'2'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            assert child.stdout.readline()=='chunk\n';gate.set();out,err=child.communicate(timeout=5)
            assert child.returncode==0 and out==f'200 9 {sum(b"firstlast")}\n',(out,err)
        print('PASS HTTP: seven methods, HEAD, fixed/chunked/EOF framing, 1xx, malicious framing, early chunks and 4 MiB streamed through a bounded buffer',flush=True)


if __name__=='__main__':main()
