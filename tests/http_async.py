import sys,subprocess,socket,signal,time,http.client,os,concurrent.futures
from pathlib import Path
from http_handoff import free_port
import argparse
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--binary',type=Path);args=parser.parse_args()
binary=args.binary or ROOT/'build/http-async-check'
if not args.binary:subprocess.run([str(ROOT/'neoc.sh'),'build',str(ROOT/'tests/fixtures/async_http.neo'),'-o',str(binary)],check=True)
for workers in (1,2,4):
 for grace in (150,2000):
  port=free_port();p=subprocess.Popen([str(binary),str(port),str(grace)],env={**os.environ,'NEO_THREADS':str(workers)},stderr=subprocess.PIPE,stdout=subprocess.DEVNULL,text=True,start_new_session=True)
  sockets=[]
  try:
   assert p.stderr.readline().startswith('neo: serving')
   for _ in range(32):
    s=socket.create_connection(('127.0.0.1',port));s.settimeout(4);s.sendall(b'GET /wait HTTP/1.1\r\nHost: localhost\r\n\r\n');wire=b''
    while b'Shell ready' not in wire:wire+=s.recv(4096)
    assert b'deferred fragment' not in wire;sockets.append((s,wire))
   start=time.monotonic()
   for _ in range(30):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=2);c.request('GET','/fast');r=c.getresponse();assert r.status==200 and r.read()==b'FAST';c.close()
   assert time.monotonic()-start<.25,time.monotonic()-start
   p.send_signal(signal.SIGTERM);begin=time.monotonic()
   for s,wire in sockets:
    while data:=s.recv(65536):wire+=data
    if grace>1000:assert wire.endswith(b'0\r\n\r\n') and b'Second deferred' in wire,wire[-100:]
    else:assert not wire.endswith(b'0\r\n\r\n'),wire[-100:]
    s.close()
   assert p.wait(timeout=4)==0,p.stderr.read()
   assert time.monotonic()-begin<2 if grace>1000 else time.monotonic()-begin<.75
   print('PASS',workers,'workers grace',grace,'elapsed',time.monotonic()-begin,flush=True)
  finally:
   for s,_ in sockets:s.close()
   if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
