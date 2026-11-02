#!/usr/bin/env python3
"""Native Linux core collection comparisons against the preserved compiler."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import resource
import shutil
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
CASES={0:[1000,10000,50000],1:[100,1000,10000],2:[100,1000,5000]}
LABELS={0:'vector append + checksum',1:'integer sort + weighted checksum',2:'string map insert + complete lookup'}


def expected(mode,n):
    if mode==0:return sum(i%997 for i in range(n))
    if mode==1:return sum((i+1)*value for i,value in enumerate(sorted((n-i)%997 for i in range(n))))
    return 7*n*(n-1)//2


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);parser.add_argument('--repeats',default=7,type=int)
    args=parser.parse_args();assert platform.system()=='Linux' and not os.environ.get('NEO_RUNNER') and args.repeats>=5
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    baseline=ROOT/'.kernel-build/language-v01/baseline';manifest=json.loads((baseline/'sources.json').read_text())
    for name,digest in manifest.items():assert hashlib.sha256((baseline/name).read_bytes()).hexdigest()==digest,name
    data={'valid':False,'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'machine':platform.machine(),'platform':platform.platform(),
          'warmups':2,'repeats':args.repeats,'affinity':[0],'rows':[],'profiles':[],'baseline_sources':manifest}
    source=ROOT/'tests/fixtures/language_bench.neo';source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    (out/'workload.neo').write_bytes(source.read_bytes());(out/'measurement-harness.py').write_bytes(Path(__file__).read_bytes())
    def save():(out/'measurements.json').write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
    def command(cmd,log,cwd=ROOT,env=None):
        result=subprocess.run(list(map(str,cmd)),cwd=cwd,env={**os.environ,**(env or {})},capture_output=True,text=True,timeout=180)
        (out/log).write_text(result.stdout+result.stderr);assert result.returncode==0,(cmd,result.stdout[-2000:],result.stderr)
        return result
    try:
        data['versions']={name:command(cmd,name+'-version.txt').stdout.strip() for name,cmd in {'clang':['clang','--version'],'python':[sys.executable,'--version'],'kernel':['uname','-a']}.items()}
        data['load_start']=os.getloadavg();binaries={};profiles={}
        profile_root=out/'baseline-profile'
        for folder in ('neoc','runtime','stdlib'):shutil.copytree(baseline/folder,profile_root/folder)
        runtime=profile_root/'runtime/core.neo';before=runtime.read_text()
        marker='export effect fn ax_alloc (bytes : i64) -> ptr\n  = '
        assert marker in before
        after=before.replace(marker,marker+'let count=store_i64(runtime_state(),64,load_i64(runtime_state(),64)+1) in\n    let traffic=store_i64(runtime_state(),80,load_i64(runtime_state(),80)+bytes) in\n    ',1)
        runtime.write_text(after);data['baseline_profile_patch']='Only two cumulative allocation counters at state offsets 64 and 80; timing uses the unmodified baseline.'
        for label,compiler,stats in [('before',baseline,False),('after',ROOT,False),('before-profile',profile_root,True),('after-profile',ROOT,True)]:
            binary=out/label
            env={'PYTHONPATH':str(compiler),'NEO_ALLOC_STATS':'1' if stats else '0'}
            built=command([sys.executable,'-m','neoc','build',source,'-o',binary,'--report'],label+'-build.json',compiler,env)
            report=json.loads(built.stdout);assert report['undefined_symbols']==[]
            for tool,options in [('nm',['-u']),('readelf',['-l']),('readelf',['-d'])]:
                text=command([tool,*options,binary],label+'-'+tool+options[0]+'.txt').stdout
                assert not text.strip() if tool=='nm' else 'INTERP' not in text and 'NEEDED' not in text
            (profiles if stats else binaries)[label.split('-')[0]]=binary
        rng=random.Random(2026102452)
        for mode,sizes in CASES.items():
            for n in sizes:
                runs={label:[] for label in binaries}
                for trial in range(args.repeats+2):
                    order=list(binaries);rng.shuffle(order)
                    for label in order:
                        slug=f'{mode}-{n}-{label}-{trial}';rss=out/(slug+'.rss')
                        cmd=['/usr/bin/time','-f','%M','-o',str(rss),'taskset','-c','0',str(binaries[label]),str(mode),str(n)]
                        before_usage=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter_ns()
                        result=subprocess.run(cmd,capture_output=True,text=True,timeout=120,env={**os.environ,'NEO_THREADS':'1'})
                        elapsed=time.perf_counter_ns()-start;usage=resource.getrusage(resource.RUSAGE_CHILDREN)
                        (out/(slug+'.stdout')).write_text(result.stdout);(out/(slug+'.stderr')).write_text(result.stderr)
                        assert result.returncode==0,(slug,result.stderr)
                        checksum,phase,requests,traffic=map(int,result.stdout.split());assert checksum==expected(mode,n),(slug,checksum)
                        if trial>=2:runs[label].append({'wall_ns':elapsed,'phase_ns':phase,'cpu_s':usage.ru_utime+usage.ru_stime-before_usage.ru_utime-before_usage.ru_stime,
                            'peak_rss_bytes':int(rss.read_text().strip())*1024,'checksum':checksum,'command':cmd})
                for label,samples in runs.items():data['rows'].append({'mode':mode,'workload':LABELS[mode],'n':n,'implementation':label,'runs':samples})
                for label,binary in profiles.items():
                    result=command(['taskset','-c','0',binary,mode,n],f'{mode}-{n}-{label}-profile.txt',env={'NEO_THREADS':'1'})
                    checksum,phase,requests,traffic=map(int,result.stdout.split());assert checksum==expected(mode,n)
                    data['profiles'].append({'mode':mode,'n':n,'implementation':label,'requests':requests,'requested_bytes':traffic})
                before_row=runs['before'];after_row=runs['after']
                print(LABELS[mode],n,'before',round(statistics.median(r['phase_ns'] for r in before_row)/1e6,4),'ms after',round(statistics.median(r['phase_ns'] for r in after_row)/1e6,4),'ms',flush=True);save()
        data['current_scaling']=[]
        for mode in (0,1,2):
            for n in (100000,1000000):
                samples=[]
                for trial in range(args.repeats+2):
                    slug=f'{mode}-{n}-scale-{trial}';rss=out/(slug+'.rss')
                    cmd=['/usr/bin/time','-f','%M','-o',rss,'taskset','-c','0',binaries['after'],mode,n]
                    before_usage=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter_ns()
                    run=command(cmd,slug+'.txt',env={'NEO_THREADS':'1'})
                    elapsed=time.perf_counter_ns()-start;usage=resource.getrusage(resource.RUSAGE_CHILDREN)
                    checksum,phase,requests,traffic=map(int,run.stdout.split());assert checksum==expected(mode,n)
                    if trial>=2:samples.append({'phase_ns':phase,'wall_ns':elapsed,'cpu_s':usage.ru_utime+usage.ru_stime-before_usage.ru_utime-before_usage.ru_stime,
                        'peak_rss_bytes':int(rss.read_text().strip())*1024,'checksum':checksum,'command':list(map(str,cmd))})
                data['current_scaling'].append({'mode':mode,'n':n,'runs':samples})
                print('Current scaling',LABELS[mode],n,round(statistics.median(r['phase_ns'] for r in samples)/1e6,3),'ms',flush=True);save()
        data['binary_sha256']={label:hashlib.sha256(binary.read_bytes()).hexdigest() for label,binary in {**binaries,**{k+'-profile':v for k,v in profiles.items()}}.items()}
        data['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder,pattern in [('neoc','*.py'),('runtime','*.neo'),('stdlib','*.neo')] for p in (ROOT/folder).glob(pattern)}
        assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
        for name,digest in manifest.items():assert hashlib.sha256((baseline/name).read_bytes()).hexdigest()==digest,name
        data['load_end']=os.getloadavg();data['valid']=True;data['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
    except BaseException as exc:data['failure']=repr(exc);save();raise


if __name__=='__main__':main()
