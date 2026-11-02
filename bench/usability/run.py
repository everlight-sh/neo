#!/usr/bin/env python3
"""Native Linux usability workloads; raw timings, outputs and checksums retained."""
import argparse
import concurrent.futures
import datetime
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import hashlib
import importlib.util
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
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests'))
import usability_smoke as smoke

def main():
    p=argparse.ArgumentParser();p.add_argument('--repeats',type=int,default=5)
    p.add_argument('--report',type=Path,default=ROOT/'RESULTS-usability-linux-2026-10-24.md');args=p.parse_args()
    assert platform.system()=='Linux' and not os.environ.get('NEO_RUNNER'),'Performance requires native Linux, not QEMU'
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d-%H%M%S')
    out=ROOT/'bench/usability/results'/stamp;out.mkdir(parents=True)
    smoke.OUT.mkdir(parents=True,exist_ok=True)
    print('Artifacts:',out,flush=True)
    data={'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'directory':str(out),'repeats':args.repeats,
        'platform':platform.platform(),'architecture':platform.machine(),'process':[],'build':[],'applications':[],'commands':[],'valid':False}
    workdir=tempfile.TemporaryDirectory(prefix='axon-usability-bench-');work=Path(workdir.name)
    def save(): (out/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')
    def command(cmd,log,env=None):
        data['commands'].append(list(map(str,cmd)))
        result=subprocess.run(list(map(str,cmd)),cwd=ROOT,env={**os.environ,**(env or {})},capture_output=True,text=True)
        (out/log).write_text(result.stdout+result.stderr)
        assert result.returncode==0,(cmd,result.stdout[-5000:],result.stderr)
        return result
    try:
        data['versions']={tool:command(cmd,tool+'-version.txt').stdout.strip() for tool,cmd in {
            'python':[sys.executable,'--version'],'clang':['clang','--version'],'rust':['rustc','--version'],'bun':['bun','--version']}.items()}
        binaries={}
        for name,source in [('json-cli','examples/json-cli/main.neo'),('library','examples/library_bench.neo'),('notes','examples/notes/main.neo'),('webhook','examples/webhook/main.neo'),('hello','examples/hello.neo')]:
            binary=out/name;binaries[name]=binary
            command([sys.executable,'-m','neoc','build',source,'-o',binary,'--report'],name+'-build.json')
            command(['nm','-u',binary],name+'-imports.txt')
            assert not (out/(name+'-imports.txt')).read_text().strip()
        rust=ROOT/'bench/rust/target/release/usability'
        command(['cargo','build','--release','--locked','--manifest-path','bench/rust/Cargo.toml','--bin','usability'],'rust-build.log')
        data['binary_bytes']={name:file.stat().st_size for name,file in binaries.items()};data['binary_bytes']['Rust']=rust.stat().st_size
        data['binary_bytes']['Bun runtime']=Path(shutil.which('bun')).stat().st_size
        data['binary_sha256']={name:hashlib.sha256(file.read_bytes()).hexdigest() for name,file in binaries.items()}
        def timed(cmd,slug,repeat):
            log=work/f'{slug}-{repeat}.time';usage=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter()
            result=subprocess.run(['/usr/bin/time','-f','%M','-o',str(log),'taskset','-c','0',*map(str,cmd)],capture_output=True,timeout=120,env={**os.environ,'NEO_THREADS':'1'})
            elapsed=time.perf_counter()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN)
            shutil.copy2(log,out/log.name)
            (out/f'{slug}-{repeat}.stdout').write_bytes(result.stdout);(out/f'{slug}-{repeat}.stderr').write_bytes(result.stderr)
            assert result.returncode==0,(cmd,result.returncode,result.stderr)
            return {'wall_s':elapsed,'cpu_s':after.ru_utime+after.ru_stime-usage.ru_utime-usage.ru_stime,
                'peak_rss_bytes':int(log.read_text().strip())*1024,'command':list(map(str,cmd)),'stdout':result.stdout.decode()}
        rng=random.Random(241024)
        for count in (100,1000):
            rows=[{'id':i,'name':f'café 🚀 <{i}>','score':rng.randrange(-1000,1000)} for i in range(count)]
            source=work/f'input-{count}.json';source.write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':')));shutil.copy2(source,out/source.name)
            expected=sorted([row for row in rows if row['score']>=100],key=lambda row:row['score'])
            variants={'Axon':[binaries['json-cli']],'Rust':[rust],'Bun':['bun',ROOT/'bench/usability/bun.ts']}
            runs={name:[] for name in variants}
            for repeat in range(args.repeats+1):
                order=list(variants);rng.shuffle(order)
                for name in order:
                    target=work/f'output-{count}-{name}.json';cmd=variants[name]+[source,target,'100']
                    run=timed(cmd,f'cli-{count}-{name}',repeat)
                    assert json.loads(target.read_text())==expected,(name,count)
                    shutil.copy2(target,out/target.name)
                    if repeat:runs[name].append(run)
            for name,values in runs.items():
                data['process'].append({'workload':'JSON file CLI','size':count,'server':name,'runs':values})
                print('CLI',count,name,f"{statistics.median(r['wall_s'] for r in values)*1000:.2f} ms",flush=True)
            save()
        for count in (1000,10000):
            variants={'Axon':[binaries['library'],'0',str(count)],'Rust':[rust,'parse',str(count)],'Bun':['bun',ROOT/'bench/usability/bun.ts','parse',str(count)]}
            expected=sum(i%1000+14 for i in range(count));runs={name:[] for name in variants}
            for repeat in range(args.repeats+1):
                order=list(variants);rng.shuffle(order)
                for name in order:
                    run=timed(variants[name],f'parse-{count}-{name}',repeat)
                    assert int(run['stdout'])==expected,(name,count,run['stdout'],expected)
                    if repeat:runs[name].append(run)
            for name,values in runs.items():
                data['process'].append({'workload':'Render + parse dynamic JSON + access fields','size':count,'server':name,'runs':values})
                print('JSON',count,name,f"{statistics.median(r['wall_s'] for r in values)*1000:.2f} ms",flush=True)
            save()
        count=10000;expected=sum(i%1000+11+len(str(i%1000)) for i in range(count));values=[]
        for repeat in range(args.repeats+1):
            run=timed([binaries['library'],'1',str(count)],'collections',repeat);assert int(run['stdout'])==expected
            if repeat:values.append(run)
        data['process'].append({'workload':'Integer/UTF-8/vector/map operations','size':count,'server':'Axon','runs':values});save()
        for name,source in [('hello','examples/hello.neo'),('json-cli','examples/json-cli/main.neo'),('notes','examples/notes/main.neo'),('webhook','examples/webhook/main.neo')]:
            for kind,repeats in [('cold',3),('warm',5)]:
                samples=[]
                for repeat in range(repeats):
                    cmd=[sys.executable,'-m','neoc','build',source,'-o',str(binaries[name]),'--report']
                    if kind=='cold':cmd.append('--no-cache')
                    run=timed(cmd,f'build-{name}-{kind}',repeat);report=json.loads(run['stdout'])
                    assert report['build']['cache']==('miss' if kind=='cold' else 'hit')
                    samples.append(run)
                data['build'].append({'name':name,'kind':kind,'runs':samples})
                print('Build',name,kind,f"{statistics.median(r['wall_s'] for r in samples)*1000:.2f} ms",flush=True)
                save()
        # Stateful application figures include client and real filesystem I/O.
        os.sched_setaffinity(0,{4,5,6,7})
        for workers in (1,4):
            for repeat in range(3):
                with tempfile.TemporaryDirectory(prefix='axon-notes-bench-') as tmp:
                    env={'NEO_NOTES_FILE':tmp+'/notes.log'}
                    with smoke.server(binaries['notes'],env,workers,affinity=list(range(workers))) as (port,_):
                        for workload,operations in [('durable create',25),('list 25 notes',100)]:
                            durations=[]
                            def operation(i):
                                start=time.perf_counter()
                                status,body=smoke.request(port,'POST','/api/notes',{'title':f'note {i} café'}) if workload=='durable create' else smoke.request(port,'GET','/api/notes')
                                elapsed=time.perf_counter()-start
                                assert status==(201 if workload=='durable create' else 200)
                                if workload!='durable create':assert len(json.loads(body))==25
                                return elapsed
                            start=time.perf_counter()
                            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:durations=list(pool.map(operation,range(operations)))
                            elapsed=time.perf_counter()-start;ordered=sorted(durations)
                            data['applications'].append({'application':'notes','workers':workers,'repeat':repeat,'workload':workload,'operations':operations,
                                'elapsed_s':elapsed,'ops_s':operations/elapsed,'p50_s':statistics.median(durations),'p99_s':ordered[min(len(ordered)-1,int(len(ordered)*.99))]})
                    assert len(Path(tmp+'/notes.log').read_bytes().splitlines())==25
                save()
        received=set();lock=threading.Lock()
        class Receiver(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.1'
            def log_message(self,*args):pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                with lock:received.add(self.headers['Idempotency-Key'])
                self.send_response(200);self.send_header('Content-Length','0');self.send_header('Connection','close');self.end_headers()
        receiver=ThreadingHTTPServer(('127.0.0.1',0),Receiver);thread=threading.Thread(target=receiver.serve_forever,daemon=True);thread.start()
        try:
            for repeat in range(3):
                with tempfile.TemporaryDirectory(prefix='axon-webhook-bench-') as tmp:
                    received.clear();env={'NEO_WEBHOOK_FILE':tmp+'/jobs.log','NEO_WEBHOOK_PORT':str(receiver.server_port)}
                    with smoke.server(binaries['webhook'],env,1,affinity=[0]) as (port,_):
                        started=time.perf_counter()
                        for i in range(20):assert smoke.request(port,'POST','/events',{'id':str(i),'payload':{'value':i}})[0]==202
                        accepted=time.perf_counter()-started;deadline=time.monotonic()+30
                        while time.monotonic()<deadline:
                            status,body=smoke.request(port,'GET','/jobs');jobs=json.loads(body)
                            if len(jobs)==20 and all(j['status']=='done' for j in jobs):break
                            time.sleep(.01)
                        else:raise AssertionError('webhook benchmark delivery timed out')
                        elapsed=time.perf_counter()-started;assert len(received)==20
                        data['applications'].append({'application':'webhook','workers':1,'repeat':repeat,'workload':'durable enqueue to acknowledged delivery',
                            'operations':20,'accept_s':accepted,'elapsed_s':elapsed,'ops_s':20/elapsed})
                save()
        finally:receiver.shutdown();receiver.server_close();thread.join()
        data['source_sha256']={str(file.relative_to(ROOT)):hashlib.sha256(file.read_bytes()).hexdigest() for folder in ('neoc','runtime','stdlib','examples/json-cli','examples/notes','examples/webhook','bench/usability') for file in (ROOT/folder).glob('*') if file.is_file()}
        data['valid']=True;data['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
        write_report(data,args.report)
        print('All workload outputs and durability checks PASS',flush=True)
    except BaseException as error:
        data['failure']=repr(error);save();raise
    finally:workdir.cleanup()

def write_report(data,path):
    lines=['# Axon usability workloads — Linux ARM64, 2026-10-24','',f"Measured {data['started']} on {data['platform']}. Native {data['architecture']}, 8-vCPU/6-GiB Colima VM on Apple M1 Pro. Python/LLVM remain build tools; all measured Axon binaries have zero undefined imports.",'',
        'The file CLI validates integer id/score and string name, filters score >= 100, stably sorts by score, writes UTF-8 JSON and fsyncs the output. All variants receive identical files and are verified against Python outside timing. The parsing workload constructs a different JSON document on each iteration, parses it, accesses fields and checksums values. Rust uses serde_json; Bun uses JSON.parse. Axon uses its initial source-slice JSON representation with defensive validation and owned value copies. This measures complete implementations, not isolated language arithmetic.','',
        f"Process workloads use {data['repeats']} measured runs after one warmup; variant order is shuffled each round. They run on CPU 0 with NEO_THREADS=1. Wall times include process startup, taskset and GNU time overhead, I/O and shutdown. CPU is child user+system time; maximum RSS is GNU time's peak for the command, not PSS or container working set. Short startup-heavy cases are sensitive to scheduler noise.",'',
        '| Workload | Items | Implementation | Median wall ms | Run range ms | Median CPU ms | Max peak RSS MiB |','|---|---:|---|---:|---:|---:|---:|']
    for row in data['process']:
        runs=row['runs'];times=[r['wall_s']*1000 for r in runs]
        lines.append(f"| {row['workload']} | {row['size']} | {row['server']} | {statistics.median(times):.2f} | {min(times):.2f}–{max(times):.2f} | {statistics.median(r['cpu_s'] for r in runs)*1000:.2f} | {max(r['peak_rss_bytes'] for r in runs)/2**20:.2f} |")
    lines+=['','## Compiler workflow','','Cold means --no-cache, including parsing, proofs, LLVM generation, compilation, linking and import audit. Warm means verified cached executable reuse, including dependency/compiler/options hashing and atomic publication. Three cold and five warm runs per application. This is a development compiler measurement, not runtime overhead.','',
        '| Project | Mode | Median ms | Min–max ms | Max compiler RSS MiB |','|---|---|---:|---:|---:|']
    for row in data['build']:
        values=[r['wall_s']*1000 for r in row['runs']]
        lines.append(f"| {row['name']} | {row['kind']} | {statistics.median(values):.2f} | {min(values):.2f}–{max(values):.2f} | {max(r['peak_rss_bytes'] for r in row['runs'])/2**20:.2f} |")
    lines+=['','## Stateful applications','','Three fresh-journal runs per case. Notes uses eight concurrent Python clients, new HTTP connections per operation, 25 durable creates followed by 100 reads of the 25-note state. Writes include flock, journal append and fsync before acknowledgment. Servers run with the stated worker count; these application figures are end-to-end elapsed throughput and latency, not isolated server CPU or peak capacity. Test files use the container writable layer on the Linux VM disk; results are not production storage guarantees.','',
        '| Application/workload | Workers | Median operations/s | Run range operations/s | Median p50 ms | Median p99 ms |','|---|---:|---:|---:|---:|---:|']
    groups={}
    for row in data['applications']:groups.setdefault((row['application'],row['workload'],row['workers']),[]).append(row)
    for (app,workload,workers),rows in groups.items():
        rates=[r['ops_s'] for r in rows]
        p50=f"{statistics.median(r['p50_s'] for r in rows)*1000:.2f}" if 'p50_s' in rows[0] else 'not measured'
        p99=f"{statistics.median(r['p99_s'] for r in rows)*1000:.2f}" if 'p99_s' in rows[0] else 'not measured'
        lines.append(f'| {app}: {workload} | {workers} | {statistics.median(rates):.1f} | {min(rates):.1f}–{max(rates):.1f} | {p50} | {p99} |')
    lines+=['','Webhook measures 20 persisted events through a local Python receiver to recorded successful delivery; it includes journal replay, claims, HTTP, fsyncs and completion records. There is one consumer plus the HTTP server. Receiver/client speed and the small batch affect the result.','',
        'Collections currently use concrete typed vectors and a linear string association map. This is an initial usable library, not a claim of generic containers or an optimized hash table. The dynamic JSON and collections workloads are deliberately broader than the earlier small SSR benchmark.','',
        'Checked signed arithmetic is now the safe-code default; explicit wrapping operations cover intentional wraparound. This is a documented semantic change. Correctness, fault recovery and dependency audits accompany performance; no universal language ranking follows.','',
        f"Raw timings, stdout/stderr, time logs, inputs/outputs, build reports, tool versions, commands and hashes: `{data['directory']}`.",'']
    path.write_text('\n'.join(lines))

if __name__=='__main__':main()
