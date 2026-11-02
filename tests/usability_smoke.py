#!/usr/bin/env python3
"""Real application, crash/restart, failure and differential JSON checks."""
import argparse
import concurrent.futures
from contextlib import contextmanager
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import platform
from pathlib import Path
import random
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
BUILD_ID=os.environ.get('NEO_TARGET') or platform.system().lower()+'-'+platform.machine()
OUT=ROOT/'.kernel-build/usability/test'/BUILD_ID
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))

def build(name,source):
    OUT.mkdir(parents=True,exist_ok=True);binary=OUT/name
    result=subprocess.run([sys.executable,'-m','neoc','build',source,'-o',str(binary),'--report'],cwd=ROOT,capture_output=True,text=True)
    (OUT/(name+'-build.json')).write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout[-8000:]+result.stderr
    report=json.loads(result.stdout);assert not report['undefined_symbols'],report['undefined_symbols']
    return binary

def request(port,method,path,body=None,raw=False):
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=15)
    try:
        connection.request(method,path,body if raw else json.dumps(body,ensure_ascii=False).encode() if body is not None else None,{'Content-Type':'application/json'})
        response=connection.getresponse();data=response.read()
        assert int(response.getheader('Content-Length'))==len(data)
        return response.status,data
    finally:connection.close()

def free_port():
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

@contextmanager
def server(binary,env,workers=4,affinity=None):
    port=free_port()
    log=tempfile.TemporaryFile()
    child=subprocess.Popen(RUNNER+[str(binary),str(port)],env={**os.environ,'NEO_THREADS':str(workers),**env},stdout=log,stderr=log,start_new_session=True,
        preexec_fn=(lambda:os.sched_setaffinity(0,affinity)) if affinity else None)
    try:
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            assert child.poll() is None,'server exited'
            try:request(port,'GET','/');break
            except OSError:time.sleep(.02)
        else:raise AssertionError('server startup timed out')
        yield port,child
    finally:
        if child.poll() is None:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        log.seek(0);(OUT/(binary.name+'-server.log')).write_bytes(log.read());log.close()

def json_cli(binary):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp);source=path/'input.json';output=path/'output.json'
        rng=random.Random(8401)
        rows=[{'id':i,'name':f'café 🚀 <{i}>','score':rng.randrange(-100,100)} for i in range(120)]
        source.write_text(json.dumps(rows,ensure_ascii=False))
        result=subprocess.run(RUNNER+[str(binary),str(source),str(output),'10'],capture_output=True)
        assert result.returncode==0 and result.stdout==b'',result.stderr
        assert json.loads(output.read_text())==sorted([r for r in rows if r['score']>=10],key=lambda r:r['score'])
        for contents in ('[1,]','{}','[{"id":1,"name":2,"score":3}]','[{"id":9223372036854775808,"name":"x","score":3}]'):
            source.write_text(contents);output.write_text('unchanged')
            r=subprocess.run(RUNNER+[str(binary),str(source),str(output)],capture_output=True)
            assert r.returncode==2 and b'neo-json:' in r.stderr and output.read_text()=='unchanged'
        r=subprocess.run(RUNNER+[str(binary),str(path/'missing'),str(output)],capture_output=True)
        assert r.returncode==2 and b'open failed' in r.stderr
        source.write_text('[]');r=subprocess.run(RUNNER+[str(binary),str(source),str(path/'missing'/'out')],capture_output=True)
        assert r.returncode==2
    print('PASS JSON CLI: schema, stable sort/filter, Unicode, malformed data and recoverable file errors',flush=True)

def io_library(binary):
    with tempfile.TemporaryDirectory() as tmp:
        env=dict(os.environ);env.pop('NEO_TEST_UNSET_20261024',None)
        result=subprocess.run(RUNNER+[str(binary),str(Path(tmp)/'data')],env=env,capture_output=True,timeout=15)
        assert result.returncode==0 and result.stdout==b'',(result.returncode,result.stdout,result.stderr)
    print('PASS file append/read/errors, environment/argv, embedded-NUL rejection, clocks and sleep',flush=True)

