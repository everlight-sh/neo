#!/usr/bin/env python3
"""Compare standalone Axon SSR with production Bun + React, with identical HTML."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import shutil
import sys
from zoneinfo import ZoneInfo

import compare as http

ROOT = http.ROOT
REACT = ROOT/'examples/ssr-react'
spec = importlib.util.spec_from_file_location('ssr_smoke', ROOT/'tests/ssr_smoke.py')
sys.path.insert(0, str(ROOT/'tests'))
smoke = importlib.util.module_from_spec(spec); spec.loader.exec_module(smoke)


def write_report(data, path):
    m = data['metadata']; metric = m['footprint_metric']
    mib = lambda value: f'{value/2**20:.2f}'
    lines = ['# SSR: pure Axon versus Bun + React', '',
        f"Measured {m['started']}; {m['cpu']}; {m['cores']} logical CPUs; {m['os']} {m['kernel']}.", '',
        'Both serve the same catalog page: generated product rows, formatted prices and total, and escaped HTML text. Every measured route renders from its request parameter; responses are not cached. Axon constructs HTML with pure functions and its own HTTP runtime. Bun runs React components through react-dom/server renderToString with NODE_ENV=production. Neither sends client JavaScript or hydrates.', '',
        f"Bun {m['bun']}; React/react-dom {m['react']}; {m['clang']}. Three page sizes: 3, 50 and 1,000 rows. {m['repeats']} runs of {m['duration']} after {m['warmup']} warm-up, wrk with {m['threads']} threads and 64 connections. Server order is shuffled with seed {m['seed']}.", '',
        'Before each comparison, output for nine page sizes is checked byte-for-byte against an independent Python renderer, along with content type/length, escaped text, route validation and keep-alive. Runtime tests additionally cover concurrent requests and pipelining. The client shares the machine with the server; these are short saturation measurements, not production capacity or energy measurements.', '',
        'Axon (1 worker) and Bun + React are the comparison with one rendering worker each. Axon (default) uses one process per configured CPU and shows additional parallel capacity; Bun here has one process/event loop. Worker counts are not CPU affinity. React builds a general component tree; Axon directly assembles HTML for this page, so this measures that implementation tradeoff rather than universal language speed.', '',
        f'CPU/request includes every worker process and all its threads, user + kernel time. Memory is sampled every 100 ms across all workers; the footprint column is {metric}. Aggregate RSS can count shared pages more than once. Linux uses smaps_rollup for RSS/PSS and procfs CPU; Mac uses calibrated libproc counters. Latencies are closed-loop wrk values and can hide coordinated omission.', '',
        '## Deployment size', '', '| Server | Executable and app/dependencies MiB |', '|---|---:|']
    for name, server in data['servers'].items(): lines.append(f"| {name} | {mib(server['disk_bytes'])} |")
    lines += ['', 'Axon size is its executable. Bun size includes the Bun executable, example source and installed react/react-dom/scheduler packages; build tools and OS libraries are excluded.', '']
    for n in (3, 50, 1000):
        lines += [f'## /page/{n}', '', f"HTML body: {data['body_bytes'][str(n)]:,} bytes.", '',
            f'| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Processes | Aggregate RSS MiB | {metric} MiB | Valid |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
        for name in data['servers']:
            for r in data['results']:
                if r['scenario'] != f'page-{n}' or r['server'] != name: continue
                lines.append(f"| {name} | {r['median_rps']:,.0f} | {r['min_rps']:,.0f}–{r['max_rps']:,.0f} | {r['cpu_us_per_request']:.2f} | {r['median_p50_us']:.0f} | {r['median_p99_us']:.0f} | {r['max_process_count']} | {mib(r['peak_rss_bytes'])} | {mib(r['peak_footprint_bytes'])} | {r['valid']} |")
    lines += ['', '## Runtime dependencies', '',
        'The Axon application and runtime are Axon source with direct ARM64 kernel syscalls. Linux is static with no libc, CRT, ELF interpreter or shared libraries. Mac imports no libc functions but retains the required libSystem/dyld loader dependency. Python/LLVM are build tools. The Bun example requires Bun and its React packages. The Axon HTTP subset is narrower than Bun’s HTTP implementation.', '',
        f"Raw commands, hashes, measurements, CPU/memory samples and logs: `{data['directory']}`.", '']
    if data.get('observations'): lines += ['## Reading this run', ''] + ['- '+s for s in data['observations']] + ['']
    path.write_text('\n'.join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--axon', type=Path); p.add_argument('--report', type=Path)
    p.add_argument('--duration', default='5s'); p.add_argument('--warmup', default='2s')
    p.add_argument('--repeats', type=int, default=3); p.add_argument('--threads', type=int, default=4)
    args = p.parse_args(); assert args.repeats > 0
    timestamp = datetime.datetime.now(ZoneInfo('Europe/Madrid'))
    directory = ROOT/'bench/http/results'/timestamp.strftime('%Y-%m-%d-%H%M%S-ssr')
    (directory/'bin').mkdir(parents=True)
    if not (REACT/'node_modules/react/package.json').exists():
        print(http.command(['bun', 'install', '--frozen-lockfile'], cwd=REACT), flush=True)
    binary = directory/'bin/axon'
    if args.axon: shutil.copy2(args.axon.resolve(), binary)
    else: print(http.command(['python3', '-m', 'axonc', 'build', 'examples/ssr.ax', '--report', '-o', binary], cwd=ROOT), flush=True)
    smoke.audit(binary)
    bun = Path(shutil.which('bun')).resolve()
    package_files = [f for name in ('react', 'react-dom', 'scheduler') for f in (REACT/'node_modules'/name).rglob('*') if f.is_file()]
    app_files = [REACT/name for name in ('server.tsx', 'page.tsx', 'package.json', 'bun.lock')]
    specs = {'Axon (1 worker)': {'binary': str(binary), 'disk_bytes': binary.stat().st_size, 'kind': 'axon', 'single': True},
             'Axon (default)': {'binary': str(binary), 'disk_bytes': binary.stat().st_size, 'kind': 'axon', 'single': False},
             'Bun + React': {'binary': str(bun), 'disk_bytes': bun.stat().st_size+sum(f.stat().st_size for f in package_files+app_files), 'kind': 'react', 'single': True}}
    mac = platform.system() == 'Darwin'; sampler = http.Sampler()
    for name, server in specs.items():
        executable = Path(server['binary'])
        server['sha256'] = hashlib.sha256(executable.read_bytes()).hexdigest()
        server['linked_libraries'] = http.command(['otool', '-L', executable]) if mac else http.command(['readelf', '-d', executable])
        if server['kind'] == 'axon': server['undefined_symbols'] = http.command(['nm', '-u', executable])
    data = {'metadata': {'started': timestamp.isoformat(), 'os': platform.system(), 'kernel': platform.release(),
        'cpu': http.command(['sysctl', '-n', 'machdep.cpu.brand_string']) if mac else platform.machine()+' Linux VM',
        'cores': os.cpu_count(), 'footprint_metric': 'macOS physical footprint' if mac else 'Linux PSS',
        'bun': http.command(['bun', '--version']), 'react': json.loads((REACT/'node_modules/react/package.json').read_text())['version'],
        'clang': http.command(['clang', '--version']).splitlines()[0], 'repeats': args.repeats, 'duration': args.duration,
        'warmup': args.warmup, 'threads': args.threads, 'seed': 20261023, 'cpu_sampler_calibration': sampler.calibrate()},
        'directory': str(directory), 'servers': specs, 'body_bytes': {str(n): len(smoke.reference(n)) for n in (3, 50, 1000)}, 'results': []}
    sources = list((ROOT/'axonc').glob('*.py'))+list((ROOT/'runtime').glob('*.ax'))+app_files+[ROOT/'examples/ssr.ax',ROOT/'tests/ssr_smoke.py',Path(__file__).resolve(),ROOT/'bench/http/compare.py']
    data['source_sha256'] = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sources}
    report = args.report or ROOT/f"RESULTS-ssr-{'macos' if mac else 'linux'}-{timestamp:%Y-%m-%d}.md"
    rng = random.Random(data['metadata']['seed'])
    print('Artifacts:', directory, flush=True)
    for n in (3, 50, 1000):
        order = list(specs); rng.shuffle(order)
        for name in order:
            server = specs[name]
            override = (lambda port: [str(bun), 'run', str(REACT/'server.tsx'), str(port)]) if server['kind'] == 'react' else None
            r = http.measure((name, Path(server['binary'])), (f'page-{n}', f'/page/{n}', 64, 0, server['single']), args,
                             sampler, {}, directory, command_override=override, env_override={'NODE_ENV': 'production'}, validator=smoke.validate)
            data['results'].append(r)
            (directory/'measurements.json').write_text(json.dumps(data, indent=2)); write_report(data, report)
            print(f"/page/{n:<4} {name:16} {r['median_rps']:>10,.0f} req/s {r['cpu_us_per_request']:>8.2f} CPU µs/req valid={r['valid']}", flush=True)
    data['metadata']['finished'] = datetime.datetime.now(ZoneInfo('Europe/Madrid')).isoformat()
    (directory/'measurements.json').write_text(json.dumps(data, indent=2)); write_report(data, report)
    print('Report:', report, flush=True)


if __name__ == '__main__': main()
