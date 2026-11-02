#!/usr/bin/env python3
"""Fresh, independently interleaved repeat of flagged map workloads."""
import argparse,hashlib,importlib.util,json,os,random,select,statistics,subprocess,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--repeats',type=int,default=15);a=p.parse_args();assert a.repeats>=15
    root=a.workspace/'current';out=a.workspace/'results';target=out/'confirmation';target.mkdir(exist_ok=False);bins=out/'bin'
    initial=json.loads((out/'measurements.json').read_text());assert initial['valid']
    spec=importlib.util.spec_from_file_location('maps',root/'bench/maps/run.py');mp=importlib.util.module_from_spec(spec);spec.loader.exec_module(mp)
    env={**os.environ,'NEO_THREADS':'1','GOMAXPROCS':'1'};rng=random.Random(271029);data={'repeats':a.repeats,'warmups':3,'maps':[],'collections':[],'valid':False};started=time.time()
    def save():(target/'measurements.json').write_text(json.dumps(data,indent=2))
    for n in [100000,1000000]:
        for reserved in [0,1]:
            samples={name:[] for name in ['previous','Axon']}
            for trial in range(a.repeats+3):
                order=list(samples);rng.shuffle(order)
                for name in order:
                    binary=bins/('previous-map' if name=='previous' else 'axon-map');slug=f'{n}-{reserved}-{name}-{trial}';cmd=['taskset','-c','0',str(binary),str(n),str(reserved)];records=[]
                    with (target/(slug+'.stderr')).open('w') as error:
                        proc=subprocess.Popen(cmd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=error)
                        try:
                            for phase in mp.PHASES:
                                assert select.select([proc.stdout],[],[],90)[0],(slug,phase)
                                line=proc.stdout.readline().decode();actual,ns,checksum,count=line.split();assert actual==phase and (int(checksum),int(count))==mp.expected(phase,n)
                                records.append(dict(phase=phase,ns=int(ns),checksum=int(checksum),count=int(count),**mp.memory(proc.pid)));proc.stdin.write(b'x');proc.stdin.flush()
                            assert proc.wait(timeout=10)==0
                        finally:
                            if proc.poll() is None:proc.kill();proc.wait()
                    (target/(slug+'.json')).write_text(json.dumps(records))
                    if trial>=3:samples[name].append(dict(trial=trial,phases=records))
            data['maps'].append(dict(n=n,reserved=bool(reserved),runs=samples));save()
            print(n,reserved,{name:{phase:round(statistics.median(next(x['ns'] for x in r['phases'] if x['phase']==phase) for r in runs)/1e6,3) for phase in ['insert','lookup','update','delete']} for name,runs in samples.items()},flush=True)
    samples={name:[] for name in ['previous','Axon']};n=1000000;expected=7*n*(n-1)//2
    for trial in range(a.repeats+3):
        order=list(samples);rng.shuffle(order)
        for name in order:
            binary=bins/('previous-collections' if name=='previous' else 'axon-collections');usage=target/f'string-{name}-{trial}.time'
            r=subprocess.run(['/usr/bin/time','-f','%M','-o',str(usage),'taskset','-c','0',str(binary),'2',str(n)],env=env,capture_output=True,text=True,timeout=60)
            (target/f'string-{name}-{trial}.stdout').write_text(r.stdout);assert r.returncode==0,(name,r.stderr)
            checksum,phase,requests,traffic=map(int,r.stdout.split());assert checksum==expected and requests==traffic==0
            if trial>=3:samples[name].append(dict(phase_ns=phase,peak_rss_bytes=int(usage.read_text())*1024,trial=trial))
    data['collections'].append(dict(case='string-map-1000000',runs=samples));print('collections',{n:round(statistics.median(x['phase_ns'] for x in rs)/1e6,3) for n,rs in samples.items()},flush=True)
    for name,details in initial['inventory']['binaries'].items():assert hashlib.sha256((bins/name).read_bytes()).hexdigest()==details['sha256'],name
    data['elapsed_s']=time.time()-started;data['valid']=True;save();print('CONFIRMATION COMPLETE',flush=True)

if __name__=='__main__':main()