def notes(binary):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'notes.log';env={'NEO_NOTES_FILE':str(path)}
        with server(binary,env) as (port,process):
            assert request(port,'GET','/api/notes')==(200,b'[]')
            status,body=request(port,'POST','/api/notes',{'title':'café 🚀 <script>alert("x")</script>'})
            assert status==201 and json.loads(body)['id']==1
            status,html=request(port,'GET','/')
            assert status==200 and b'&lt;script&gt;' in html and b'<script>' not in html
            assert request(port,'POST','/api/notes',b'{bad',True)[0]==400
            def create(i):
                status,body=request(port,'POST','/api/notes',{'title':f'parallel {i}'})
                assert status==201;return json.loads(body)['id']
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:ids=list(pool.map(create,range(30)))
            assert len(set(ids))==30 and set(ids)==set(range(2,32))
            assert request(port,'PUT','/api/notes/1',{'title':'updated 🚀'})[0]==200
            assert request(port,'DELETE','/api/notes/2')[0]==200
            status,body=request(port,'GET','/api/notes');expected=json.loads(body)
            assert status==200 and len(expected)==30
            os.killpg(process.pid,signal.SIGKILL);process.wait()
        with path.open('ab') as file:file.write(b'{"op":"put","id":999,"title":"torn')
        with server(binary,env) as (port,_):
            assert json.loads(request(port,'GET','/api/notes')[1])==expected
            status,body=request(port,'POST','/api/notes',{'title':'after recovery'})
            assert status==201 and json.loads(body)['id']==32
            assert request(port,'GET','/api/notes/999')[0]==404
        assert path.read_bytes().endswith(b'\n') and b'torn' not in path.read_bytes()
        with path.open('ab') as file:file.write(b'not-json\n')
        with server(binary,env) as (port,_):assert request(port,'GET','/api/notes')[0]==503
        with server(binary,{'NEO_NOTES_FILE':str(Path(tmp)/'missing'/'notes')}) as (port,_):assert request(port,'GET','/api/notes')[0]==503
    print('PASS notes: CRUD, escaped SSR, 30 concurrent writes, SIGKILL/restart, torn-tail repair, corruption and storage failure',flush=True)

def webhook(binary):
    attempts={};effects={};lock=threading.Lock()
    class Receiver(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args):pass
        def do_POST(self):
            body=self.rfile.read(int(self.headers['Content-Length']));key=self.headers['Idempotency-Key']
            with lock:attempts[key]=attempts.get(key,0)+1;number=attempts[key]
            if key=='timeout':time.sleep(.25)
            status=500 if key=='retry' and number<3 or key=='dead' or key=='resume' and number==1 else 200
            if status==200:
                with lock:effects.setdefault(key,json.loads(body))
            self.send_response(status);self.send_header('Content-Length','2');self.send_header('Connection','close');self.end_headers()
            try:self.wfile.write(b'ok')
            except (BrokenPipeError,ConnectionResetError):pass
    receiver=ThreadingHTTPServer(('127.0.0.1',0),Receiver);thread=threading.Thread(target=receiver.serve_forever,daemon=True);thread.start()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'queue.log'
            env={'NEO_WEBHOOK_FILE':str(path),'NEO_WEBHOOK_PORT':str(receiver.server_port),'NEO_WEBHOOK_TIMEOUT_MS':'80','NEO_WEBHOOK_RETRY_MS':'200','NEO_WEBHOOK_MAX_ATTEMPTS':'3'}
            with server(binary,env) as (port,process):
                for key in ('ok','retry','dead','timeout'):
                    assert request(port,'POST','/events',{'id':key,'payload':{'name':'café 🚀','key':key}})[0]==202
                def duplicate(_):return request(port,'POST','/events',{'id':'ok','payload':{'changed':True}})
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:duplicates=list(pool.map(duplicate,range(12)))
                assert all(s==202 and json.loads(b)['duplicate'] for s,b in duplicates)
                deadline=time.monotonic()+25
                while time.monotonic()<deadline:
                    status,body=request(port,'GET','/jobs');jobs={j['id']:j for j in json.loads(body)}
                    if len(jobs)==4 and all(j['status'] in ('done','failed') for j in jobs.values()):break
                    time.sleep(.03)
                else:raise AssertionError(('jobs did not finish',jobs))
                assert jobs['ok']['status']=='done' and jobs['retry']['status']=='done'
                assert jobs['retry']['attempts']==3 and jobs['dead']['status']=='failed' and jobs['timeout']['status']=='failed'
                assert attempts['ok']==1 and attempts['retry']==3 and attempts['dead']==3
                assert effects['ok']=={'name':'café 🚀','key':'ok'}
                expected=jobs
                assert request(port,'POST','/events',{'id':'resume','payload':{'pending':True}})[0]==202
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    pending={j['id']:j for j in json.loads(request(port,'GET','/jobs')[1])}['resume']
                    if pending['attempts']==1 and pending['status']=='pending' and attempts.get('resume')==1:break
                    time.sleep(.005)
                else:raise AssertionError('no pending retry to crash')
                os.killpg(process.pid,signal.SIGKILL);process.wait()
            with path.open('ab') as file:file.write(b'{"op":"partial')
            with server(binary,env) as (port,_):
                restored={j['id']:j for j in json.loads(request(port,'GET','/jobs')[1])}
                assert {k:v for k,v in restored.items() if k!='resume'}==expected
                assert json.loads(request(port,'POST','/events',{'id':'retry','payload':None})[1])['duplicate']
                assert request(port,'POST','/events',{'id':'bad\r\nkey','payload':{}})[0]==400
                assert request(port,'POST','/events',{'id':'after','payload':{'recover':True}})[0]==202
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    if 'after' in effects and 'resume' in effects:break
                    time.sleep(.02)
                else:raise AssertionError('pending/new delivery after restart failed')
                assert attempts['resume']==2
    finally:receiver.shutdown();receiver.server_close();thread.join()
    print('PASS webhook: durable enqueue, concurrent deduplication, retries, deadlines, failure limits and restart recovery',flush=True)

