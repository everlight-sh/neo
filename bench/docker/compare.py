#!/usr/bin/env python3
"""Run inside the Linux load container, with the Docker socket mounted."""
import argparse
import concurrent.futures
import datetime
import hashlib
import http.client
import json
import os
import platform
from pathlib import Path
import random
import re
import resource
import shutil
import socket
import statistics
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'bench/http'))
import compare as http_bench


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/var/run/docker.sock')


class Engine:
    def call(self, method, path, data=None, raw=False):
        connection = UnixConnection('localhost', timeout=30)
        body = json.dumps(data).encode() if data is not None else None
        connection.request(method, path, body=body, headers={'Content-Type': 'application/json'})
        response = connection.getresponse(); result = response.read(); connection.close()
        if response.status >= 300: raise RuntimeError((method, path, response.status, result[:2000]))
        if raw: return result
        return json.loads(result) if result else None

    def stats(self, cid):
        raw = self.call('GET', f'/containers/{cid}/stats?stream=false&one-shot=true')
        memory = raw['memory_stats']; values = memory.get('stats', {})
        return {'time': time.monotonic(), 'cpu_ns': raw['cpu_stats']['cpu_usage']['total_usage'],
            'memory_bytes': memory.get('usage', 0),
            'working_set_bytes': max(0, memory.get('usage', 0)-values.get('inactive_file', values.get('total_inactive_file', 0))),
            'tasks': raw.get('pids_stats', {}).get('current'),
            'throttling': raw['cpu_stats'].get('throttling_data', {}), 'raw': raw}

    def remove(self, cid, log):
        raw = self.call('GET', f'/containers/{cid}/logs?stdout=true&stderr=true', raw=True)
        parts = []; offset = 0
        while offset+8 <= len(raw) and raw[offset] in (0, 1, 2):
            length = int.from_bytes(raw[offset+4:offset+8], 'big')
            parts.append(raw[offset+8:offset+8+length]); offset += 8+length
        log.write_bytes(b''.join(parts) if parts else raw)
        self.call('DELETE', f'/containers/{cid}?force=true')


def request(host, path='/page/3', method='GET'):
    c = http.client.HTTPConnection(host, 8080, timeout=10)
    try:
        c.request(method, path); response = c.getresponse()
        return response.status, response.read(), dict(response.getheaders())
    finally: c.close()


def validate(host, fixtures):
    c = http.client.HTTPConnection(host, 8080, timeout=10)
    try:
        for n in range(1, 1001):
            c.request('GET', f'/page/{n}'); r = c.getresponse(); body = r.read()
            assert r.status == 200 and body == fixtures[n], (host, n, r.status, body[:100])
            assert r.getheader('Content-Type').lower() == 'text/html; charset=utf-8', (host, n, 'content type', r.getheaders())
            assert int(r.getheader('Content-Length')) == len(body), (host, n, 'content length', len(body), r.getheaders())
        for path, expected in (('/', fixtures[3]), ('/?view=home', fixtures[3]), ('/page/13?q=escape', fixtures[13])):
            c.request('GET', path); r = c.getresponse(); assert (r.status, r.read()) == (200, expected)
        for path in ('/page/0', '/page/1001', '/page/-1', '/page/x', '/page/1x', '/page/1/', '/page/1234567890123'):
            c.request('GET', path); r = c.getresponse()
            assert (r.status, r.read()) == (400, b'usage: /page/N, 1 <= N <= 1000'), (host, path)
        c.request('GET', '/missing'); r = c.getresponse(); assert (r.status, r.read()) == (404, b'Not Found')
        c.request('POST', '/', body='test'); r = c.getresponse(); assert (r.status, r.read()) == (405, b'')
    finally: c.close()
    def parallel_request(i):
        n = 2 if i % 2 else 13
        status, body, _ = request(host, f'/page/{n}')
        assert status == 200 and body == fixtures[n], (host, 'parallel', n, status, body[:100])
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool: list(pool.map(parallel_request, range(100)))
    with socket.create_connection((host, 8080), timeout=10) as sock:
        counts = [3, 2]*64 + [13]
        sock.sendall(b''.join(f'GET /page/{n} HTTP/1.1\r\nHost: benchmark\r\n'.encode() +
            (b'Connection: close\r\n' if i+1 == len(counts) else b'') + b'\r\n' for i, n in enumerate(counts)))
        stream = sock.makefile('rb')
        for n in counts:
            assert stream.readline().startswith(b'HTTP/1.1 200'), host
            headers = {}
            while (line := stream.readline()) != b'\r\n':
                assert line
                k, v = line.split(b':', 1); headers[k.lower()] = v.strip()
            body = stream.read(int(headers[b'content-length']))
            assert body == fixtures[n], (host, 'pipeline', n, body[:100])
        tail = stream.read(1)
        assert tail == b'', (host, 'pipeline expected EOF', tail)
        stream.close()


