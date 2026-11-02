#!/usr/bin/env python3
"""Native, interleaved rerun of the unchanged dynamic-JSON usability workload."""
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats',type=int,default=9)
    parser.add_argument('--baseline',type=Path,default=ROOT/'.kernel-build/json-opt/baseline/library')
    parser.add_argument('--report',type=Path,default=ROOT/'RESULTS-json-optimized-linux-2026-10-24.md')
    args=parser.parse_args()
    assert platform.system()=='Linux' and platform.machine() in ('arm64','aarch64') and not os.environ.get('NEO_RUNNER')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d-%H%M%S')
    out=ROOT/'bench/json/results'/stamp;out.mkdir(parents=True)
    print('Artifacts:',out,flush=True)
    data={'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'directory':str(out),'platform':platform.platform(),
          'repeats':args.repeats,'warmups':2,'cpu_affinity':[0],'results':[],'valid':False}
    def command(cmd,log):
        result=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,text=True)
        (out/log).write_text(result.stdout+result.stderr)
        assert result.returncode==0,(cmd,result.stdout[-5000:],result.stderr)
        return result
    binary=out/'axon-json'
    command([sys.executable,'-m','neoc','build','examples/library_bench.neo','-o',binary,'--report'],'axon-build.json')
    command(['cargo','build','--release','--locked','--manifest-path','bench/rust/Cargo.toml','--bin','usability'],'rust-build.log')
    for name,file in [('Axon',binary),('Axon previous',args.baseline)]:
        assert file.is_file(),file
        assert not command(['nm','-u',file],name+'-imports.txt').stdout.strip()
        assert 'INTERP' not in command(['readelf','-l',file],name+'-headers.txt').stdout
        assert 'NEEDED' not in command(['readelf','-d',file],name+'-dynamic.txt').stdout
    original=ROOT/'.kernel-build/json-opt/baseline/library_bench.neo'
    assert original.read_bytes()==(ROOT/'examples/library_bench.neo').read_bytes(),'The original workload must remain unchanged'
    rust=ROOT/'bench/rust/target/release/usability'
    data['versions']={name:command(cmd,name+'-version.txt').stdout.strip() for name,cmd in
        {'clang':['clang','--version'],'rust':['rustc','--version'],'bun':['bun','--version'],'python':[sys.executable,'--version']}.items()}
    data['binary_sha256']={name:hashlib.sha256(file.read_bytes()).hexdigest() for name,file in [('Axon',binary),('Axon previous',args.baseline),('Rust',rust),('Bun',Path(shutil.which('bun')))]}
    data['binary_bytes']={name:file.stat().st_size for name,file in [('Axon',binary),('Axon previous',args.baseline),('Rust',rust),('Bun runtime',Path(shutil.which('bun')))]}
    rng=random.Random(2026102417)
    try:
        for count in (10000,100000,1000000):
            cases={'Axon':[binary,'0',count],'Axon previous':[args.baseline,'0',count],
                'Rust':[rust,'parse',count],'Bun':['bun',ROOT/'bench/usability/bun.ts','parse',count]}
            runs={name:[] for name in cases};expected=sum(i%1000+14 for i in range(count))
            for repeat in range(args.repeats+2):
                order=list(cases);rng.shuffle(order)
                for name in order:
                    slug=f'{count}-{name.replace(" ","-")}-{repeat}'
                    metrics=out/(slug+'.time')
                    cmd=['/usr/bin/time','-f','%M','-o',metrics,'taskset','-c','0',*cases[name]]
                    before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter()
                    result=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=120,env={**os.environ,'NEO_THREADS':'1'})
                    elapsed=time.perf_counter()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN)
                    (out/(slug+'.stdout')).write_text(result.stdout);(out/(slug+'.stderr')).write_text(result.stderr)
                    assert result.returncode==0 and int(result.stdout)==expected,(name,count,result.returncode,result.stdout,result.stderr)
                    if repeat>=2:runs[name].append({'wall_s':elapsed,'cpu_s':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                        'peak_rss_bytes':int(metrics.read_text().strip())*1024,'checksum':int(result.stdout),'command':list(map(str,cmd))})
            for name,samples in runs.items():
                data['results'].append({'documents':count,'implementation':name,'runs':samples})
                print(count,name,f'{statistics.median(r["wall_s"] for r in samples)*1000:.2f} ms',flush=True)
            (out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')
        files=[Path(__file__),ROOT/'examples/library_bench.neo',ROOT/'bench/rust/src/usability.rs',ROOT/'bench/rust/Cargo.toml',ROOT/'bench/rust/Cargo.lock',ROOT/'bench/usability/bun.ts']
        files += [p for folder in ('neoc','runtime','stdlib') for p in (ROOT/folder).glob('*') if p.is_file()]
        data['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        (out/'measurement-harness.py').write_bytes(Path(__file__).read_bytes())
        data['valid']=True;data['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_report(data,args.report)
        shutil.copy2(args.report,out/'report.md')
    except BaseException as exc:
        data['failure']=repr(exc);raise
    finally:(out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')


def write_report(data,path):
    lines=['# Dynamic JSON workload after optimization — 2026-10-24','',
        f'Measured {data["started"]} on native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Each command is pinned to CPU 0; NEO_THREADS=1. No CPU emulation. {data["repeats"]} measured process runs after two warmups, with implementation order shuffled each round. GNU time/taskset startup, construction, parsing, field access, destruction and process shutdown are included.','',
        'This is the unchanged `examples/library_bench.neo` workload from the usability report: construct a different JSON object each iteration, fully validate/parse it, read integer id and decoded UTF-8 name, count array elements and checksum the result. Rust still uses the unmodified optimized serde_json::Value implementation; Bun still uses the unmodified JSON.parse implementation. The previous Axon executable is preserved and rerun in this session. Every output is checked. This measures the complete JSON workflow, not an isolated parser instruction or every JSON input shape.','',
        '| Documents | Implementation | Median wall ms | Min–max ms | Median CPU ms | Max process peak RSS MiB |',
        '|---:|---|---:|---:|---:|---:|']
    for row in data['results']:
        samples=row['runs'];times=[r['wall_s']*1000 for r in samples]
        lines.append(f'| {row["documents"]:,} | {row["implementation"]} | {statistics.median(times):.2f} | {min(times):.2f}–{max(times):.2f} | {statistics.median(r["cpu_s"] for r in samples)*1000:.2f} | {max(r["peak_rss_bytes"] for r in samples)/2**20:.2f} |')
    lines+=['','## What changed','',
        '- UTF-8 validation is integrated with string scanning; strict validation, Unicode scalar rules and the depth limit remain enforced.',
        '- Object validation builds member offsets in the same pass. Lookups use that index, and reverse search preserves last-duplicate-key semantics. The index grows geometrically rather than with the byte size of string payloads.',
        '- `sealed type` restricts construction/updates to the declaring module. Parsed JSON values retain their validation invariant; callers can read fields and copy bytes, but cannot forge raw/kind/index combinations.',
        '- Pure internal record calls borrow live arguments. Escaping children acquire ownership before return; temporaries remain alive through calls. Empty arrays are canonical non-owning values, and static string fields stay immutable.',
        '- Bounded nonrecursive functions called with literal strings receive an inlining hint. Allocator headers cache their size-class index instead of recomputing it on every release.','',
        'Axon remains source-slice/index based, while Rust constructs serde_json::Value and Bun constructs JavaScript values. Their representations and memory policies differ. Native x86 performance, other parser libraries, arbitrary schemas, and universal language-performance rankings are not established here. Local VM measurements share the physical host; inspect the complete run ranges. Peak RSS is GNU time accounting, not Docker working set or PSS.','',
        f'Raw commands, outputs, tool versions, binary/source hashes, dependency audits and timings: `{data["directory"]}`.','']
    path.write_text('\n'.join(lines))


if __name__=='__main__':main()
