#!/usr/bin/env python3
"""Interleaved original/pre-fix/fixed Axon comparisons against Rust, Go and Bun."""
import argparse, hashlib, importlib.util, json, math, os, random, resource, select
import shutil, statistics, subprocess, sys, time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--repeats',type=int,default=9);p.add_argument('--http-repeats',type=int,default=5);a=p.parse_args()
    assert a.repeats>=7 and a.http_repeats>=5 and os.uname().machine in ('aarch64','arm64')
    work=a.workspace.resolve();root=work/'current';out=work/'results';bins=out/'bin'
    inventory=json.loads((out/'inventory.json').read_text());assert not (out/'measurements.json').exists()
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    def audit():
        for name,digest in inventory['source_hashes'].items():assert sha(root/name)==digest,('changed source',name)
        for name,details in inventory['binaries'].items():assert sha(bins/name)==details['sha256'],('changed executable',name)
    audit();shutil.copyfile(Path(__file__),out/'measurement-harness.py')
    env={**os.environ,'NEO_HOME':str(root),'PYTHONPATH':str(root),'NEO_THREADS':'1','GOMAXPROCS':'1','GOWORK':'off','GOTOOLCHAIN':'local'}
    rng=random.Random(271027);data={'valid':False,'repeats':a.repeats,'warmups':2,'seed':271027,'compute':[],'json':[],'collections':[],'maps':[],'profiles':[],'http':[],'inventory':inventory,'started':time.time()}
    def save():(out/'measurements.json').write_text(json.dumps(data,indent=2))
    def run(cmd,slug,workers=1):
        usage=out/(slug+'.time');before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter_ns()
        argv=['/usr/bin/time','-f','%M','-o',str(usage),'taskset','-c','0' if workers==1 else '0-3',*map(str,cmd)]
        r=subprocess.run(argv,cwd=root,env={**env,'NEO_THREADS':str(workers),'GOMAXPROCS':str(workers),'RAYON_NUM_THREADS':str(workers)},capture_output=True,text=True,timeout=120)
        wall=time.perf_counter_ns()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN)
        (out/(slug+'.stdout')).write_text(r.stdout);(out/(slug+'.stderr')).write_text(r.stderr)
        assert r.returncode==0,(slug,r.returncode,r.stderr)
        return dict(wall_ns=wall,cpu_s=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,peak_rss_bytes=int(usage.read_text())*1024,output=r.stdout.strip(),command=argv)
    def process_case(section,key,variants,verify,workers=1):
        samples={n:[] for n in variants}
        for trial in range(a.repeats+2):
            order=list(variants);rng.shuffle(order)
            for name in order:
                result=run(variants[name],section+'-'+key+'-'+name+'-'+str(trial),workers)
                verify(result['output']);result['trial']=trial
                if trial>=2:samples[name].append(result)
        data[section].append(dict(case=key,workers=workers,runs=samples))
        print(section,key,{n:round(statistics.median(x['wall_ns'] for x in rs)/1e6,3) for n,rs in samples.items()},flush=True);save()
    def equal_int(expected):
        def check(output):assert int(output)==expected,(output,expected)
        return check
    try:
        # Check the new Bun implementations at small inputs before timing them.
        for kind,args in [('mandel',[31,29,50]),('stencil',[73,7]),('nbody',[32,2])]:
            expected=subprocess.check_output([str(bins/('previous-'+kind)),*map(str,args)],env=env,text=True).strip()
            result=subprocess.check_output(['bun',str(root/'bench/core/compute.ts'),kind,*map(str,args)],env=env,text=True).strip()
            assert math.isclose(float(result),float(expected),rel_tol=1e-9,abs_tol=1e-12) if kind=='nbody' else result==expected
        for workers in [1,4]:
            for kind,args in [('mandel',[1200,1200,300]),('stencil',[1000000,20]),('nbody',[1024,3]),('nbody',[4096,10])]:
                expected=subprocess.check_output(['taskset','-c','0',str(bins/('previous-'+kind)),*map(str,args)],env=env,text=True).strip()
                variants={name:[bins/(prefix+kind),*args] for name,prefix in [('previous','previous-'),('Before','before-'),('Axon','axon-'),('Rust','rust-'),('Go','go-')]}
                if workers==1:variants['Bun']=['bun',root/'bench/core/compute.ts',kind,*args]
                def verify(output):
                    assert math.isclose(float(output),float(expected),rel_tol=1e-9,abs_tol=1e-12) if kind=='nbody' else output==expected,(kind,output,expected)
                process_case('compute',kind+'-'+'-'.join(map(str,args)),variants,verify,workers)
        for n in [10000,100000,1000000]:
            variants={'previous':[bins/'previous-json','0',n],'Before':[bins/'before-json','0',n],'Axon':[bins/'axon-json','0',n],'Rust':[bins/'rust-json','parse',n],'Go':[bins/'go-json',n],'Bun':['bun',root/'bench/usability/bun.ts','parse',n]}
            expected=513500*(n//1000)
            process_case('json',str(n),variants,equal_int(expected))
        for kind,mode,n in [('append',0,1000000),('sort',1,1000000),('string-map',2,100000),('string-map',2,1000000),('generic-map',2,1000000)]:
            binary='generic' if kind=='generic-map' else 'collections';params=[n] if kind=='generic-map' else [mode,n]
            expected=7*n*(n-1)//2 if mode==2 else sum(i%997 for i in range(n)) if mode==0 else sum((i+1)*v for i,v in enumerate(sorted((n-i)%997 for i in range(n))))
            variants={name:[bins/(prefix+binary),*params] for name,prefix in [('previous','previous-'),('Before','before-'),('Axon','axon-')]}
            def verify(output):
                checksum,ns,requests,traffic=map(int,output.split());assert checksum==expected and requests==traffic==0 and ns>0
            process_case('collections',kind+'-'+str(n),variants,verify)
            for name,prefix in [('previous','previous-'),('Before','before-'),('Axon','axon-')]:
                r=run([bins/(prefix+binary+'-profile'),*params],'profile-'+kind+'-'+name)
                checksum,ns,requests,traffic=map(int,r['output'].split());assert checksum==expected
                data['profiles'].append(dict(case=kind+'-'+str(n),implementation=name,requests=requests,requested_bytes=traffic))
        # The original protocol pauses outside every API phase for procfs memory.
        spec=importlib.util.spec_from_file_location('map_protocol',root/'bench/maps/run.py');mp=importlib.util.module_from_spec(spec);spec.loader.exec_module(mp)
        for n in [0,100000,1000000]:
            for reserved in [0,1]:
                variants={name:[bins/file,n,reserved] for name,file in [('previous','previous-map'),('Before','before-map'),('Axon','axon-map'),('Rust','rust-map'),('Go','go-map')]}
                if not reserved:variants['Bun']=['bun',root/'bench/maps/bun.ts',n,0]
                samples={name:[] for name in variants}
                repeats=1 if n==0 else a.repeats+2
                for trial in range(repeats):
                    order=list(variants);rng.shuffle(order)
                    for name in order:
                        slug=f'maps-{n}-{reserved}-{name}-{trial}';cmd=['taskset','-c','0',*map(str,variants[name])];records=[]
                        with (out/(slug+'.stderr')).open('w') as error:
                            proc=subprocess.Popen(cmd,cwd=root,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=error)
                            try:
                                for phase in mp.PHASES:
                                    assert select.select([proc.stdout],[],[],90)[0],(slug,phase,'timeout')
                                    text=proc.stdout.readline().decode();fields=text.split();assert len(fields)==4,(slug,text)
                                    actual,ns,checksum,count=fields;assert actual==phase and (int(checksum),int(count))==mp.expected(phase,n),(slug,text)
                                    records.append(dict(phase=phase,ns=int(ns),checksum=int(checksum),count=int(count),**mp.memory(proc.pid)))
                                    proc.stdin.write(b'x');proc.stdin.flush()
                                assert proc.wait(timeout=10)==0,(slug,proc.returncode)
                            finally:
                                if proc.poll() is None:proc.kill();proc.wait()
                        (out/(slug+'.json')).write_text(json.dumps(records))
                        if trial>=2 or n==0:samples[name].append(dict(trial=trial,phases=records,command=cmd))
                data['maps'].append(dict(n=n,reserved=bool(reserved),runs=samples))
                print('maps',n,reserved,{name:round(statistics.median(next(p['ns'] for p in r['phases'] if p['phase']=='lookup') for r in rs)/1e6,3) for name,rs in samples.items()},flush=True);save()
        audit()
        # Actual measured current binaries must still execute without a rootfs.
        for name,args,expected in [('axon-json',['0','1000000'],513500000),('axon-collections',['0','1000000'],497995554)]:
            import tempfile
            with tempfile.TemporaryDirectory(prefix='axon-core-empty-root-') as temp:
                target=Path(temp)/'program';shutil.copyfile(bins/name,target);target.chmod(0o755)
                r=subprocess.run(['chroot',temp,'/program',*args],capture_output=True,text=True,timeout=60);assert r.returncode==0 and int(r.stdout.split()[0])==expected,(name,r.stdout,r.stderr)
        r=subprocess.run(['python3',str(root/'tests/map_freestanding.py'),'--binary',str(bins/'axon-map')],cwd=root,env=env,capture_output=True,text=True,timeout=120)
        (out/'empty-root-map.log').write_text(r.stdout+r.stderr);assert r.returncode==0,(r.stdout,r.stderr)
        spec=importlib.util.spec_from_file_location('http',root/'bench/http/compare.py');hp=importlib.util.module_from_spec(spec);spec.loader.exec_module(hp)
        def load(port,scenario,duration,threads,log):
            cmd=['taskset','-c','4-7',str(bins/'http-load'),str(port),str(scenario[2]),str(scenario[3]),duration]
            r=subprocess.run(cmd,env={**os.environ,'GOMAXPROCS':'4'},capture_output=True,text=True,timeout=30)
            log.write_text(r.stdout+r.stderr);assert r.returncode==0,(cmd,r.stdout,r.stderr)
            value=json.loads(r.stdout);assert value['errors']==0 and value['requests']>0,value
            return dict(rps=value['rps'],requests=value['requests'],p50_us=None,p99_us=None,non2xx=0,errors=0,command=cmd,log=str(log),elapsed_ns=value['elapsed_ns'])
        hp.load=load;os.sched_setaffinity(0,{4,5,6,7});sampler=hp.Sampler();data['http_calibration']=sampler.calibrate()
        refs={'1000':hp.checksum(1000),'10000':hp.checksum(10000),'nbody':hp.nbody_reference()};config=argparse.Namespace(duration='2s',warmup='1s',repeats=1,threads=4)
        servers={'previous':bins/'previous-http','Before':bins/'before-http','Axon':bins/'axon-http','Rust':bins/'rust-http','Go':bins/'go-http','Bun':Path(shutil.which('bun'))};rng=random.Random(271027)
        data['http_protocol']='Validation-first Go load client; complete Content-Length/status/body checked on every response, full outstanding pipeline batches drained before finish. No latency percentiles measured.'
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
        audit();data['finished']=time.time();data['valid']=True;save();print('ALL CORE FIX OUTPUTS, SOURCE AUDITS AND EMPTY-ROOT CHECKS PASS',flush=True)
    except BaseException as error:data['failure']=repr(error);save();raise

if __name__=='__main__':main()