def load(host, duration, log):
    command = ['wrk', '-t4', '-c64', f'-d{duration}', '--latency', '--timeout', '5s', f'http://{host}:8080/page/3']
    usage = resource.getrusage(resource.RUSAGE_CHILDREN); started = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    elapsed = time.monotonic()-started; after = resource.getrusage(resource.RUSAGE_CHILDREN)
    log.write_text(result.stdout+result.stderr)
    assert result.returncode == 0, result.stderr
    out = result.stdout
    errors = re.search(r'Socket errors: connect (\d+), read (\d+), write (\d+), timeout (\d+)', out)
    bad = re.search(r'Non-2xx or 3xx responses:\s+(\d+)', out)
    return {'rps': float(re.search(r'Requests/sec:\s+([\d.]+)', out)[1]),
        'requests': int(re.search(r'(\d+) requests in', out)[1]), 'errors': sum(map(int, errors.groups())) if errors else 0,
        'non2xx': int(bad[1]) if bad else 0,
        'p50_us': http_bench.latency_us(re.search(r'\s50%\s+(\S+)', out)[1]),
        'p99_us': http_bench.latency_us(re.search(r'\s99%\s+(\S+)', out)[1]),
        'client_cpu_cores': (after.ru_utime+after.ru_stime-usage.ru_utime-usage.ru_stime)/elapsed,
        'command': command, 'log': str(log)}


