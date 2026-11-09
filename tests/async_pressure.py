"""Bounded streaming, fairness under backpressure, admission and shutdown."""
import argparse,http.client,json,os,signal,socket,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def port():
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]
def call(number,path):
    connection=http.client.HTTPConnection('127.0.0.1',number,timeout=4)
    try:connection.request('GET',path);r=connection.getresponse();return r.status,r.read()
    finally:connection.close()
def open_request(number,path):
    connection=socket.create_connection(('127.0.0.1',number),timeout=4);connection.settimeout(4);connection.sendall(f'GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n'.encode());wire=b''
    while b'SHELL' not in wire:
        part=connection.recv(4096);assert part,wire;wire+=part
    return connection,wire
def zero(number):
    deadline=time.monotonic()+3
    while time.monotonic()<deadline:
        value=json.loads(call(number,'/stats')[1])
        if all(n==0 for n in value.values()):return
        time.sleep(.005)
    raise AssertionError(value)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binary',type=Path,default=ROOT/'build/async-pressure');args=parser.parse_args();number=port();sockets=[]
    process=subprocess.Popen([str(args.binary.resolve()),str(number)],env={**os.environ,'NEO_THREADS':'1'},stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:
        assert process.stderr.readline().startswith('neo: serving');zero(number)
        assert call(number,'/handoff')==(200,b'SHELLCHILD')
        assert call(number,'/queued-timeout')==(200,b'SHELLTIMEOUT');zero(number)
        assert call(number,'/rollback')==(503,b'ROLLBACK');zero(number)
        status,body=call(number,'/root-fail');assert status==503 and b'CHILD' not in body,(status,body);zero(number)
        print('PASS root I/O-to-stream handoff, partial admission rollback, and root failure before headers',flush=True)
        for _ in range(8):sockets.append(open_request(number,'/large')[0])
        time.sleep(.05);began=time.monotonic()
        for _ in range(30):assert call(number,'/fast')==(200,b'FAST')
        elapsed=time.monotonic()-began;assert elapsed<.3,elapsed
        for sock in sockets:sock.close()
        sockets.clear();zero(number);print('PASS 8 backpressured 8 MiB streams do not stall fast requests',elapsed,flush=True)
        status,body=call(number,'/large');assert status==200 and body.startswith(b'SHELL') and body.endswith(b'END') and len(body)==5+512*16384+3,len(body)
        zero(number)
        for _ in range(256):sockets.append(open_request(number,'/hold')[0])
        stats=json.loads(call(number,'/stats')[1]);assert stats['live']==256,stats
        assert call(number,'/hold')[0]==503
        for sock in sockets:sock.close()
        sockets.clear();zero(number);print('PASS exact 256-task admission bound and cancellation of every admitted task',flush=True)
        for _ in range(16):sockets.append(open_request(number,'/large?short=1')[0])
        time.sleep(.4);zero(number)
        for sock in sockets:sock.close()
        sockets.clear();print('PASS slow-reader deadlines release task and result memory',flush=True)
        for _ in range(16):sockets.append(open_request(number,'/hold')[0])
        start=time.monotonic();process.send_signal(signal.SIGTERM)
        for sock in sockets:
            while sock.recv(65536):pass
            sock.close()
        sockets.clear();assert process.wait(timeout=3)==0;assert time.monotonic()-start<1
        print('PASS graceful shutdown cancels held socket/timer continuations by deadline',flush=True)
    finally:
        for sock in sockets:sock.close()
        if process.poll() is None:os.killpg(process.pid,signal.SIGKILL);process.wait()
if __name__=='__main__':main()
