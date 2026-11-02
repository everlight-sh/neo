#!/usr/bin/env python3
"""Frozen three-version append/JSON comparison, with unchanged Rust/Bun JSON."""
import argparse,hashlib,json,os,platform,random,resource,statistics,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=int,default=15)
    args=p.parse_args();assert platform.system()=='Linux' and not os.environ.get('NEO_RUNNER') and args.repeats>=7
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    env={**os.environ,'NEO_THREADS':'1','GOMAXPROCS':'1'}
    compilers={'Axon original':args.original.resolve(),'Axon lookup':args.baseline.resolve(),'Axon fixed':ROOT}
    data={'valid':False,'started':time.time(),'platform':platform.platform(),'warmups':3,'affinity':[0],'repeats':args.repeats,'rows':[],'profiles':[],'binaries':{},'commands':[],'load_start':os.getloadavg()}
    def save():(out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')
    def command(cmd,log,cwd=ROOT,extra=None):
        run=subprocess.run(list(map(str,cmd)),cwd=cwd,env={**env,**(extra or {})},capture_output=True,text=True,timeout=180)
        (out/log).write_text(run.stdout+run.stderr);data['commands'].append({'command':list(map(str,cmd)),'cwd':str(cwd),'exit':run.returncode})
        assert run.returncode==0,(log,run.stdout[-2000:],run.stderr[-2000:]);return run.stdout
    try:
        binaries={}
        for name,compiler in compilers.items():
            if name!='Axon fixed':
                hashes=json.loads((compiler/'sources.json').read_text())
                assert all(hashlib.sha256((compiler/f).read_bytes()).hexdigest()==h for f,h in hashes.items())
            for kind,source,stats in [('append','tests/fixtures/language_bench.neo',False),('append-profile','tests/fixtures/language_bench.neo',True),('json','examples/library_bench.neo',False)]:
                binary=out/(name.replace(' ','-')+'-'+kind)
                report=json.loads(command(['python3','-m','neoc','build',ROOT/source,'-o',binary,'--report'],binary.name+'-build.json',compiler,{'PYTHONPATH':str(compiler),'NEO_ALLOC_STATS':str(int(stats))}))
                assert report['undefined_symbols']==[]
                assert not command(['nm','-u',binary],binary.name+'-imports.txt').strip()
                for flag in ['-l','-d']:
                    audit=command(['readelf',flag,binary],binary.name+flag+'.txt');assert 'INTERP' not in audit and 'NEEDED' not in audit
                binaries[name,kind]=binary
                data['binaries'][binary.name]={'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'bytes':binary.stat().st_size}
            checksum,ns,requests,traffic=map(int,command(['taskset','-c','0',binaries[name,'append-profile'],'0','1000000'],name+'-append-profile.txt').split())
            assert checksum==sum(i%997 for i in range(1000000))
            data['profiles'].append({'implementation':name,'requests':requests,'requested_bytes':traffic})
        assert len({(r['requests'],r['requested_bytes']) for r in data['profiles']})==1,'append allocation policy changed'
        command(['cargo','build','--release','--locked','--manifest-path','bench/rust/Cargo.toml','--bin','usability'],'rust-build.log')
        rust=ROOT/'bench/rust/target/release/usability'
        data['versions']={name:command(cmd,name+'-version.txt').splitlines()[0] for name,cmd in {'clang':['clang','--version'],'Rust':['rustc','--version'],'Bun':['bun','--version'],'Python':['python3','--version']}.items()}
        data['binaries']['Rust-json']={'sha256':hashlib.sha256(rust.read_bytes()).hexdigest(),'bytes':rust.stat().st_size}
        rng=random.Random(25102513)
        for kind,n,repeats in [('append',1000000,max(31,args.repeats)),('json',10000,args.repeats),('json',100000,args.repeats),('json',1000000,args.repeats)]:
            cases={name:[binaries[name,kind],'0',n] for name in compilers}
            if kind=='json':cases.update({'Rust':[rust,'parse',n],'Bun':['bun',ROOT/'bench/usability/bun.ts','parse',n]})
            expected=sum(i%997 for i in range(n)) if kind=='append' else sum(i%1000+14 for i in range(n))
            samples={name:[] for name in cases}
            for repeat in range(repeats+3):
                order=list(cases);rng.shuffle(order)
                for name in order:
                    slug=f'{kind}-{n}-{name.replace(" ","-")}-{repeat}';usage=out/(slug+'.usage')
                    cmd=['/usr/bin/time','-f','%M','-o',str(usage),'taskset','-c','0',*map(str,cases[name])]
                    before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter_ns()
                    run=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
                    wall=time.perf_counter_ns()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN)
                    (out/(slug+'.txt')).write_text(run.stdout+run.stderr);assert run.returncode==0,(slug,run.stderr)
                    fields=list(map(int,run.stdout.split()));assert fields[0]==expected,(slug,fields,expected)
                    if kind=='append':assert len(fields)==4 and fields[2:]==[0,0]
                    else:assert len(fields)==1
                    if repeat>=3:samples[name].append({'wall_ns':wall,'phase_ns':fields[1] if kind=='append' else wall,'cpu_s':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,'peak_rss_bytes':int(usage.read_text())*1024,'checksum':fields[0],'command':cmd})
            for name,runs in samples.items():
                data['rows'].append({'workload':kind,'n':n,'implementation':name,'runs':runs})
                print(kind,n,name,f'{statistics.median(r["phase_ns"] for r in runs)/1e6:.3f} ms',f'{max(r["peak_rss_bytes"] for r in runs)/2**20:.2f} MiB',flush=True)
            save()
        files=[Path(__file__),ROOT/'tests/fixtures/language_bench.neo',ROOT/'examples/library_bench.neo',ROOT/'bench/usability/bun.ts',ROOT/'bench/rust/src/usability.rs',ROOT/'bench/rust/Cargo.toml',ROOT/'bench/rust/Cargo.lock']
        files +=[f for folder,pattern in [('neoc','*.py'),('stdlib','*.neo'),('runtime','*.neo')] for f in (ROOT/folder).glob(pattern)]
        data['source_sha256']={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
        data['valid']=True;data['finished']=time.time();data['load_end']=os.getloadavg();save()
    except BaseException as error:data['failure']=repr(error);save();raise
if __name__=='__main__':main()
