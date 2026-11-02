#!/usr/bin/env python3
"""Native process-level stencil comparison with unchanged workloads and baselines."""
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
CASES=[(1000000,20),(1000031,20),(65537,100),(8000000,20),(1000000,1)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats',type=int,default=21)
    parser.add_argument('--baseline',type=Path,default=ROOT/'.kernel-build/stencil-opt/baseline/stencil')
    args=parser.parse_args()
    assert args.repeats>=5 and platform.system()=='Linux' and not os.environ.get('AXON_RUNNER')
    out=ROOT/'bench/stencil/results'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d-%H%M%S')
    out.mkdir(parents=True);print('Artifacts:',out,flush=True)
    (out/'measurement-harness.py').write_bytes(Path(__file__).read_bytes())
    data={'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'directory':str(out),
          'repeats':args.repeats,'warmups':2,'cases':CASES,'results':[],'valid':False}
    def execute(cmd,log,cwd=ROOT,env=None):
        r=subprocess.run(list(map(str,cmd)),cwd=cwd,env={**os.environ,**(env or {})},capture_output=True,text=True,timeout=300)
        (out/log).write_text(r.stdout+r.stderr);assert r.returncode==0,(cmd,r.stdout[-5000:],r.stderr)
        return r
    try:
        baseline=ROOT/'.kernel-build/stencil-opt/baseline'
        assert (baseline/'stencil.ax').read_bytes()==(ROOT/'examples/stencil.ax').read_bytes(),'Workload changed'
        before=json.loads((baseline/'build.json').read_text())
        assert hashlib.sha256(args.baseline.read_bytes()).hexdigest()==before['binary_sha256']
        shutil.copy2(baseline/'build.json',out/'baseline-build.json')
        axon=out/'axon-stencil';go=out/'go-stencil'
        execute([sys.executable,'-m','axonc','build','examples/stencil.ax','--report','-o',axon],'axon-build.json')
        execute(['go','build','-o',go,'./stencil'],'go-build.log',ROOT/'bench/go',{'GOWORK':'off','GOTOOLCHAIN':'local','CGO_ENABLED':'0'})
        execute(['cargo','build','--release','--locked','--manifest-path','bench/rust/Cargo.toml','--bin','stencil'],'rust-build.log')
        rust=ROOT/'bench/rust/target/release/stencil'
        binaries={'Axon':axon,'Axon previous':args.baseline,'Rust':rust,'Go':go}
        for name in ('Axon','Axon previous'):
            file=binaries[name]
            assert not execute(['nm','-u',file],name+'-imports.txt').stdout.strip()
            assert 'INTERP' not in execute(['readelf','-l',file],name+'-headers.txt').stdout
            assert 'NEEDED' not in execute(['readelf','-d',file],name+'-dynamic.txt').stdout
        data['versions']={name:execute(command,name+'-version.txt').stdout.strip() for name,command in
            {'clang':['clang','--version'],'rust':['rustc','--version'],'go':['go','version'],'python':[sys.executable,'--version']}.items()}
        data['binary_sha256']={name:hashlib.sha256(file.read_bytes()).hexdigest() for name,file in binaries.items()}
        data['binary_bytes']={name:file.stat().st_size for name,file in binaries.items()}
        files=[Path(__file__),ROOT/'examples/stencil.ax',ROOT/'bench/rust/src/stencil.rs',ROOT/'bench/rust/Cargo.toml',ROOT/'bench/rust/Cargo.lock',ROOT/'bench/go/stencil/main.go']
        files += [p for folder in ('axonc','runtime') for p in (ROOT/folder).glob('*') if p.is_file()]
        data['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        historical=json.loads((ROOT/'bench/usability/results/2026-10-24-082918-compute/measurements.json').read_text())
        for source in ('bench/rust/src/stencil.rs','bench/go/stencil/main.go'):
            assert data['source_sha256'][source]==historical['source_sha256'][source],source+' changed'
        data['baseline_source_archive_sha256']=hashlib.sha256((baseline/'source.tar.gz').read_bytes()).hexdigest()
        rng=random.Random(2026102423)
        for workers in (1,4):
            for n,passes in CASES:
                samples={name:[] for name in binaries};expected=499998359740 if (n,passes)==(1000000,20) else None
                for repeat in range(args.repeats+2):
                    order=list(binaries);rng.shuffle(order)
                    for name in order:
                        slug=f'{workers}-{n}-{passes}-{name.replace(" ","-")}-{repeat}'
                        metrics=out/(slug+'.time')
                        cmd=['/usr/bin/time','-f','%M','-o',metrics,'taskset','-c','0' if workers==1 else '0-3',binaries[name],n,passes]
                        start_usage=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter()
                        r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=60,
                            env={**os.environ,'AXON_THREADS':str(workers),'RAYON_NUM_THREADS':str(workers),'GOMAXPROCS':str(workers)})
                        elapsed=time.perf_counter()-start;usage=resource.getrusage(resource.RUSAGE_CHILDREN)
                        (out/(slug+'.stdout')).write_text(r.stdout);(out/(slug+'.stderr')).write_text(r.stderr)
                        assert r.returncode==0,(name,n,passes,r.returncode,r.stdout,r.stderr)
                        value=int(r.stdout)
                        if expected is None:expected=value
                        assert value==expected,(name,n,passes,value,expected)
                        if repeat>=2:samples[name].append({'wall_s':elapsed,'cpu_s':usage.ru_utime+usage.ru_stime-start_usage.ru_utime-start_usage.ru_stime,
                            'peak_rss_bytes':int(metrics.read_text().strip())*1024,'checksum':value,'command':list(map(str,cmd))})
                for name,runs in samples.items():
                    data['results'].append({'elements':n,'passes':passes,'workers':workers,'implementation':name,'runs':runs})
                    print(n,passes,workers,name,f'{statistics.median(r["wall_s"] for r in runs)*1000:.2f} ms',flush=True)
                (out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')
        data['valid']=True;data['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        report=ROOT/'RESULTS-stencil-optimized-linux-2026-10-24.md';write_report(data,report);shutil.copy2(report,out/'report.md')
    except BaseException as exc:
        data['failure']=repr(exc);raise
    finally:(out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')


def write_report(data,path):
    lines=['# Stencil after compiler and kernel-worker optimization — 2026-10-24','',
        f'Native ARM64 Linux on Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Measured {data["started"]}. {data["repeats"]} measured process runs after two warmups; seeded shuffled implementation order every round. One worker is pinned to CPU 0; four workers to CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. GNU time/taskset startup, initialization, allocation, every pass, checksum and shutdown are included. No emulation or persistent benchmark service. Host load can vary, so the previous Axon executable is rerun in the same interleaved rounds.','',
        'Axon, Rust/Rayon and Go sources are unchanged from the prior compute report: signed i64 data, the same seed, the same 3-point recurrence modulo 1,000,003, copied endpoints and all requested passes. Every checksum must agree across all four executables. Axon retains checked application arithmetic. No tiling, reduced iteration count, cached result, or changes to competitors.','',
        '| Elements | Passes | Workers | Implementation | Median wall ms | Min–max ms | Median CPU ms | Max process peak RSS MiB |',
        '|---:|---:|---:|---|---:|---:|---:|---:|']
    for row in data['results']:
        runs=row['runs'];times=[r['wall_s']*1000 for r in runs]
        lines.append(f'| {row["elements"]:,} | {row["passes"]} | {row["workers"]} | {row["implementation"]} | {statistics.median(times):.2f} | {min(times):.2f}–{max(times):.2f} | {statistics.median(r["cpu_s"] for r in runs)*1000:.2f} | {max(r["peak_rss_bytes"] for r in runs)/2**20:.2f} |')
    lines += ['', '## Changes and limits','',
        '- General scalar array comprehensions now emit four-lane vectors for arithmetic and affine reads. The compiler intersects every source array’s valid interval, including speculative branch loads; prefix, suffix and vector tails remain scalar. Checked arithmetic uses masked overflow checks unless existing lexical/whole-program facts prove safety. Bounded remainders also lower inside vectors.',
        '- Allocation-free vector bodies on Linux use raw clone(CLONE_VM | SIGCHLD) workers with separate aligned stacks and waitable process identities. Axon owns scheduling, stack allocation, joins and spawn-failure fallback. A small compiler-emitted ARM64/x86-64 stack-switch boundary makes the raw syscall; it calls no library. Workers never touch the allocator. Allocating bodies retain isolated fork workers. Stacks and contexts stay alive through the join.',
        '- The runtime still creates workers per parallel region; this does not implement a persistent pool. macOS keeps fork workers and its platform-required libSystem loader command. Native performance was measured only on Linux ARM64; x86-64 correctness under emulation is separate evidence.',
        '- RSS is GNU time’s maximum per-process resident high-water mark, not summed worker RSS, cgroup memory or virtual reservations. Shared-address worker mappings must not be counted repeatedly. CPU includes waited descendants.',
        '- Linux Axon executables have no undefined symbols, ELF interpreter, DT_NEEDED entry, C runtime or shared-library dependency. Python/LLVM remain build tools. See retained nm/readelf output.', '',
        '## Binary size','', '| Implementation | Bytes |','|---|---:|']
    for name,size in data['binary_bytes'].items():lines.append(f'| {name} | {size:,} |')
    lines += ['',f'Raw commands, outputs, build reports, tool versions, checksums, samples and hashes: `{data["directory"]}`.','']
    path.write_text('\n'.join(lines))

if __name__=='__main__':main()
