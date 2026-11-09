"""Prepared native callbacks: state reuse, eviction under backpressure, cleanup."""
import argparse,http.client,json,os,signal,socket,subprocess,time
from pathlib import Path
from http_handoff import free_port
parser=argparse.ArgumentParser();parser.add_argument('--binary',type=Path,required=True);args=parser.parse_args()
def call(port,path):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=10);c.request('GET',path);r=c.getresponse();body=r.read();status=r.status;c.close();return status,body
def quiet(port):
    until=time.monotonic()+2
    while time.monotonic()<until:
        if json.loads(call(port,'/stats')[1])['subscribers']==0:return
        time.sleep(.01)
    raise AssertionError('Retained callback after disconnect')
for workers in (1,2):
    port=free_port();connections=[]
    p=subprocess.Popen([str(args.binary.resolve()),str(port)],env={**os.environ,'NEO_THREADS':str(workers)},stderr=subprocess.PIPE,stdout=subprocess.DEVNULL,text=True,start_new_session=True)
    try:
        assert p.stderr.readline().startswith('neo: serving')
        for _ in range(8):assert call(port,'/frames')==(200,b'SHELL'+b'A'*15+b'END')
        assert call(port,'/late-wake')==(200,b'SHELL'+b'A'*15+b'END')
        quiet(port)
        for _ in range(4):
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=10);c.request('GET','/large');r=c.getresponse();assert r.status==200;connections.append((c,r))
        time.sleep(.3);began=time.monotonic()
        for _ in range(30):assert call(port,'/fast')==(200,b'FAST')
        assert time.monotonic()-began<.3
        assert call(port,'/evict')==(200,b'EVICTED')
        for c,r in connections:
            body=r.read();assert body==b'SHELL'+b'A'*(128*32768)+b'END',(len(body),body[-50:]);c.close()
        connections.clear();quiet(port)
        for _ in range(8):assert call(port,'/frames')==(200,b'SHELL'+b'A'*15+b'END')
        for _ in range(4):
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=10);c.request('GET','/large');r=c.getresponse();connections.append((c,r))
        for c,r in connections:r.close();c.close()
        connections.clear();quiet(port)
        began=time.monotonic();p.send_signal(signal.SIGTERM);assert p.wait(timeout=2)==0;assert time.monotonic()-began<1
        print(f'PASS {workers} workers: persistent state/reset, prepared fast writes, 4 backpressured 4 MiB bodies across cache eviction, responsive fast requests and disconnect/shutdown cleanup',flush=True)
    finally:
        for c,r in connections:r.close();c.close()
        if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
