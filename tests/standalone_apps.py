#!/usr/bin/env python3
"""Audit prepared scratch images via Docker socket, from a Linux tool container.

Application containers are nonroot, read-only, capability-free and receive
only writable application data. The tools/image builder stays outside them.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bench/http'))
spec=importlib.util.spec_from_file_location('docker_app_audit',ROOT/'bench/docker/compare.py');bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)

def main():
    p=argparse.ArgumentParser();p.add_argument('--arch',choices=('arm64','x86_64'),required=True);args=p.parse_args()
    out=ROOT/'.kernel-build/usability/standalone'/args.arch;out.mkdir(parents=True,exist_ok=True)
    engine=bench.Engine();results=[]
    for name in ('json-cli','notes','webhook'):
        tag=f'neo-usability-{name}-{args.arch}:20261024'
        config={'Image':tag,'Env':['NEO_THREADS=2','NEO_NOTES_FILE=/data/notes.log','NEO_WEBHOOK_FILE=/data/jobs.log','NEO_WEBHOOK_PORT=1','NEO_WEBHOOK_MAX_ATTEMPTS=1'],
            'HostConfig':{'ReadonlyRootfs':True,'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],'Memory':256*2**20,'PidsLimit':64,
                'Tmpfs':{'/data':'rw,size=33554432,mode=1777'}}}
        if name=='json-cli':config['Cmd']=['/input.json','/data/output.json','1']
        cid=engine.call('POST','/containers/create',config)['Id']
        try:
            engine.call('POST',f'/containers/{cid}/start');info=engine.call('GET',f'/containers/{cid}/json')
            assert info['Config']['User']=='65532:65532'
            if name=='json-cli':
                state=engine.call('POST',f'/containers/{cid}/wait?condition=not-running')
                assert state['StatusCode']==0,state
            else:
                host=info['NetworkSettings']['Networks']['bridge']['IPAddress'];deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    try:
                        if bench.request(host,'/')[0] in (200,404):break
                    except OSError:time.sleep(.02)
                else:raise AssertionError('scratch server not ready')
                import http.client
                path='/api/notes' if name=='notes' else '/events'
                body={'title':'standalone café 🚀'} if name=='notes' else {'id':'standalone','payload':{'value':'café 🚀'}}
                c=http.client.HTTPConnection(host,8080,timeout=10);c.request('POST',path,body=json.dumps(body),headers={'Content-Type':'application/json'})
                response=c.getresponse();payload=response.read();assert response.status==(201 if name=='notes' else 202),(response.status,payload);c.close()
                status,body,_=bench.request(host,'/api/notes' if name=='notes' else '/jobs')
                assert status==200 and len(json.loads(body))==1
            info=engine.call('GET',f'/containers/{cid}/json')
            assert not info['State']['OOMKilled']
            results.append({'image':tag,'valid':True,'inspect':info})
            print('PASS scratch',args.arch,name,'nonroot/read-only/cap-drop; runtime and I/O work',flush=True)
        finally:engine.remove(cid,out/(name+'-server.log'))
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':main()