def json_differential(binary,count=600):
    rng=random.Random(241024)
    valid=[None,True,False,0,-1,9223372036854775807,'café 🚀','\x00\n"\\',{'a':[1,2,{'b':'hello'}]},[{},[],None]]
    corpus=[json.dumps(v,ensure_ascii=i%2==0,separators=(',',':')).encode() for i,v in enumerate(valid)]
    corpus += [b'',b'[1,]',b'01',b'{"a":}',b'"\\ud800"',b'"\\udc00"',b'NaN',b'\xff',b'[true false]',b'1e+',b'"\x01"',b'[[[[0]]]]',
        b'['*128+b'0'+b']'*128,b'['*129+b'0'+b']'*129,b'"\xc0\x80"',b'"\xf4\x90\x80\x80"',b'{"a":1,"a":2}']
    for i in range(count):
        source=bytearray(rng.choice(corpus[:10]));position=rng.randrange(len(source)+1)
        if rng.randrange(2) and source:del source[min(position,len(source)-1)]
        else:source[position:position]=bytes([rng.randrange(256)])
        corpus.append(bytes(source))
    data=b''.join(case.hex().encode()+b'\n' for case in corpus)
    result=subprocess.run(RUNNER+[str(binary)],input=data,capture_output=True,timeout=90)
    assert result.returncode==0,result.stderr
    replies=[json.loads(line) for line in result.stdout.splitlines()]
    assert len(replies)==len(corpus),(len(replies),len(corpus))
    def scalar_strings(value,depth=0):
        if depth>128:return False
        if isinstance(value,str):return not any(0xd800<=ord(c)<=0xdfff for c in value)
        if isinstance(value,list):return all(scalar_strings(v,depth+1) for v in value)
        if isinstance(value,dict):return all(scalar_strings(k,depth+1) and scalar_strings(v,depth+1) for k,v in value.items())
        return True
    for case,reply in zip(corpus,replies):
        try:
            parsed=json.loads(case.decode('utf-8'),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
            accepted=scalar_strings(parsed)
        except (ValueError,UnicodeError):accepted=False;parsed=None
        assert reply['ok']==accepted,(case,reply,accepted)
        if accepted:assert reply['value']==parsed,(case,reply,parsed)
    (OUT/'json-fuzz-corpus.json').write_text(json.dumps([case.hex() for case in corpus]))
    print(f'PASS JSON differential fuzz: {len(corpus)} valid/malformed byte inputs against independent Python JSON',flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only',choices=('cli','notes','webhook','json','io'));args=parser.parse_args()
    cases={'cli':('json-cli','examples/json-cli/main.neo',json_cli),'notes':('notes','examples/notes/main.neo',notes),
           'webhook':('webhook','examples/webhook/main.neo',webhook),'json':('json-probe','tests/fixtures/json_probe.neo',json_differential),
           'io':('io','tests/fixtures/io.neo',io_library)}
    for name,(binary,source,verify) in cases.items():
        if not args.only or args.only==name:verify(build(binary,source))

if __name__=='__main__':main()
