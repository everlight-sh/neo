#!/usr/bin/env python3
"""Intrusive syscall-count profiling; run in a host-PID SYS_PTRACE tool container.

Traced timings/throughput are NOT comparable with untraced benchmark results.
Application containers keep the normal nonroot/read-only/capability settings.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'bench/http'))
spec = importlib.util.spec_from_file_location('docker_bench', Path(__file__).with_name('compare.py'))
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', default='baseline')
    p.add_argument('--axon-image', default='axon-compare-axon-poll:20261023')
    args = p.parse_args()
    out = ROOT/'.kernel-build/http-epoll'/args.stage; out.mkdir(parents=True, exist_ok=True)
    engine = bench.Engine(); data = []
    for label, image in (('axon', args.axon_image), ('rust-musl', 'axon-compare-rust:20261023'), ('rust-glibc', 'axon-compare-rust-gnu:20261023')):
        config = {'Image': image, 'Env': ['NEO_THREADS=1', 'BENCH_WORKERS=1', 'NODE_ENV=production'],
            'HostConfig': {'NetworkMode': 'axon-http-profile', 'NanoCpus': 10**9, 'CpusetCpus': '0',
                'Memory': 2**30, 'MemorySwap': 2**30, 'ReadonlyRootfs': True, 'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges']}}
        cid = engine.call('POST', '/containers/create', config)['Id']; tracer = None
        try:
            engine.call('POST', f'/containers/{cid}/start')
            info = engine.call('GET', f'/containers/{cid}/json'); pid = info['State']['Pid']
            host = info['NetworkSettings']['Networks']['axon-http-profile']['IPAddress']
            for _ in range(100):
                try:
                    if bench.request(host)[0] == 200: break
                except OSError: time.sleep(.02)
            else: raise RuntimeError('Server not ready')
            bench.load(host, '2s', out/(label+'-warmup.txt'))
            trace_command = ['strace', '-f', '-c', '-e', 'trace=network,read,write,ppoll,epoll_pwait,epoll_ctl,fcntl,getppid', '-p', str(pid), '-o', str(out/(label+'-strace.txt'))]
            with (out/(label+'-tracer.log')).open('w') as log:
                tracer = subprocess.Popen(trace_command, stderr=log, stdout=log)
                time.sleep(.2); assert tracer.poll() is None, 'strace attach failed'
                run = bench.load(host, '5s', out/(label+'-traced-wrk.txt'))
                tracer.send_signal(signal.SIGINT); tracer.wait(timeout=5); tracer = None
            data.append({'server': label, 'image': image, 'container': info, 'trace_command': trace_command, 'load': run})
            print(label, 'profile saved; requests', run['requests'], flush=True)
        finally:
            if tracer and tracer.poll() is None: tracer.send_signal(signal.SIGINT); tracer.wait(timeout=5)
            engine.remove(cid, out/(label+'-server.log'))
    (out/'profile.json').write_text(json.dumps({'note': 'strace changes scheduling and timings; use syscall counts, not these rates as benchmark results', 'profiles': data}, indent=2)+'\n')


if __name__ == '__main__': main()
