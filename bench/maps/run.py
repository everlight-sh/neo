#!/usr/bin/env python3
"""Matched decimal string-map operations, Linux checkpoint memory, immutable rivals."""
import argparse,hashlib,json,os,platform,random,select,statistics,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PHASES=['insert','lookup','steady','update','lookup_updated','delete','lookup_remaining']
def memory(pid):
    status=Path(f'/proc/{pid}/status').read_text();fields={line.split(':')[0]:line.split(':')[1].strip() for line in status.splitlines() if ':' in line}
    smaps=Path(f'/proc/{pid}/smaps_rollup').read_text();parts={line.split(':')[0]:line.split(':')[1].strip() for line in smaps.splitlines() if ':' in line}
    return {'rss_bytes':int(fields['VmRSS'].split()[0])*1024,'peak_rss_bytes':int(fields['VmHWM'].split()[0])*1024,'pss_bytes':int(parts['Pss'].split()[0])*1024}
def expected(phase,n):
    checksum=7*n*(n-1)//2 if phase in ('lookup','steady') else 11*n*(n-1)//2 if phase=='lookup_updated' else 11*(n//2)**2 if phase=='lookup_remaining' else 0
    return checksum,n//2 if phase in ('delete','lookup_remaining') else n
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--repeats',type=int,default=7);p.add_argument('--include-after',action='store_true');p.add_argument('--sizes',nargs='+',type=int,default=[100000,1000000]);a=p.parse_args()
    assert platform.system()=='Linux' and not os.environ.get('NEO_RUNNER') and a.repeats>=3
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);base=a.baseline.resolve();env={**os.environ,'NEO_THREADS':'1','GOMAXPROCS':'1','GOWORK':'off','CGO_ENABLED':'0','GOTOOLCHAIN':'local'}
    data={'valid':False,'platform':platform.platform(),'machine':platform.machine(),'started':time.time(),'warmups':2,'repeats':a.repeats,'affinity':[0],'phases':PHASES,'rows':[],'sources':{},'versions':{},'note':'Ordinary owned decimal string maps. Axon 2-GiB arena limit and value/alias semantics differ from standard Rust/Go maps. Go steady checkpoint explicitly runs GC; normal insert checkpoint does not. Timed phases exclude sampling/acknowledgements. Shared physical host.'}
    def save():(out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')
    def command(cmd,name,cwd=ROOT,extra=None):
        r=subprocess.run(list(map(str,cmd)),cwd=cwd,env={**env,**(extra or {})},capture_output=True,text=True,timeout=180);(out/(name+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,(name,r.stdout[-2000:],r.stderr[-2000:]);return r.stdout
    bins={}
    for label,compiler in [('Axon before',base)]+([('Axon after',ROOT)] if a.include_after else []):
        binary=out/label.replace(' ','-');report=json.loads(command(['python3','-m','neoc','build',ROOT/'bench/maps/workload.neo','-o',binary,'--report'],label+'-build',compiler,{'PYTHONPATH':str(compiler)}));assert not report['undefined_symbols'];bins[label]=binary
        for tool,flag in [('nm','-u'),('readelf','-l'),('readelf','-d')]:
            s=command([tool,flag,binary],label+'-'+tool+flag);assert not s.strip() if tool=='nm' else 'INTERP' not in s and 'NEEDED' not in s
    bins['Rust']=out/'Rust';bins['Go']=out/'Go'
    command(['rustc','-O','-C','lto=fat','-C','codegen-units=1','bench/maps/rust.rs','-o',bins['Rust']],'rust-build')
    command(['go','build','-o',bins['Go'],'bench/maps/go.go'],'go-build')
    for tool,args in [('rustc',['--version']),('go',['version']),('clang',['--version'])]:data['versions'][tool]=command([tool,*args],tool+'-version').splitlines()[0]
    for name in ['workload.neo','rust.rs','go.go','run.py']:
        source=ROOT/'bench/maps'/name;data['sources'][name]=hashlib.sha256(source.read_bytes()).hexdigest();(out/name).write_bytes(source.read_bytes())
    data['binaries']={k:{'sha256':hashlib.sha256(v.read_bytes()).hexdigest(),'bytes':v.stat().st_size} for k,v in bins.items()};data['load_start']=os.getloadavg();rng=random.Random(2510255)
    try:
        for n in a.sizes:
            for reserved in [0,1]:
                samples={name:[] for name in bins}
                for repeat in range(a.repeats+2):
                    order=list(bins);rng.shuffle(order)
                    for name in order:
                        slug=f'{n}-{reserved}-{name.replace(" ","-")}-{repeat}';cmd=['taskset','-c','0',str(bins[name]),str(n),str(reserved)];records=[]
                        with (out/(slug+'.stderr')).open('w') as error:
                            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=error,env=env)
                            try:
                                for phase in PHASES:
                                    assert select.select([proc.stdout],[],[],60)[0],(slug,phase,'timeout')
                                    line=proc.stdout.readline().decode();fields=line.split();assert len(fields)==4,(slug,phase,line)
                                    actual,ns,checksum,count=fields;assert actual==phase and (int(checksum),int(count))==expected(phase,n),(slug,line,expected(phase,n))
                                    records.append({'phase':phase,'ns':int(ns),'checksum':int(checksum),'count':int(count),**memory(proc.pid)});proc.stdin.write(b'x');proc.stdin.flush()
                                assert proc.wait(timeout=10)==0,(slug,proc.returncode)
                            finally:
                                if proc.poll() is None:proc.kill();proc.wait()
                        (out/(slug+'.json')).write_text(json.dumps(records,indent=2)+'\n')
                        if repeat>=2:samples[name].append({'command':cmd,'phases':records})
                for name,runs in samples.items():
                    row={'rows':n,'reserved':bool(reserved),'implementation':name,'runs':runs,'medians':{phase:{metric:statistics.median(next(v for v in r['phases'] if v['phase']==phase)[metric] for r in runs) for metric in ['ns','rss_bytes','peak_rss_bytes','pss_bytes']} for phase in PHASES}};data['rows'].append(row)
                    print(n,'reserved' if reserved else 'grow',name,' '.join(f'{s}={row["medians"][s]["ns"]/1e6:.2f}ms' for s in ['insert','lookup','update','delete']),f'peak={row["medians"]["lookup_remaining"]["peak_rss_bytes"]/1048576:.2f}MiB steady={row["medians"]["steady"]["rss_bytes"]/1048576:.2f}MiB',flush=True)
                save()
        data['valid']=True;data['load_end']=os.getloadavg();save()
    except BaseException as error:data['failure']=repr(error);save();raise
if __name__=='__main__':main()