def write_report(data, path):
    lines = ['# Docker SSR: Axon, Rust, Bun direct and Bun React', '',
        f"Measured {data['started']} on ARM64 Linux in an 8-vCPU, 6-GiB Colima VM on Apple M1 Pro. Docker Engine {data['engine']['Version']}. Runtime images are linux/arm64; no CPU emulation.", '',
        'Every server renders the same 518-byte /page/3 HTML body on every request, without caching. Axon compiles the shared TSX subset to native functions. Rust uses direct String rendering with Hyper/Tokio. Two Rust builds use identical source: static musl and dynamic glibc. Bun direct uses string rendering; Bun React executes the same TSX through renderToStaticMarkup. Both Bun variants share their route/server implementation. This compares complete stacks, not language speed alone.', '',
        'Axon and static Rust use scratch images containing only the executable; Rust statically includes musl, while Axon has no libc imports. The glibc Rust image also starts from scratch but copies the executable and its required loader/shared libraries. Bun uses the pinned official 1.3.13-alpine base; React/react-dom are 19.2.8. Image IDs, base digest, binary/source hashes, tool versions and build logs are retained.', '',
        f"Servers run as UID/GID 65532, read-only root filesystem, all capabilities dropped, no-new-privileges, {data['memory_mib']} MiB RAM with swap disabled. The one-worker test uses CPU 0 and a one-CPU quota; four-worker tests use CPUs 0–3 and a four-CPU quota. The load container and sampler use CPUs 4–7. Traffic crosses the same Docker bridge entirely inside Linux; there are no host port mappings or macOS forwarding paths.", '',
        'Axon uses worker processes (1 or 4 total). Rust uses one process with 1 or 4 Tokio worker threads plus the main thread. Bun uses one serving process, or a supervisor plus four serving processes sharing a port with SO_REUSEPORT. Container CPU and memory include all workers, supervisors and threads.', '',
        f"Each server/budget is checked against all 1,000 valid prop values from React, plus routing, escaping/Unicode, 100 concurrent requests and 129 pipelined responses. Performance is wrk -t4 -c64, no pipelining, {data['repeats']} runs of {data['duration']} after {data['warmup']} warm-up. Server order is shuffled. Latencies are closed-loop and can hide coordinated omission.", '',
        'Memory is sampled during measured loads, after warm-up: container cgroup usage minus inactive file cache (Docker-style working set), not RSS/PSS; it includes charged kernel memory. Startup and warm-up spikes are not included in the table peaks. Raw usage and samples are retained. CPU/request uses cgroup CPU nanoseconds, including user/kernel time for the complete container. Sampled peaks may miss shorter spikes. Quota throttling and client CPU usage are recorded.', '',
        '## Image size', '', '| Image | Uncompressed file payload MiB | gzip docker-save archive MiB |', '|---|---:|---:|']
    for name, image in data['build']['images'].items():
        lines.append(f"| {name} | {image['rootfs_file_bytes']/2**20:.4f} | {image['gzip_docker_save_bytes']/2**20:.4f} |")
    lines += ['', 'The gzip column is a locally compressed docker-save archive, including image metadata; it is not measured registry transfer size. Uncompressed payload sums regular files in an exported fresh root filesystem, excluding Docker-injected host/resolver files and .dockerenv. It excludes tar padding and metadata, and is not allocated disk usage. Shared Bun layers are counted for each standalone image. Docker/containerd also reports image content size separately in the raw manifest. Build tools are excluded.', '']
    for workers in (1, 4):
        lines += [f'## {workers} CPU(s), {workers} rendering worker(s)', '',
            '| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Measured-load peak working set MiB | Start→first response ms | Client CPU cores | Errors / non-2xx | Valid |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
        for name in data['build']['images']:
            for r in data['results']:
                if r['server'] != name or r['workers'] != workers: continue
                if r.get('failure'):
                    lines.append(f"| {name} | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | failed | False |")
                    continue
                lines.append(f"| {name} | {r['median_rps']:,.0f} | {r['min_rps']:,.0f}–{r['max_rps']:,.0f} | {r['cpu_us_per_request']:.2f} | {r['p50_us']:.0f} | {r['p99_us']:.0f} | {r['peak_working_set_bytes']/2**20:.2f} | {r['median_start_ms']:.1f} | {r['client_cpu_cores']:.2f} | {r['errors']} / {r['non2xx']} | {r['valid']} |")
        lines.append('')
    lines += [f"Startup is the median of {data['startup_repeats']} fresh-container starts with images already cached, measured from the Docker start API call until the first response with verified HTML; container creation, pulls and builds are excluded. Polling, Docker control-plane latency and bridge setup are included. For multicore it measures the first ready worker, not the entire pool.", '',
        'Results are local VM measurements on a shared physical machine. Inspect run ranges and load-client CPU consumption before interpreting small gaps or multicore limits. No energy or universal language-performance claims follow from this one small SSR page.', '',
        f"Raw artifacts: `{data.get('host_directory', data['directory'])}`.", '']
    if data.get('observations'): lines += ['## Observations', ''] + ['- '+s for s in data['observations']] + ['']
    if 'Axon poll baseline' in data['build']['images']:
        lines += ['## HTTP backend comparison', '',
            'Current Axon uses persistent level-triggered epoll registrations through direct Linux syscalls. The poll baseline is the preserved executable/image from before this change, rerun in this same session with identical resource and load settings. Framing, rendering and the 64-response batching policy are unchanged. Raw image manifests retain both source/binary hashes.', '',
            'The syscall-count profiles are intrusive strace runs, separate from these untraced measurements. Both backends already use approximately one read and one send per unpipelined request. Registration persistence avoids rebuilding and attaching a wait set for all open sockets on each wait; counts alone do not measure that cost or establish how much of the gain comes from kernel versus user-space dispatch.', '']
    path.write_text('\n'.join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--duration', default='10s'); p.add_argument('--warmup', default='3s')
    p.add_argument('--repeats', type=int, default=5); p.add_argument('--startup-repeats', type=int, default=5)
    p.add_argument('--memory-mib', type=int, default=1024)
    p.add_argument('--report', type=Path, default=ROOT/'RESULTS-docker-ssr-linux-2026-10-23.md')
    p.add_argument('--include-poll-baseline', type=Path, help='Preserved pre-epoll image manifest')
    p.add_argument('--baseline-label', default='Axon poll baseline', help='Label for a preserved image comparison')
    p.add_argument('--include-current-poll', action='store_true', help='Same current Axon binary with its poll fallback')
    p.add_argument('--servers', nargs='+', help='Selected manifest labels')
    p.add_argument('--workers', nargs='+', type=int, choices=(1, 4), default=[1, 4])
    args = p.parse_args()
    engine = Engine(); network = os.environ.get('BENCH_NETWORK', 'axon-ssr-comparison')
    build = json.loads((ROOT/'.kernel-build/docker-ssr/images.json').read_text())
    if args.include_poll_baseline:
        baseline = json.loads(args.include_poll_baseline.read_text())
        build['images'][args.baseline_label] = baseline['images']['Axon JSX']
        build['poll_baseline_build'] = baseline
    if args.include_current_poll:
        build['images']['Axon current poll'] = dict(build['images']['Axon JSX'], benchmark_env=['NEO_HTTP_POLL=1'])
    if args.servers:
        build['images'] = {name: build['images'][name] for name in args.servers}
    directory = ROOT/'bench/http/results'/datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S-docker-ssr')
    directory.mkdir(parents=True)
    print('Artifacts:', directory, flush=True)
    fixtures_text = subprocess.check_output(['bun', 'run', 'fixtures.ts'], cwd=ROOT/'examples/jsx-ssr', env=dict(os.environ,NODE_ENV='production'), text=True)
    (directory/'react-reference.json').write_text(fixtures_text)
    fixtures = {int(k): v.encode() for k,v in json.loads(fixtures_text).items()}
    data = {'started': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'directory': str(directory), 'build': build,
        'engine': engine.call('GET', '/version'), 'repeats': args.repeats, 'duration': args.duration,
        'kernel': platform.release(), 'architecture': platform.machine(), 'client_cpu_affinity': sorted(os.sched_getaffinity(0)),
        'warmup': args.warmup, 'startup_repeats': args.startup_repeats, 'memory_mib': args.memory_mib, 'results': []}
    data['harness_sha256'] = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in (Path(__file__).resolve(), ROOT/'bench/http/compare.py')}
    shutil.copy2(__file__, directory/'measurement-harness.py')
    report = args.report
    rng = random.Random(20261023)
    for workers in args.workers:
        order = list(build['images']); rng.shuffle(order)
        for name in order:
            prefix = f'w{workers}-'+name.lower().replace(' ', '-')
            startup = []; cid = None; snapshots = []; runs = []
            def create_start():
                config = {'Image': build['images'][name]['id'], 'Env': [f'NEO_THREADS={workers}', f'BENCH_WORKERS={workers}', 'NODE_ENV=production'] + build['images'][name].get('benchmark_env', []),
                    'Labels': {'axon.benchmark': 'docker-ssr'},
                    'HostConfig': {'NetworkMode': network, 'NanoCpus': workers*10**9, 'CpusetCpus': '0' if workers == 1 else '0-3',
                        'Memory': args.memory_mib*2**20, 'MemorySwap': args.memory_mib*2**20, 'ReadonlyRootfs': True, 'CapDrop': ['ALL'],
                        'SecurityOpt': ['no-new-privileges'], 'PidsLimit': 256,
                        'Ulimits': [{'Name': 'nofile', 'Soft': 65536, 'Hard': 65536}]}}
                ident = engine.call('POST', '/containers/create', config)['Id']
                try:
                    start = time.monotonic(); engine.call('POST', f'/containers/{ident}/start')
                    info = engine.call('GET', f'/containers/{ident}/json')
                    host = info['NetworkSettings']['Networks'][network]['IPAddress']
                    while True:
                        try:
                            status, body, _ = request(host)
                            if status == 200 and body == fixtures[3]: break
                        except OSError: pass
                        if time.monotonic()-start > 15: raise TimeoutError((name, info))
                        time.sleep(.002)
                    return ident, host, {'start_to_response_ms': (time.monotonic()-start)*1000, 'inspect': info}
                except BaseException:
                    engine.remove(ident, directory/(prefix+'-failed-start.log')); raise
            try:
                for index in range(args.startup_repeats):
                    cid, host, ready = create_start(); startup.append(ready)
                    if index+1 != args.startup_repeats:
                        engine.remove(cid, directory/f'{prefix}-startup-{index}.log'); cid = None
                validate(host, fixtures)
                print(prefix, 'all 1000 inputs + HTTP checks PASS', flush=True)
                idle = engine.stats(cid)
                top = engine.call('GET', f'/containers/{cid}/top?ps_args=-eo%20pid,ppid,comm')
                warmup = load(host, args.warmup, directory/(prefix+'-warmup.txt'))
                stop = threading.Event(); sampling_errors = []
                def sample():
                    while not stop.is_set():
                        try: snapshots.append(engine.stats(cid))
                        except Exception as exc: sampling_errors.append(repr(exc)); return
                        stop.wait(.1)
                monitor = threading.Thread(target=sample); monitor.start()
                try:
                    for repeat in range(args.repeats):
                        before = engine.stats(cid); started = time.monotonic()
                        run = load(host, args.duration, directory/f'{prefix}-{repeat+1}.txt')
                        after = engine.stats(cid)
                        run.update(cpu_s=(after['cpu_ns']-before['cpu_ns'])/1e9,
                            wall_s=time.monotonic()-started, before=before, after=after)
                        runs.append(run)
                finally: stop.set(); monitor.join()
                info = engine.call('GET', f'/containers/{cid}/json')
                valid = all(r['errors'] == 0 and r['non2xx'] == 0 for r in [warmup]+runs) and info['State']['Running'] and not info['State']['OOMKilled'] and not sampling_errors
                result = {'server': name, 'workers': workers, 'valid': valid, 'runs': runs, 'warmup': warmup,
                    'startup': startup, 'idle': idle, 'top': top, 'final_inspect': info, 'snapshots': snapshots, 'sampling_errors': sampling_errors,
                    'median_rps': statistics.median(r['rps'] for r in runs), 'min_rps': min(r['rps'] for r in runs), 'max_rps': max(r['rps'] for r in runs),
                    'p50_us': statistics.median(r['p50_us'] for r in runs), 'p99_us': statistics.median(r['p99_us'] for r in runs),
                    'cpu_us_per_request': sum(r['cpu_s'] for r in runs)*1e6/sum(r['requests'] for r in runs),
                    'peak_working_set_bytes': max(s['working_set_bytes'] for s in snapshots), 'peak_memory_bytes': max(s['memory_bytes'] for s in snapshots),
                    'median_start_ms': statistics.median(s['start_to_response_ms'] for s in startup),
                    'client_cpu_cores': statistics.mean(r['client_cpu_cores'] for r in runs),
                    'errors': sum(r['errors'] for r in runs), 'non2xx': sum(r['non2xx'] for r in runs)}
                data['results'].append(result)
                (directory/'measurements.json').write_text(json.dumps(data, indent=2)); write_report(data, report)
                print(prefix, f"{result['median_rps']:,.0f} req/s, {result['cpu_us_per_request']:.2f} CPU µs/req, {result['peak_working_set_bytes']/2**20:.2f} MiB working set, valid={valid}", flush=True)
            except Exception as exc:
                info = engine.call('GET', f'/containers/{cid}/json') if cid else None
                failure = {'server': name, 'workers': workers, 'valid': False, 'failure': repr(exc),
                    'traceback': traceback.format_exc(),
                    'startup': startup, 'runs': runs, 'snapshots': snapshots, 'final_inspect': info}
                data['results'].append(failure)
                (directory/'measurements.json').write_text(json.dumps(data, indent=2)); write_report(data, report)
                print(prefix, 'FAILED:', repr(exc), 'state:', info['State'] if info else None, flush=True)
            finally:
                if cid: engine.remove(cid, directory/(prefix+'-server.log'))
    data['finished'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (directory/'measurements.json').write_text(json.dumps(data, indent=2)); write_report(data, report)
    print('Report:', report, flush=True)
    if not all(r['valid'] for r in data['results']): raise SystemExit('Invalid comparisons preserved; inspect logs')


if __name__ == '__main__': main()
