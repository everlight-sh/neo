#!/usr/bin/env python3
"""Independent socket peer: burst accepts, short-lived connections, binary bodies.

No request is retried: a dropped/duplicated connection must fail this regression.
"""
import argparse
import concurrent.futures
import http.client
import os
from pathlib import Path
import signal
import secrets
import socket
import subprocess
import tempfile
import time
from agent_codecs import RUNNER

ROOT=Path(__file__).resolve().parents[1]
def free_port():
    for _ in range(128):
        number=15000+secrets.randbelow(15000)
        with socket.socket() as reservation:
            try:reservation.bind(('0.0.0.0',number))
            except OSError:continue
            return number
    raise RuntimeError('No free test listener port')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path);parser.add_argument('--requests',type=int,default=1024)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='neo-http-ownership-') as temporary:
        binary=args.binary or Path(temporary)/'server'
        if not args.binary:subprocess.run([str(ROOT/'neoc.sh'),'build',str(ROOT/'tests/fixtures/http_handoff.neo'),'-o',str(binary)],check=True)
        for workers in (2,4):
            port=free_port()
            with tempfile.TemporaryFile() as log:
                process=subprocess.Popen(RUNNER+[str(binary),str(port)],env={**os.environ,'NEO_THREADS':str(workers)},start_new_session=True,stdout=subprocess.DEVNULL,stderr=log)
                try:
                    for _ in range(200):
                        if process.poll() is not None:raise AssertionError('Native server stopped')
                        try:
                            with socket.create_connection(('127.0.0.1',port),timeout=.1):break
                        except OSError:time.sleep(.01)
                    else:raise AssertionError('Native server not ready')
                    def one(index):
                        body=(str(index)+': café\0').encode()+bytes(range(256))*4
                        connection=http.client.HTTPConnection('127.0.0.1',port,timeout=15)
                        try:
                            connection.request('POST','/echo',body,{'Content-Type':'application/octet-stream',**({'Connection':'close'} if index%2 else {})})
                            response=connection.getresponse();assert response.status==200 and response.read()==body,index
                        finally:connection.close()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:list(pool.map(one,range(args.requests)))
                    print(f'PASS {workers} native workers: {args.requests} short-lived concurrent connections, binary echoes, no retries',flush=True)
                finally:
                    if process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
                    process.wait(timeout=10)

if __name__=='__main__':main()
