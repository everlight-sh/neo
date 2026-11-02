#!/usr/bin/env python3
"""Native runtime microbenchmarks, checksum-verified and without competitors."""
import argparse,datetime,hashlib,json,os,platform,random,statistics,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);parser.add_argument('--repeats',default=7,type=int);args=parser.parse_args()
    assert platform.system()=='Linux' and not os.environ.get('NEO_RUNNER') and args.repeats>=5
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);binary=out/'runtime'
    source=ROOT/'tests/fixtures/agent_runtime_bench.neo';(out/'workload.neo').write_bytes(source.read_bytes());(out/'harness.py').write_bytes(Path(__file__).read_bytes())
    built=subprocess.run(['python3','-m','neoc','build',str(source),'-o',str(binary),'--report'],cwd=ROOT,capture_output=True,text=True)
    (out/'build.json').write_text(built.stdout+built.stderr);assert built.returncode==0,built.stdout[-3000:]
    assert not json.loads(built.stdout)['undefined_symbols']
    data={'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'valid':False,'platform':platform.platform(),'affinity':[0],'workers':1,'warmups':2,'repeats':args.repeats,'rows':[],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'load_start':os.getloadavg(),'note':'Shared host/VM, no absolute isolation; throughput is for these concrete workloads. Function-value loop may be inlined/devirtualized by LLVM.'}
    rng=random.Random(251026)
    modes=[(0,'optimized function-value loop',1000000),(1,'bounded FIFO push + pop',100000),(2,'managed resource adopt + borrow + release',100000),(3,'one cooperative task tick',100000)]
    samples={mode:[] for mode,_,_ in modes}
    for repeat in range(args.repeats+2):
        order=list(modes);rng.shuffle(order)
        for mode,label,n in order:
            usage=out/f'usage-{mode}-{repeat}.txt';command=['/usr/bin/time','-f','%U %S %M','-o',str(usage),'taskset','-c','0',str(binary),str(mode),str(n)]
            start=time.perf_counter_ns();run=subprocess.run(command,capture_output=True,text=True,timeout=60,env={**os.environ,'NEO_THREADS':'1'});wall=time.perf_counter_ns()-start
            (out/f'run-{mode}-{repeat}.txt').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stderr
            checksum,phase_ns=map(int,run.stdout.split());expected=n*(n+1)//2 if mode==0 else n*(n-1)//2 if mode==1 else n*64 if mode==2 else n
            assert checksum==expected,(mode,checksum,expected)
            user,system,rss=map(float,usage.read_text().split())
            if repeat>=2:samples[mode].append({'command':command,'checksum':checksum,'phase_ns':phase_ns,'wall_ns':wall,'cpu_s':user+system,'peak_rss_bytes':int(rss*1024)})
    for mode,label,n in modes:
        runs=samples[mode];row={'label':label,'iterations':n,'runs':runs,'median_ns_per_iteration':statistics.median(r['phase_ns'] for r in runs)/n,'median_peak_rss_bytes':statistics.median(r['peak_rss_bytes'] for r in runs)};data['rows'].append(row);print(label,round(row['median_ns_per_iteration'],2),'ns/iteration',round(row['median_peak_rss_bytes']/1048576,2),'MiB',flush=True)
    data['valid']=True;data['load_end']=os.getloadavg();(out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':main()
