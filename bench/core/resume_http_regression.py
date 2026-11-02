#!/usr/bin/env python3
"""Resume validated core data with an independently validating HTTP client."""
import argparse,hashlib,importlib.util,json,os,random,shutil,subprocess,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();root=a.workspace/'current';out=a.workspace/'results';bins=out/'bin'
    data=json.loads((out/'measurements.json').read_text());assert data.get('failure') and not data['valid']
    assert len(data['compute'])==8 and len(data['json'])==3 and len(data['collections'])==5 and len(data['maps'])==6
    shutil.copyfile(out/'measurements.json',out/'measurements-initial-http-failure.json')
    data['initial_http_failure']=data.pop('failure');data['initial_http']=data['http'];data['http']=[]
    shutil.copyfile(Path(__file__),out/'http-resume-harness.py')
    spec=importlib.util.spec_from_file_location('http',root/'bench/http/compare.py');hp=importlib.util.module_from_spec(spec);spec.loader.exec_module(hp)
    def load(port,scenario,duration,threads,log):
        cmd=['taskset','-c','4-7',str(bins/'http-load'),str(port),str(scenario[2]),str(scenario[3]),duration]
        r=subprocess.run(cmd,env={**os.environ,'GOMAXPROCS':'4'},capture_output=True,text=True,timeout=30)
        log.write_text(r.stdout+r.stderr);assert r.returncode==0,(cmd,r.stdout,r.stderr)
        value=json.loads(r.stdout);assert value['errors']==0 and value['requests']>0,value
        return dict(rps=value['rps'],requests=value['requests'],p50_us=None,p99_us=None,non2xx=0,errors=0,command=cmd,log=str(log),elapsed_ns=value['elapsed_ns'])
    hp.load=load;os.sched_setaffinity(0,{4,5,6,7});sampler=hp.Sampler();data['http_calibration']=sampler.calibrate()
    refs={'1000':hp.checksum(1000),'10000':hp.checksum(10000),'nbody':hp.nbody_reference()};config=argparse.Namespace(duration='2s',warmup='1s',repeats=1,threads=4)
    servers={'previous':bins/'previous-http','Axon':bins/'axon-http','Rust':bins/'rust-http','Go':bins/'go-http','Bun':Path(shutil.which('bun'))};rng=random.Random(271027)
    data['http_protocol']='Validation-first Go load client; complete Content-Length/status/body checked on every response, full outstanding pipeline batches drained before finish. No latency percentiles measured. Failed wrk run retained separately.'
    def save():(out/'measurements.json').write_text(json.dumps(data,indent=2))
    for label,workers,connections,depth in [('hello-1',1,64,0),('pipeline-1',1,64,16),('hello-4',4,256,0)]:
        for trial in range(5):
            order=list(servers);rng.shuffle(order)
            for name in order:
                directory=out/'http-validated'/label/str(trial)/name;directory.mkdir(parents=True,exist_ok=False);binary=servers[name]
                def argv(port):return ['taskset','-c','0' if workers==1 else '0-3',str(binary),*(['run',str(root/'bench/bun/server.ts')] if name=='Bun' else []),str(port)]
                result=hp.measure((name,binary),(label,'/',connections,depth,True),config,sampler,refs,directory,command_override=argv,env_override={'NEO_THREADS':str(workers),'TOKIO_WORKER_THREADS':str(workers),'GOMAXPROCS':str(workers)})
                data['http'].append(dict(case=label,workers=workers,trial=trial,implementation=name,result=result));save();assert result['valid'],(label,trial,name)
                print(label,trial,name,round(result['median_rps']),flush=True)
    for name,digest in data['inventory']['source_hashes'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    for name,details in data['inventory']['binaries'].items():assert hashlib.sha256((bins/name).read_bytes()).hexdigest()==details['sha256'],name
    data['finished']=time.time();data['valid']=True;save();print('COMPLETE: CORE/JSON/MAPS/HTTP SOURCE, OUTPUT AND STANDALONE CHECKS PASS',flush=True)

if __name__=='__main__':main()
