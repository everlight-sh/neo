#!/usr/bin/env python3
"""Fresh representative native Axon/Rust/Go compute regression measurements."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import resource
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
CASES={'mandel':['1200','1200','300'],'stencil':['1000000','20'],'nbody':['1024','3']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats',type=int,default=5)
    parser.add_argument('--report',type=Path,default=ROOT/'RESULTS-usability-compute-linux-2026-10-24.md')
    options=parser.parse_args();assert options.repeats>=1
    assert platform.system()=='Linux' and not os.environ.get('AXON_RUNNER')
    out=ROOT/'bench/usability/results'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d-%H%M%S-compute');out.mkdir(parents=True)
    (out/'measurement-harness.py').write_bytes(Path(__file__).read_bytes())
    data={'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'directory':str(out),'platform':platform.platform(),'repeats':options.repeats,'cases':CASES,'results':[],'valid':False}
    def execute(cmd,log,cwd=ROOT,env=None):
        r=subprocess.run(list(map(str,cmd)),cwd=cwd,env={**os.environ,**(env or {})},capture_output=True,text=True)
        (out/log).write_text(r.stdout+r.stderr);assert r.returncode==0,(cmd,r.stdout[-5000:],r.stderr)
        return r
    try:
        binaries={}
        for name in CASES:
            binary=out/('axon-'+name);execute([sys.executable,'-m','axonc','build',f'examples/{name}.ax','-o',binary,'--report'],name+'-axon-build.json')
            assert not execute(['nm','-u',binary],name+'-imports.txt').stdout.strip();binaries[name,'Axon']=binary
            go=out/('go-'+name);execute(['go','build','-o',go,'./'+name],name+'-go-build.log',ROOT/'bench/go',{'GOWORK':'off','GOTOOLCHAIN':'local','CGO_ENABLED':'0'});binaries[name,'Go']=go
        execute(['cargo','build','--release','--locked','--manifest-path','bench/rust/Cargo.toml','--bin','mandel','--bin','stencil','--bin','nbody'],'rust-build.log')
        for name in CASES:binaries[name,'Rust']=ROOT/'bench/rust/target/release'/name
        data['versions']={tool:execute([tool,'--version'] if tool!='go' else ['go','version'],tool+'-version.txt').stdout.strip() for tool in ('rustc','go','clang')}
        rng=random.Random(241024)
        for workers in (1,4):
            for name,args in CASES.items():
                runs={language:[] for language in ('Axon','Rust','Go')};expected=None
                for repeat in range(options.repeats+1):
                    order=list(runs);rng.shuffle(order)
                    for language in order:
                        cmd=['taskset','-c','0' if workers==1 else '0-3',str(binaries[name,language]),*args]
                        usage=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter()
                        r=subprocess.run(cmd,capture_output=True,text=True,timeout=60,env={**os.environ,'AXON_THREADS':str(workers),'RAYON_NUM_THREADS':str(workers),'GOMAXPROCS':str(workers)})
                        elapsed=time.perf_counter()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN)
                        (out/f'{name}-{workers}-{language}-{repeat}.log').write_text(r.stdout+r.stderr)
                        assert r.returncode==0,(name,language,r.stderr)
                        value=r.stdout.strip()
                        if expected is None:expected=value
                        assert value==expected or name=='nbody' and math.isclose(float(value),float(expected),rel_tol=1e-9),(name,language,expected,value)
                        if repeat:runs[language].append({'wall_s':elapsed,'cpu_s':after.ru_utime+after.ru_stime-usage.ru_utime-usage.ru_stime,'command':cmd,'output':value})
                for language,samples in runs.items():
                    data['results'].append({'workload':name,'workers':workers,'implementation':language,'runs':samples})
                    print(name,workers,language,f"{statistics.median(r['wall_s'] for r in samples)*1000:.2f} ms",flush=True)
                (out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')
        data['valid']=True;data['binary_sha256']={name+'-'+language:hashlib.sha256(file.read_bytes()).hexdigest() for (name,language),file in binaries.items()}
        data['source_sha256']={str(file.relative_to(ROOT)):hashlib.sha256(file.read_bytes()).hexdigest()
            for folder in ('axonc','runtime','bench/rust/src','bench/go/mandel','bench/go/stencil','bench/go/nbody')
            for file in (ROOT/folder).glob('*') if file.is_file()}
        data['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat();(out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')
        lines=['# Representative compute regressions — 2026-10-24','',
            f'Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. {options.repeats} process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.','',
            'Mandelbrot: 1,200×1,200, 300 iterations. Its outer dimension exceeds the 1,024-element Axon parallel-dispatch threshold; the retained initial 600×600 run did not spawn Axon workers. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.','',
            '| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |','|---|---:|---|---:|---:|---:|']
        for row in data['results']:
            values=[r['wall_s']*1000 for r in row['runs']]
            lines.append(f"| {row['workload']} | {row['workers']} | {row['implementation']} | {statistics.median(values):.2f} | {min(values):.2f}–{max(values):.2f} | {statistics.median(r['cpu_s'] for r in row['runs'])*1000:.2f} |")
        lines+=['',f'Raw commands, outputs, tool versions, builds, checksums and timings: `{out}`.','']
        options.report.write_text('\n'.join(lines))
        (out/'report.md').write_text('\n'.join(lines))
    except BaseException as exc:
        data['failure']=repr(exc);(out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n');raise

if __name__=='__main__':main()
