#!/usr/bin/env python3
"""Measure rendering + UTF-8 checksum, without sockets or the HTTP runtime."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import shutil
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT/'examples/jsx-ssr'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, default=ROOT/'.kernel-build/jsx-ssr/render-bench')
    p.add_argument('--iterations', type=int, default=500000)
    p.add_argument('--repeats', type=int, default=5)
    args = p.parse_args()
    assert args.iterations > 0 and args.repeats > 0
    binary = args.binary.resolve()
    env = dict(os.environ, AXON_THREADS='1', NODE_ENV='production')
    bun = shutil.which('bun')
    fixture_text = subprocess.check_output([bun, 'run', 'fixtures.ts'], cwd=EXAMPLE, env=env, text=True)
    fixtures = json.loads(fixture_text)
    checksums = [sum(fixtures[str(i)].encode()) for i in range(1, 1001)]
    expected = sum(checksums)*(args.iterations//1000) + sum(checksums[:args.iterations % 1000])
    commands = {'Axon baseline': [str(binary), str(args.iterations), '0'],
        'Axon optimized': [str(binary), str(args.iterations), '1'],
        'Bun + React': [bun, 'run', str(EXAMPLE/'render-bench.ts'), str(args.iterations)]}
    directory = ROOT/'bench/http/results'/datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S-jsx-render')
    directory.mkdir(parents=True)
    results = {name: [] for name in commands}
    rng = random.Random(20261023)
    # Warm executable/signature/filesystem caches, outside the recorded runs.
    for name, command in commands.items():
        warm = list(command)
        warm[1 if name.startswith('Axon') else -1] = '1000'
        output = subprocess.check_output(warm, env=env, text=True)
        assert output.strip() == str(sum(checksums)), (name, output)
    for repeat in range(args.repeats):
        order = list(commands); rng.shuffle(order)
        for name in order:
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            start = time.perf_counter()
            r = subprocess.run(commands[name], capture_output=True, text=True, env=env, check=True)
            elapsed = time.perf_counter()-start
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            assert r.stdout.strip() == str(expected), (name, r.stdout, expected)
            cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
            results[name].append({'wall_s': elapsed, 'cpu_s': cpu, 'cpu_us_per_render': cpu*1e6/args.iterations,
                'renders_per_s': args.iterations/elapsed, 'checksum': expected})
            print(f"{repeat+1} {name}: {args.iterations/elapsed:,.0f} renders/s, {cpu*1e6/args.iterations:.3f} CPU µs/render", flush=True)
    summary = {name: {'median_renders_per_s': statistics.median(r['renders_per_s'] for r in runs),
        'min_renders_per_s': min(r['renders_per_s'] for r in runs), 'max_renders_per_s': max(r['renders_per_s'] for r in runs),
        'median_cpu_us_per_render': statistics.median(r['cpu_us_per_render'] for r in runs)} for name, runs in results.items()}
    data = {'iterations': args.iterations, 'repeats': args.repeats, 'warmup_iterations': 1000, 'commands': commands, 'results': results, 'summary': summary,
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(), 'directory': str(directory),
        'note': 'Every iteration varies count 1..1000, renders the full document and checksums every UTF-8 byte. Wall/CPU include process startup and checksum work. One native binary contains both variants; mode chooses the renderer. Bun uses production React and includes UTF-8 encoding. This is not isolated render-call timing.'}
    (directory/'measurements.json').write_text(json.dumps(data, indent=2)+'\n')
    for path in (Path(__file__), EXAMPLE/'render-bench.ts', ROOT/'.kernel-build/jsx-ssr/render-bench.ax'):
        shutil.copy2(path, directory/path.name)
    print(json.dumps(summary, indent=2), flush=True)
    print('Artifacts:', directory, flush=True)


if __name__ == '__main__': main()
