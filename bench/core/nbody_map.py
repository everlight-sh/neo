#!/usr/bin/env python3
"""Interleaved native N-body and string/generic-map before/after measurements."""
import argparse,datetime,hashlib,json,math,os,platform,random,resource,statistics,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--repeats',type=int,default=11)
    args=parser.parse_args();assert platform.system()=='Linux' and not os.environ.get('NEO_RUNNER') and args.repeats>=7
    baseline=args.baseline.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    preserved=json.loads((baseline/'sources.json').read_text())
    assert all(hashlib.sha256((baseline/n).read_bytes()).hexdigest()==h for n,h in preserved.items())
    data={'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'repeats':args.repeats,'warmups':2,'seed':251025,'platform':platform.platform(),'baseline_sources':preserved,'rows':[],'profiles':[],'valid':False,'load_start':os.getloadavg()}
    def save():(out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')
    def execute(command,log,cwd=ROOT,env=None):
        run=subprocess.run(list(map(str,command)),cwd=cwd,env={**os.environ,**(env or {})},capture_output=True,text=True,timeout=180)
        (out/log).write_text(run.stdout+run.stderr);assert run.returncode==0,(command,run.stdout[-2000:],run.stderr);return run
    try:
        binaries={}
        for label,compiler in [('before',baseline),('after',ROOT)]:
            for name,source in [('nbody','examples/nbody.neo'),('collections','tests/fixtures/language_bench.neo'),('generic','tests/fixtures/generic_map_bench.neo')]:
                for stats in ([False,True] if name!='nbody' else [False]):
                    key=f'{label}-{name}'+('-profile' if stats else '');binary=out/key
                    run=execute([sys.executable,'-m','neoc','build',ROOT/source,'-o',binary,'--report'],key+'-build.json',cwd=compiler,env={'PYTHONPATH':str(compiler),'NEO_ALLOC_STATS':str(int(stats))})
                    report=json.loads(run.stdout);assert report['undefined_symbols']==[]
                    assert not execute(['nm','-u',binary],key+'-imports.txt').stdout.strip()
                    for tool,flag in [('readelf','-l'),('readelf','-d')]:
                        audit=execute([tool,flag,binary],key+'-'+flag+'.txt').stdout;assert 'INTERP' not in audit and 'NEEDED' not in audit
                    binaries[key]=binary
        execute(['cargo','build','--release','--locked','--manifest-path','bench/rust/Cargo.toml','--bin','nbody'],'rust-build.log')
        execute(['go','build','-o',out/'go-nbody','./nbody'],'go-build.log',ROOT/'bench/go',{'GOWORK':'off','CGO_ENABLED':'0','GOTOOLCHAIN':'local'})
        binaries['Rust-nbody']=ROOT/'bench/rust/target/release/nbody';binaries['Go-nbody']=out/'go-nbody'
        data['versions']={tool:execute([tool,'version'] if tool=='go' else [tool,'--version'],tool+'-version.txt').stdout.strip() for tool in ['clang','rustc','go']}
        rng=random.Random(data['seed'])
        for n,steps in [(1024,3),(2048,10),(4096,10)]:
            for workers in [1,4]:
                samples={name:[] for name in ['before','after','Rust','Go']};expected=None
                for repeat in range(args.repeats+2):
                    order=list(samples);rng.shuffle(order)
                    for name in order:
                        binary=binaries[name+'-nbody'];command=['taskset','-c','0' if workers==1 else '0-3',str(binary),str(n),str(steps)]
                        before=resource.getrusage(resource.RUSAGE_CHILDREN);start=__import__('time').perf_counter_ns()
                        run=subprocess.run(command,capture_output=True,text=True,timeout=90,env={**os.environ,'NEO_THREADS':str(workers),'RAYON_NUM_THREADS':str(workers),'GOMAXPROCS':str(workers)})
                        elapsed=__import__('time').perf_counter_ns()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN)
                        (out/f'nbody-{n}-{steps}-{workers}-{name}-{repeat}.txt').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stderr
                        value=float(run.stdout);expected=value if expected is None else expected;assert math.isclose(value,expected,rel_tol=1e-9,abs_tol=1e-12),(name,value,expected)
                        if repeat>=2:samples[name].append({'command':command,'wall_ns':elapsed,'cpu_s':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,'output':run.stdout})
                for name,runs in samples.items():
                    data['rows'].append({'workload':'nbody','n':n,'steps':steps,'workers':workers,'implementation':name,'runs':runs});print('nbody',n,steps,workers,name,round(statistics.median(r['wall_ns'] for r in runs)/1e6,3),'ms',flush=True)
                save()
        for kind,mode,n in [('string-map',2,10000),('string-map',2,100000),('string-map',2,1000000),('generic-map',2,1000000),('append',0,1000000),('sort',1,1000000)]:
            samples={name:[] for name in ['before','after']};binary_kind='generic' if kind=='generic-map' else 'collections';parameters=[n] if kind=='generic-map' else [mode,n]
            expected=7*n*(n-1)//2 if mode==2 else sum(i%997 for i in range(n)) if mode==0 else sum((i+1)*v for i,v in enumerate(sorted((n-i)%997 for i in range(n))))
            for repeat in range(args.repeats+2):
                order=list(samples);rng.shuffle(order)
                for name in order:
                    rss=out/f'{kind}-{n}-{name}-{repeat}.usage';command=['/usr/bin/time','-f','%U %S %M','-o',str(rss),'taskset','-c','0',str(binaries[name+'-'+binary_kind]),*map(str,parameters)]
                    start=__import__('time').perf_counter_ns();run=subprocess.run(command,capture_output=True,text=True,timeout=120,env={**os.environ,'NEO_THREADS':'1'});elapsed=__import__('time').perf_counter_ns()-start
                    (out/f'{kind}-{n}-{name}-{repeat}.txt').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stderr
                    checksum,phase_ns,requests,traffic=map(int,run.stdout.split());assert requests==traffic==0
                    assert checksum==expected,(kind,name,checksum,expected)
                    user,system,rss_kib=map(float,rss.read_text().split())
                    if repeat>=2:samples[name].append({'command':command,'wall_ns':elapsed,'phase_ns':phase_ns,'cpu_s':user+system,'peak_rss_bytes':int(rss_kib*1024),'checksum':checksum})
            for name,runs in samples.items():
                data['rows'].append({'workload':kind,'n':n,'workers':1,'implementation':name,'runs':runs});print(kind,n,name,round(statistics.median(r['phase_ns'] for r in runs)/1e6,3),'ms',round(max(r['peak_rss_bytes'] for r in runs)/2**20,2),'MiB',flush=True)
                profile=execute(['taskset','-c','0',binaries[name+'-'+binary_kind+'-profile'],*parameters],f'{kind}-{n}-{name}-profile.txt',env={'NEO_THREADS':'1'})
                checksum,phase_ns,requests,traffic=map(int,profile.stdout.split());assert checksum==expected
                data['profiles'].append({'workload':kind,'n':n,'implementation':name,'requests':requests,'requested_bytes':traffic})
            save()
        data['binary_sha256']={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in binaries.items()}
        files=[Path(__file__),ROOT/'examples/nbody.neo',ROOT/'tests/fixtures/language_bench.neo',ROOT/'tests/fixtures/generic_map_bench.neo',ROOT/'bench/rust/src/nbody.rs',ROOT/'bench/rust/Cargo.lock',ROOT/'bench/rust/Cargo.toml',ROOT/'bench/go/nbody/main.go']
        files+=[p for folder,glob in [('neoc','*.py'),('stdlib','*.neo'),('runtime','*.neo')] for p in (ROOT/folder).glob(glob)]
        data['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        assert all(hashlib.sha256((baseline/n).read_bytes()).hexdigest()==h for n,h in preserved.items())
        data['valid']=True;data['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat();data['load_end']=os.getloadavg();save()
    except BaseException as error:data['failure']=repr(error);save();raise
if __name__=='__main__':main()
