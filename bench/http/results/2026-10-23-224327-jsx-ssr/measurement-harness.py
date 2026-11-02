#!/usr/bin/env python3
"""Benchmark the same TSX page compiled to Axon and rendered by Bun/React."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo

import compare as http

ROOT = http.ROOT
EXAMPLE = ROOT/'examples/jsx-ssr'
sys.path.insert(0, str(ROOT/'tests'))
import ssr_smoke as smoke

SCENARIOS = [
    ('base-c1', '/page/3', 1, 0, True),
    ('base-c64', '/page/3', 64, 0, True),
    ('badge-c64', '/page/2', 64, 0, True),
    ('escape-c64', '/page/13', 64, 0, True),
]


def write_report(data, path):
    m = data['metadata']; metric = m['footprint_metric']
    mib = lambda value: f'{value/2**20:.2f}'
    lines = ['# Shared TSX: native Axon versus Bun + React', '',
        f"Measured {m['started']}; {m['cpu']}; {m['cores']} logical CPUs; {m['os']} {m['kernel']}.", '',
        'Both servers use the same examples/jsx-ssr/page.tsx source. The example translator compiles its supported TSX subset into ordinary Axon rendering functions. The reference executes the components with React renderToStaticMarkup on Bun. Props are supplied and HTML is rendered on every request; there is no response cache or client JavaScript. This measures specialized native rendering against the general React renderer, not arbitrary React compatibility or universal language speed.', '',
        'Both have one rendering worker and one server process; Bun background threads are included in CPU and memory measurements. This is a worker budget, not CPU affinity. The HTTP stacks and route parsers differ. No multicore Axon capacity is mixed into the headline comparison.', '',
        f"Bun {m['bun']}; React/react-dom {m['react']}. Each server/case has {m['repeats']} measured runs of {m['duration']} after {m['warmup']} warm-up. wrk uses one client thread at one connection, otherwise {m['threads']} threads at 64 connections, without pipelining. Server order is shuffled with seed {m['seed']}.", '',
        'The normal page is /page/3; /page/2 adds a conditional badge; /page/13 changes the prop to script-like text, quotes and Unicode. The count is displayed and controls branches; it does not repeat components or increase row count. These are small page variants, not a scaling benchmark.', '',
        'Before timing, the full smoke suite compares all 1,000 valid inputs byte-for-byte with React, checks one/four Axon workers, routing, escaping, Unicode, 100 concurrent requests and 129 pipelined responses. Every timed server is also checked against all 1,000 reference outputs before warm-up. Raw React reference bodies and preflight output are preserved.', '',
        f'CPU/request includes all server threads and user + kernel time. Memory is sampled every 100 ms; footprint means {metric}. Peak memory covers all measured repeats and is not per-request allocation. The client shares the host with the server. wrk latencies are closed-loop and can hide coordinated omission. Short runs on a shared machine are indicative, not production capacity estimates.', '',
        '## Results', '']
    for scenario in SCENARIOS:
        label, route, connections, _, _ = scenario
        lines += [f'### {label}: {route}, {connections} connection(s)', '',
            f"Identical HTML body: {data['body_bytes'][route]:,} bytes.", '',
            f'| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Peak RSS MiB | Peak {metric} MiB | Errors / non-2xx | Valid |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
        results = {r['server']: r for r in data['results'] if r['scenario'] == label}
        for name in data['servers']:
            if name not in results: continue
            r = results[name]
            lines.append(f"| {name} | {r['median_rps']:,.0f} | {r['min_rps']:,.0f}–{r['max_rps']:,.0f} | {r['cpu_us_per_request']:.2f} | {r['median_p50_us']:.0f} | {r['median_p99_us']:.0f} | {mib(r['peak_rss_bytes'])} | {mib(r['peak_footprint_bytes'])} | {r['errors']} / {r['non2xx']} | {r['valid']} |")
        if 'Axon JSX' in results and 'Bun + React' in results:
            a, b = results['Axon JSX'], results['Bun + React']
            lines += ['', f"Axon/Bun throughput ratio: **{a['median_rps']/b['median_rps']:.2f}×**. Axon uses **{100*(1-a['cpu_us_per_request']/b['cpu_us_per_request']):.1f}% less server CPU per request** in this case."]
        if 'Axon baseline' in results and 'Axon JSX' in results:
            a, b = results['Axon JSX'], results['Axon baseline']
            lines += ['', f"Optimized/baseline throughput ratio: **{a['median_rps']/b['median_rps']:.3f}×**; server CPU/request change: **{100*(a['cpu_us_per_request']/b['cpu_us_per_request']-1):+.1f}%**. Compare run ranges before interpreting small changes."]
        lines.append('')
    lines += ['## Deployment size and runtime dependencies', '', '| Server | Executable + app/runtime packages MiB |', '|---|---:|']
    for name, server in data['servers'].items(): lines.append(f"| {name} | {mib(server['disk_bytes'])} |")
    lines += ['', 'Axon size is its executable. Bun size includes its executable, the reference app sources and installed react/react-dom/scheduler packages; TypeScript, the translator and other build tools are excluded. OS libraries are excluded from both.', '',
        'The generated Linux executable is static, with no undefined imports, ELF interpreter or shared libraries. macOS imports no libc functions but retains the required libSystem/dyld loader dependency. Python/LLVM and Bun/TypeScript are build tools for the native example. The Axon renderer supports only the documented example TSX subset.', '',
        f"Commands, binary/source hashes, per-run measurements, CPU/memory samples, reference bodies and logs: `{data['directory']}`.", '']
    path.write_text('\n'.join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--axon', type=Path)
    p.add_argument('--baseline', type=Path, help='Optional original Axon binary for a fresh side-by-side comparison')
    p.add_argument('--report', type=Path)
    p.add_argument('--duration', default='5s')
    p.add_argument('--warmup', default='2s')
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--threads', type=int, default=4)
    args = p.parse_args()
    assert args.repeats > 0 and 1 <= args.threads <= 64
    started = datetime.datetime.now(ZoneInfo('Europe/Madrid'))
    directory = ROOT/'bench/http/results'/started.strftime('%Y-%m-%d-%H%M%S-jsx-ssr')
    (directory/'bin').mkdir(parents=True)
    print('Artifacts:', directory, flush=True)
    if not (EXAMPLE/'node_modules/react/package.json').exists():
        print(http.command(['bun', 'install', '--frozen-lockfile'], cwd=EXAMPLE), flush=True)
    binary = directory/'bin/axon'
    if args.axon: shutil.copy2(args.axon.resolve(), binary)
    else: print(http.command(['bun', 'run', 'build', str(binary)], cwd=EXAMPLE), flush=True)
    smoke.audit(binary)
    bun = Path(shutil.which('bun')).resolve()
    env = dict(os.environ, NODE_ENV='production')
    fixtures_text = http.command([bun, 'run', 'fixtures.ts'], cwd=EXAMPLE, env=env)
    (directory/'react-reference.json').write_text(fixtures_text+'\n')
    fixtures = {int(k): v.encode() for k, v in json.loads(fixtures_text).items()}
    assert len(fixtures) == 1000
    smoke.reference = lambda n: fixtures[n]
    smoke.COUNTS = tuple(range(1, 1001))
    preflight = ['python3', str(ROOT/'tests/jsx_ssr_smoke.py'), '--binary', str(binary)]
    if platform.system() == 'Linux' and os.geteuid() == 0: preflight += ['--empty-root']
    result = subprocess.run(preflight, cwd=ROOT, env=env, capture_output=True, text=True)
    (directory/'preflight.log').write_text(result.stdout+result.stderr)
    assert result.returncode == 0, result.stdout+result.stderr
    print('Preflight: exact React parity, HTTP behavior, imports PASS', flush=True)
    package_files = [f for name in ('react', 'react-dom', 'scheduler') for f in (EXAMPLE/'node_modules'/name).rglob('*') if f.is_file()]
    app_files = [EXAMPLE/name for name in ('reference.tsx', 'page.tsx', 'package.json', 'bun.lock')]
    servers = {
        'Axon JSX': {'binary': str(binary), 'disk_bytes': binary.stat().st_size},
        'Bun + React': {'binary': str(bun), 'disk_bytes': bun.stat().st_size + sum(f.stat().st_size for f in package_files+app_files)},
    }
    if args.baseline:
        baseline = directory/'bin/axon-baseline'
        shutil.copy2(args.baseline.resolve(), baseline)
        smoke.audit(baseline)
        servers['Axon baseline'] = {'binary': str(baseline), 'disk_bytes': baseline.stat().st_size}
    mac = platform.system() == 'Darwin'
    sampler = http.Sampler()
    for name, server in servers.items():
        executable = Path(server['binary'])
        server['sha256'] = hashlib.sha256(executable.read_bytes()).hexdigest()
        server['linked_libraries'] = http.command(['otool', '-L', executable]) if mac else http.command(['readelf', '-d', executable])
        if name.startswith('Axon'): server['undefined_symbols'] = http.command(['nm', '-u', executable])
    data = {'metadata': {
        'started': started.isoformat(), 'os': platform.system(), 'kernel': platform.release(),
        'cpu': http.command(['sysctl', '-n', 'machdep.cpu.brand_string']) if mac else platform.machine()+' Linux VM',
        'cores': os.cpu_count(), 'footprint_metric': 'macOS physical footprint' if mac else 'Linux PSS',
        'bun': http.command([bun, '--version']), 'react': json.loads((EXAMPLE/'node_modules/react/package.json').read_text())['version'],
        'repeats': args.repeats, 'duration': args.duration, 'warmup': args.warmup, 'threads': args.threads,
        'seed': 20261023, 'cpu_sampler_calibration': sampler.calibrate(), 'preflight_command': preflight,
    }, 'directory': str(directory), 'servers': servers,
        'body_bytes': {s[1]: len(fixtures[int(s[1].split('/')[-1])]) for s in SCENARIOS}, 'results': []}
    sources = list((ROOT/'axonc').glob('*.py')) + list((ROOT/'runtime').glob('*.ax')) + [
        f for f in EXAMPLE.iterdir() if f.is_file()] + [ROOT/'tests/jsx_ssr_smoke.py', ROOT/'tests/ssr_smoke.py', ROOT/'tests/kernel_runtime_smoke.py',
        Path(__file__).resolve(), ROOT/'bench/http/compare.py', ROOT/'.kernel-build/jsx-ssr/server.ax']
    if args.baseline: sources.append(ROOT/'.kernel-build/jsx-ssr/baseline-server.ax')
    data['source_sha256'] = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sources}
    shutil.copy2(__file__, directory/'measurement-harness.py')
    report = args.report or ROOT/f"RESULTS-jsx-ssr-{'macos' if mac else 'linux'}-{started:%Y-%m-%d}.md"
    rng = random.Random(data['metadata']['seed'])
    for scenario in SCENARIOS:
        order = list(servers); rng.shuffle(order)
        scenario_args = argparse.Namespace(**vars(args))
        if scenario[2] == 1: scenario_args.threads = 1
        for name in order:
            server = servers[name]
            override = (lambda port: [str(bun), 'run', str(EXAMPLE/'reference.tsx'), str(port)]) if name == 'Bun + React' else None
            r = http.measure((name, Path(server['binary'])), scenario, scenario_args, sampler, {}, directory,
                command_override=override, env_override={'NODE_ENV': 'production'}, validator=smoke.validate)
            # Both renderers must stay in one process throughout a comparison.
            r['valid'] = r['valid'] and r['max_process_count'] == 1 and all(s['process_count'] == 1 for s in r['samples'])
            data['results'].append(r)
            (directory/'measurements.json').write_text(json.dumps(data, indent=2)); write_report(data, report)
            print(f"{scenario[0]:12} {name:12} {r['median_rps']:>10,.0f} req/s {r['cpu_us_per_request']:>7.2f} CPU µs/req valid={r['valid']}", flush=True)
    data['metadata']['finished'] = datetime.datetime.now(ZoneInfo('Europe/Madrid')).isoformat()
    (directory/'measurements.json').write_text(json.dumps(data, indent=2)); write_report(data, report)
    print('Report:', report, flush=True)
    if not all(r['valid'] for r in data['results']): raise SystemExit('Invalid comparison: see preserved logs')


if __name__ == '__main__': main()
