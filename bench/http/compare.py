#!/usr/bin/env python3
"""Neo/Rust/Go/Bun HTTP comparison, including CPU and memory.

macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses procfs.
All worker processes are counted. No third-party Python dependencies.
Historical RESULTS-http*.md files are deliberately preserved.

--neo-before adds a second Neo binary ("Neo (before)") to the same run.
--rounds R repeats the whole scenario x server sweep R times (each server
restarted, in a fresh shuffled order per scenario and round), so runs of
different servers interleave in time. Each run records how many cores the
rest of the machine kept busy meanwhile (host CPU ticks minus the server, wrk
and this script); --max-background waits for a quieter machine before a run.
--max-load waits for the one-minute load average to drop to a limit. Each run
records the load average and the busiest processes just before it starts:
macOS system processes by name, anything else as "user process".
"""
import argparse
import ctypes
import datetime
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import resource
import signal
import shutil
import socket
import statistics
import subprocess
import threading
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCENARIOS = [
    ('hello-64', '/', 64, 0, False),
    ('hello-256', '/', 256, 0, False),
    ('pipeline-16', '/', 64, 16, False),
    ('hello-one-worker', '/', 64, 0, True),
    ('smooth-1000-one-worker', '/smooth/1000', 64, 0, True),
    ('smooth-10000-one-worker', '/smooth/10000', 64, 0, True),
    ('smooth-10000-default', '/smooth/10000', 64, 0, False),
    ('nbody-default', 'POST:/nbody', 64, 0, False),
]


class Usage(ctypes.Structure):
    _fields_ = [('uuid', ctypes.c_ubyte * 16)] + [(name, ctypes.c_uint64) for name in (
        'user', 'system', 'idle_wakes', 'interrupt_wakes', 'pageins', 'wired',
        'rss', 'footprint', 'start', 'exit', 'child_user', 'child_system',
        'child_idle', 'child_interrupt', 'child_pageins', 'child_elapsed', 'disk_read', 'disk_write')]


class Timebase(ctypes.Structure):
    _fields_ = [('numer', ctypes.c_uint32), ('denom', ctypes.c_uint32)]


class MacSampler:
    def __init__(self):
        self.lib = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
        self.lib.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        self.lib.proc_pid_rusage.restype = ctypes.c_int
        system = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
        self.timebase = Timebase()
        assert system.mach_timebase_info(ctypes.byref(self.timebase)) == 0
        self.tick_seconds = self.timebase.numer / self.timebase.denom / 1e9

    def snapshot(self, pid):
        u = Usage()
        if self.lib.proc_pid_rusage(pid, 2, ctypes.byref(u)) != 0:
            raise OSError(ctypes.get_errno(), 'proc_pid_rusage')
        return {'time': time.monotonic(), 'cpu_s': (u.user + u.system) * self.tick_seconds,
                'user_s': u.user * self.tick_seconds, 'system_s': u.system * self.tick_seconds,
                'rss_bytes': u.rss, 'footprint_bytes': u.footprint}

    def children(self, pid):
        values = (ctypes.c_int * 1024)()
        n = self.lib.proc_listchildpids(pid, values, ctypes.sizeof(values))
        # proc_listchildpids returns a PID count, unlike proc_listpids' byte count.
        return [p for p in values[:max(0, n)] if p > 0]

    def calibrate(self):
        start = self.snapshot(os.getpid()); cpu = time.process_time(); end = time.monotonic() + .15
        while time.monotonic() < end: pass
        measured = self.snapshot(os.getpid())['cpu_s'] - start['cpu_s']
        expected = time.process_time() - cpu
        assert math.isclose(measured, expected, rel_tol=.15), (measured, expected)
        return {'rusage_cpu_s': measured, 'process_time_s': expected,
                'mach_numer': self.timebase.numer, 'mach_denom': self.timebase.denom}


class LinuxSampler:
    def __init__(self):
        self.hz = os.sysconf('SC_CLK_TCK')
        self.page = os.sysconf('SC_PAGE_SIZE')

    def snapshot(self, pid):
        base = Path('/proc') / str(pid)
        fields = (base/'stat').read_text().rsplit(')', 1)[1].split()
        rollup = (base/'smaps_rollup').read_text()
        # stat's RSS counter is batched and can lag badly for tiny processes.
        # Read both memory measures from the page-table walk in smaps_rollup.
        rss = int(re.search(r'^Rss:\s+(\d+)', rollup, re.M)[1])*1024
        pss = int(re.search(r'^Pss:\s+(\d+)', rollup, re.M)[1])*1024
        user, system = int(fields[11])/self.hz, int(fields[12])/self.hz
        return {'time': time.monotonic(), 'cpu_s': user+system, 'user_s': user,
                'system_s': system, 'rss_bytes': rss, 'footprint_bytes': pss}

    def children(self, pid):
        try: return list(map(int, (Path('/proc')/str(pid)/'task'/str(pid)/'children').read_text().split()))
        except FileNotFoundError: return []

    def calibrate(self):
        start = self.snapshot(os.getpid()); cpu = time.process_time(); end = time.monotonic()+.25
        while time.monotonic() < end: pass
        measured = self.snapshot(os.getpid())['cpu_s']-start['cpu_s']
        expected = time.process_time()-cpu
        assert math.isclose(measured, expected, rel_tol=.20), (measured, expected)
        return {'proc_stat_cpu_s': measured, 'process_time_s': expected, 'clock_ticks_per_s': self.hz}


class Sampler:
    """Sum every live descendant, including all Axon worker processes.

    Server workers are required to stay alive during a measurement; preserving
    each PID's final observed CPU counter prevents negative deltas on an exit.
    """
    def __init__(self):
        self.backend = MacSampler() if platform.system() == 'Darwin' else LinuxSampler()
        self.last = {}
        self.root = None

    def calibrate(self): return self.backend.calibrate()

    def snapshot(self, pid):
        if pid != self.root: self.last = {}; self.root = pid
        pending, live = [pid], {}
        while pending:
            current = pending.pop()
            if current in live: continue
            try:
                live[current] = self.backend.snapshot(current)
                pending.extend(self.backend.children(current))
            except (OSError, ProcessLookupError): pass
        if pid not in live: raise ProcessLookupError(pid)
        self.last.update(live)
        result = {'time': time.monotonic(), 'live_pids': sorted(live), 'process_count': len(live)}
        for field in ('cpu_s', 'user_s', 'system_s'):
            result[field] = sum(v[field] for v in self.last.values())
        for field in ('rss_bytes', 'footprint_bytes'):
            result[field] = sum(v[field] for v in live.values())
        return result


class HostCPU:
    """Busy CPU ticks of the whole machine (macOS host_statistics, Linux /proc/stat)."""
    def __init__(self):
        self.mac = platform.system() == 'Darwin'
        if self.mac:
            self.lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
            self.lib.mach_host_self.restype = ctypes.c_uint32
            self.hz = 100  # CPU load ticks are in units of 1/CLK_TCK; Darwin's is 100
        else: self.hz = os.sysconf('SC_CLK_TCK')

    def busy_seconds(self):
        if self.mac:
            info = (ctypes.c_uint32 * 4)(); count = ctypes.c_uint32(4)
            assert self.lib.host_statistics(self.lib.mach_host_self(), 3, info, ctypes.byref(count)) == 0
            return (info[0] + info[1] + info[3]) / self.hz  # user + system + nice, summed over CPUs
        fields = list(map(int, Path('/proc/stat').read_text().split('\n', 1)[0].split()[1:]))
        return (sum(fields) - fields[3] - fields[4]) / self.hz  # all but idle and iowait

    def busy_cores(self, seconds):
        start, t = self.busy_seconds(), time.monotonic()
        time.sleep(seconds)
        return (self.busy_seconds() - start) / (time.monotonic() - t)


def wait_quiet(host, limit, timeout):
    """Background busy cores just before a run, waiting up to timeout seconds for <= limit."""
    deadline = time.monotonic() + timeout
    while True:
        busy = host.busy_cores(1.0)
        if limit is None or busy <= limit or time.monotonic() > deadline: return busy
        time.sleep(4)


def wait_load(limit, timeout):
    """One-minute load average just before a run, waiting up to timeout seconds for <= limit."""
    deadline = time.monotonic() + timeout
    while limit is not None and os.getloadavg()[0] > limit and time.monotonic() < deadline: time.sleep(5)
    return os.getloadavg()


SYSTEM_PREFIXES = ('/System/', '/usr/libexec/', '/usr/sbin/', '/sbin/', '/bin/', '/Library/Apple/')


def process_name(path):
    """The executable name of a macOS system process, else "user process"."""
    return path.rsplit('/', 1)[-1] if path.startswith(SYSTEM_PREFIXES) else 'user process'


def busiest(count=5):
    """The busiest processes as (CPU %, name). Only macOS system processes keep
    their executable name; everything else is "user process", and no path is
    recorded."""
    out = subprocess.run(['ps', '-Ao', 'pcpu=,comm='], capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        cpu, _, path = line.strip().partition(' ')
        path = path.strip()
        if path: rows.append((float(cpu), process_name(path)))
    return sorted(rows, reverse=True)[:count]

def command(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True, **kwargs).stdout.strip()


def checksum(n):
    a = [(i * 2654435761) % 1000003 for i in range(n)]
    for _ in range(32):
        a = [a[i] if i == 0 or i + 1 == n else (a[i-1] + 2*a[i] + a[i+1]) % 1000003 for i in range(n)]
    return sum(a)


def nbody_reference(n=256, steps=4):
    bodies = [[(i*2654435761)%1009/1009, (i*40503)%1013/1013, (i*69069)%1019/1019, 0., 0., 0., 1/n] for i in range(n)]
    for _ in range(steps):
        out = []
        for b in bodies:
            acc = [0., 0., 0.]
            for other in bodies:
                d = [other[k]-b[k] for k in range(3)]
                d2 = sum(x*x for x in d)+.01
                inv = other[6]/(d2*math.sqrt(d2))
                for k in range(3): acc[k] += d[k]*inv
            velocity = [b[k+3]+acc[k]*.001 for k in range(3)]
            out.append([b[k]+velocity[k]*.001 for k in range(3)] + velocity + [b[6]])
        bodies = out
    energy = 0.
    for i, b in enumerate(bodies):
        energy += .5*b[6]*sum(x*x for x in b[3:6])
        for j, other in enumerate(bodies):
            if i != j:
                energy -= .5*b[6]*other[6]/math.sqrt(sum((other[k]-b[k])**2 for k in range(3))+.01)
    return energy


def validate(port, refs):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
    try:
        c.request('GET', '/'); r = c.getresponse()
        assert (r.status, r.read()) == (200, b'Hello, World!')
        c.request('GET', '/missing'); r = c.getresponse(); r.read(); assert r.status == 404
        for n in (1000, 10000):
            c.request('GET', f'/smooth/{n}'); r = c.getresponse(); body = json.loads(r.read())
            assert r.status == 200 and body == {'n': n, 'passes': 32, 'checksum': refs[str(n)]}, body
        c.request('POST', '/nbody', body='{"n":256,"steps":4}', headers={'Content-Type': 'application/json'})
        r = c.getresponse(); body = json.loads(r.read())
        assert r.status == 200 and body['n'] == 256 and body['steps'] == 4 and math.isclose(body['energy'], refs['nbody'], abs_tol=1e-9), body
    finally: c.close()


def latency_us(value):
    m = re.fullmatch(r'([\d.]+)(us|ms|s)', value)
    return float(m[1]) * {'us': 1, 'ms': 1000, 's': 1e6}[m[2]]


def median_optional(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def load(port, scenario, duration, threads, log):
    name, path, connections, depth, _ = scenario
    args = ['wrk', f'-t{threads}', f'-c{connections}', f'-d{duration}', '--latency', '--timeout', '5s']
    if depth: args += ['-s', str(HERE / 'pipeline.lua')]
    if path.startswith('POST:'):
        args += ['-s', str(HERE / 'post_nbody.lua')]; path = path[5:]
    args += [f'http://127.0.0.1:{port}{path}']
    if depth: args += ['--', str(depth)]
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    wrk_cpu = after.ru_utime + after.ru_stime - children.ru_utime - children.ru_stime
    log.write_text(result.stdout + result.stderr)
    assert result.returncode == 0, (args, result.stderr)
    out = result.stdout
    errors = re.search(r'Socket errors: connect (\d+), read (\d+), write (\d+), timeout (\d+)', out)
    bad = re.search(r'Non-2xx or 3xx responses:\s+(\d+)', out)
    p50 = latency_us(re.search(r'\s50%\s+(\S+)', out)[1])
    p99 = latency_us(re.search(r'\s99%\s+(\S+)', out)[1])
    return {'rps': float(re.search(r'Requests/sec:\s+([\d.]+)', out)[1]),
            'requests': int(re.search(r'(\d+) requests in', out)[1]),
            'p50_us': None if depth else p50, 'p99_us': None if depth else p99,
            'wrk_reported_p50_us': p50, 'wrk_reported_p99_us': p99,
            'non2xx': int(bad[1]) if bad else 0,
            'errors': sum(map(int, errors.groups())) if errors else 0,
            'wrk_cpu_s': wrk_cpu, 'command': args, 'log': str(log)}


def summarize(name, scenario, runs, warmups, samples, startups, idles):
    """One table row from every run of a server on a scenario (across rounds)."""
    valid = all(r['errors'] == 0 and r['non2xx'] == 0 for r in warmups+runs)
    other = [r['other_cores'] for r in runs if 'other_cores' in r]
    return {'server': name, 'scenario': scenario, 'valid': valid, 'runs': runs, 'warmup': warmups[0], 'warmups': warmups,
            'startup_ms': statistics.median(startups), 'startups_ms': startups, 'idle': idles[0], 'idles': idles, 'samples': samples,
            'median_rps': statistics.median(r['rps'] for r in runs),
            'min_rps': min(r['rps'] for r in runs), 'max_rps': max(r['rps'] for r in runs),
            'median_p50_us': median_optional(r['p50_us'] for r in runs),
            'median_p99_us': median_optional(r['p99_us'] for r in runs),
            'max_p99_us': max((r['p99_us'] for r in runs if r['p99_us'] is not None), default=None),
            'cpu_us_per_request': sum(r['cpu_s'] for r in runs)*1e6/sum(r['requests'] for r in runs),
            'average_cpu_cores': sum(r['cpu_s'] for r in runs)/sum(r['wall_s'] for r in runs),
            'median_other_cores': statistics.median(other) if other else None,
            'peak_rss_bytes': max(s['rss_bytes'] for s in samples),
            'peak_footprint_bytes': max(s['footprint_bytes'] for s in samples),
            'max_process_count': max(s['process_count'] for s in samples),
            'errors': sum(r['errors'] for r in runs), 'non2xx': sum(r['non2xx'] for r in runs)}


def merge(parts):
    return summarize(parts[0]['server'], parts[0]['scenario'], [r for p in parts for r in p['runs']],
                     [w for p in parts for w in p['warmups']], [x for p in parts for x in p['samples']],
                     [p['startup_ms'] for p in parts], [p['idle'] for p in parts])


def measure(server, scenario, args, sampler, refs, directory, *, command_override=None, env_override=None, validator=None, host=None, tag=''):
    name, binary = server
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]
    env = dict(os.environ)
    for key in ('NEO_THREADS', 'NEO_SERVE', 'NEO_HTTP_POLL', 'AXON_THREADS', 'TOKIO_WORKER_THREADS', 'GOMAXPROCS', 'BUN_REUSE_PORT', 'HYPER_PIPELINE_FLUSH'):
        env.pop(key, None)
    env['HYPER_PIPELINE_FLUSH'] = '1'
    if scenario[4]:
        env.update(TOKIO_WORKER_THREADS='1', GOMAXPROCS='1', NEO_THREADS='1')
    if env_override: env.update(env_override)
    cmd = [str(binary), str(port)] if name != 'Bun' else [str(binary), 'run', str(ROOT / 'bench/bun/server.ts'), str(port)]
    if command_override: cmd = command_override(port)
    prefix = scenario[0] + '-' + re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') + tag
    samples = []
    with (directory / (prefix+'-server.log')).open('w') as log:
        started = time.monotonic()
        p = subprocess.Popen(cmd, env=env, stdout=log, stderr=log, start_new_session=True)
        try:
            while True:
                assert p.poll() is None, f'{name} exited during startup'
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.1): pass
                    break
                except OSError:
                    if time.monotonic()-started > 10: raise TimeoutError(name)
                    time.sleep(.005)
            startup_ms = (time.monotonic()-started)*1000
            time.sleep(.2)
            idle = sampler.snapshot(p.pid)
            (validator or validate)(port, refs)
            warmup = load(port, scenario, args.warmup, args.threads, directory / (prefix+'-warmup.txt'))
            stop = threading.Event()
            def sample():
                while not stop.is_set():
                    try: samples.append(sampler.snapshot(p.pid))
                    except OSError: return
                    stop.wait(.1)
            monitor = threading.Thread(target=sample)
            monitor.start()
            runs = []
            try:
                for repeat in range(args.repeats):
                    before = sampler.snapshot(p.pid)
                    harness = time.process_time()
                    host_before = host.busy_seconds() if host else None
                    run = load(port, scenario, args.duration, args.threads, directory / f'{prefix}-{repeat+1}.txt')
                    after = sampler.snapshot(p.pid)
                    if host:
                        run['host_busy_s'] = host.busy_seconds() - host_before
                        run['harness_cpu_s'] = time.process_time() - harness
                    run['cpu_s'] = after['cpu_s']-before['cpu_s']
                    run['user_s'] = after['user_s']-before['user_s']
                    run['system_s'] = after['system_s']-before['system_s']
                    run['wall_s'] = after['time']-before['time']
                    run['process_count'] = after['process_count']
                    run['live_pids'] = after['live_pids']
                    run['cpu_us_per_request'] = run['cpu_s']*1e6/run['requests']
                    if host:
                        other = run['host_busy_s'] - run['cpu_s'] - run['wrk_cpu_s'] - run['harness_cpu_s']
                        run['other_cores'] = other / run['wall_s']
                    runs.append(run)
            finally: stop.set(); monitor.join()
            return summarize(name, scenario[0], runs, [warmup], samples, [startup_ms], [idle])
        finally:
            os.killpg(p.pid, signal.SIGTERM)
            try: p.wait(timeout=3)
            except subprocess.TimeoutExpired: os.killpg(p.pid, signal.SIGKILL); p.wait()


def write_report(data, path):
    m = data['metadata']; mib = lambda n: f'{n/2**20:.2f}'
    latency = lambda n: 'n/a' if n is None else f'{n:.0f}'
    metric = m.get('footprint_metric', 'macOS physical footprint')
    operating_system = m.get('os', 'Darwin')+' '+m.get('kernel', m.get('macos',''))
    rounds = m.get('rounds', 1)
    lines = ['# HTTP benchmarks: Neo, Rust, Go and Bun', '',
        f"Measured {m['started']}. {m['cpu']}; {m['cores']} logical CPUs; {mib(m['memory_bytes']/1024)} GiB RAM; {operating_system}.", '',
        f"wrk {m['wrk_version']}, {m['wrk_threads']} client threads. {rounds} round(s); in each, every scenario runs every server once in a freshly shuffled order (seed {m['seed']}), with {m['repeats']} measured run(s) of {m['duration']} after a {m['warmup']} warm-up per start. Client and server share this machine.", '',
        'Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Neo runs one process per worker. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set NEO_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.', '',
        f'CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. "Other cores" is the machine\'s busy CPU during each run minus the server, wrk and this script: load from the rest of the machine (median over runs). Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is {metric}. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission; p99 is the median of the runs\' p99, with the worst run\'s p99 beside it.', '',
        'Pipelined latency percentiles are omitted: the macOS wrk build emits invalid/nonmonotonic values for them. Pipeline throughput and CPU use the request and CPU counters.', '',
        'Versions: ' + '; '.join(f'{k}: {v}' for k, v in m['versions'].items()) + '.', '',
        '## Executable and idle footprint', '',
        f'| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle {metric} MiB | Startup ms |',
        '|---|---:|---:|---:|---:|']
    for name, spec in data['servers'].items():
        rows = [r for r in data['results'] if r['server'] == name]
        if not rows: continue
        lines.append(f"| {name} | {mib(spec['disk_bytes'])} | {mib(statistics.median(r['idle']['rss_bytes'] for r in rows))} | {mib(statistics.median(r['idle']['footprint_bytes'] for r in rows))} | {statistics.median(r['startup_ms'] for r in rows):.1f} |")
    for scenario in data['scenarios']:
        rows = [r for r in data['results'] if r['scenario'] == scenario[0]]
        if not rows: continue
        lines += ['', '## '+scenario[0], '', f'Route `{scenario[1]}`; {scenario[2]} connections; pipeline depth {scenario[3] or 1}.', '',
            f'| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | {metric} MiB | Errors / non-2xx |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for name in data['servers']:
            for r in rows:
                if r['server'] != name: continue
                label = name if r['valid'] else name+' (INVALID)'
                worst = '' if r.get('max_p99_us') is None else f" ({r['max_p99_us']:.0f})"
                other = 'n/a' if r.get('median_other_cores') is None else f"{r['median_other_cores']:.2f}"
                lines.append(f"| {label} | {r['median_rps']:,.0f} | {r['min_rps']:,.0f}–{r['max_rps']:,.0f} | {latency(r['median_p50_us'])} | {latency(r['median_p99_us'])}{worst} | {r['cpu_us_per_request']:.2f} | {r['average_cpu_cores']:.2f} | {other} | {r.get('max_process_count',1)} | {mib(r['peak_rss_bytes'])} | {mib(r['peak_footprint_bytes'])} | {r['errors']} / {r['non2xx']} |")
    parts = data.get('parts', [])
    if any('load_before' in q for q in parts):
        names = list(data['servers'])
        lines += ['', '## Each run with the load before it', '',
            'req/s of each run, with the one-minute load average just before it started (the whole machine, including the previous run).', '',
            '| Scenario | Round | ' + ' | '.join(names) + ' |', '|---|---:|' + '---:|' * len(names)]
        for scenario in data['scenarios']:
            for rnd in sorted({q['round'] for q in parts if q['scenario'] == scenario[0]}):
                cells = []
                for name in names:
                    q = next((q for q in parts if q['scenario'] == scenario[0] and q['round'] == rnd and q['server'] == name), None)
                    cells.append('' if q is None else f"{q['median_rps']:,.0f} @ {q['load_before'][0]:.2f}")
                lines.append(f"| {scenario[0]} | {rnd} | " + ' | '.join(cells) + ' |')
    lines += ['', '## Dependency boundary and limits', '',
        'Neo allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Neo source, with compiler primitives for direct kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.', '',
        f"Raw measurements, memory samples, commands, binary hashes and per-run logs: `{data['directory']}`.", '']
    if data.get('observations'):
        lines += ['## Reading this run', ''] + ['- '+s for s in data['observations']] + ['']
    path.write_text('\n'.join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--duration', default='5s'); p.add_argument('--warmup', default='2s')
    p.add_argument('--repeats', type=int, default=3); p.add_argument('--threads', type=int, default=4)
    p.add_argument('--rounds', type=int, default=1)
    p.add_argument('--neo', '--axon', type=Path, dest='neo'); p.add_argument('--neo-before', type=Path)
    p.add_argument('--rust', type=Path); p.add_argument('--go', type=Path)
    p.add_argument('--servers', nargs='*', help='subset of server names to run')
    p.add_argument('--max-background', type=float, help='wait (up to --quiet-timeout s) until the rest of the machine uses at most this many cores')
    p.add_argument('--max-load', type=float, help='wait (up to --quiet-timeout s) until the one-minute load average is at most this')
    p.add_argument('--quiet-timeout', type=float, default=120)
    p.add_argument('--scenarios', nargs='*'); p.add_argument('--report', type=Path)
    args = p.parse_args()
    assert platform.system() in ('Darwin', 'Linux')
    assert args.repeats > 0 and args.rounds > 0
    timestamp = datetime.datetime.now(ZoneInfo('Europe/Madrid'))
    directory = HERE / 'results' / timestamp.strftime('%Y-%m-%d-%H%M%S-native')
    (directory / 'bin').mkdir(parents=True)
    builds = [('neo', args.neo), ('rust', args.rust), ('go', args.go)] + ([('neo-before', args.neo_before)] if args.neo_before else [])
    for name, supplied in builds:
        target = directory / 'bin' / name
        if supplied: shutil.copy2(supplied.resolve(), target)
        elif name == 'neo': print(command(['python3', '-m', 'neoc', 'build', 'examples/http.neo', '--no-cache', '-o', target], cwd=ROOT), flush=True)
        elif name == 'rust':
            build_env = dict(os.environ)
            if platform.system() == 'Linux': build_env['CARGO_TARGET_DIR'] = '/tmp/axon-linux-cargo-target'
            print(command(['cargo', 'build', '--release', '--locked', '--bin', 'http_hyper'], cwd=ROOT/'bench/rust', env=build_env), flush=True)
            cargo_target = Path(build_env.get('CARGO_TARGET_DIR', str(ROOT/'bench/rust/target')))
            shutil.copy2(cargo_target/'release/http_hyper', target)
        else: command(['go', 'build', '-o', target, './http'], cwd=ROOT/'bench/go', env=dict(os.environ, GOWORK='off', GOTOOLCHAIN='local'))
    servers = [('Neo', directory/'bin'/'neo')] + ([('Neo (before)', directory/'bin'/'neo-before')] if args.neo_before else [])
    servers += [('Rust', directory/'bin'/'rust'), ('Go', directory/'bin'/'go'), ('Bun', Path(shutil.which('bun')).resolve())]
    if args.servers: servers = [s for s in servers if s[0] in args.servers]
    sampler = Sampler()
    host = HostCPU()
    mac = platform.system() == 'Darwin'
    cpu = command(['sysctl', '-n', 'machdep.cpu.brand_string']) if mac else platform.machine()+' Linux VM'
    memory = int(command(['sysctl', '-n', 'hw.memsize'])) if mac else int(re.search(r'MemTotal:\s+(\d+)', Path('/proc/meminfo').read_text())[1])*1024
    neo_label = 'kqueue worker processes' if mac else 'io_uring/epoll worker processes'
    versions = {'Neo': f'{neo_label}, examples/http.neo'}
    if args.neo_before: versions['Neo (before)'] = f'supplied binary {args.neo_before.name}'
    versions.update({'Clang': command(['clang','--version']).splitlines()[0],
                     'Rust': command(['rustc','--version']), 'Go': command(['go','version'],env=dict(os.environ,GOTOOLCHAIN='local')),
                     'Bun': command(['bun','--version'])})
    metadata = {'started': timestamp.isoformat(), 'cpu': cpu, 'os': platform.system(),
        'footprint_metric': 'macOS physical footprint' if mac else 'Linux PSS',
        'cores': os.cpu_count(), 'memory_bytes': memory, 'macos': platform.mac_ver()[0], 'kernel': platform.release(),
        'wrk_version': subprocess.run(['wrk','--version'],capture_output=True,text=True).stdout.splitlines()[0],
        'wrk_threads': args.threads, 'repeats': args.repeats, 'rounds': args.rounds, 'duration': args.duration, 'warmup': args.warmup,
        'max_background': args.max_background, 'max_load': args.max_load, 'seed': 20261023, 'cpu_sampler_calibration': sampler.calibrate(), 'load_start': os.getloadavg(),
        'versions': versions}
    scenarios = [s for s in SCENARIOS if not args.scenarios or s[0] in args.scenarios]
    assert scenarios
    specs = {}
    for name, binary in servers:
        size = binary.stat().st_size + ((ROOT/'bench/bun/server.ts').stat().st_size if name == 'Bun' else 0)
        specs[name] = {'binary': str(binary), 'disk_bytes': size, 'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                       'linked_libraries': command(['otool', '-L', binary]) if mac else command(['readelf', '-d', binary]),
                       'undefined_symbols': command(['nm', '-u', binary]) if name.startswith('Neo') else None}
    data = {'metadata': metadata, 'directory': str(directory.relative_to(ROOT)), 'servers': specs, 'scenarios': scenarios,
            'references': {'1000': checksum(1000), '10000': checksum(10000), 'nbody': nbody_reference()}, 'results': [], 'parts': []}
    sources = list((ROOT/'neoc').glob('*.py')) + list((ROOT/'runtime').glob('*.neo')) + [ROOT/'examples/http.neo',
        ROOT/'bench/rust/Cargo.toml', ROOT/'bench/rust/Cargo.lock', ROOT/'bench/rust/src/http_hyper.rs',
        ROOT/'bench/rust/src/smooth.rs', ROOT/'bench/rust/src/nbody_seq.rs', ROOT/'bench/go/go.mod',
        ROOT/'bench/go/http/main.go', ROOT/'bench/bun/server.ts', Path(__file__).resolve()]
    data['source_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    report = args.report or directory / 'report.md'
    print('Artifacts:', directory, flush=True)
    rng = random.Random(metadata['seed'])
    for round_index in range(args.rounds):
        for scenario in scenarios:
            order = list(servers); rng.shuffle(order)
            print(f'\n--- round {round_index+1}: {scenario[0]} ---', flush=True)
            for server in order:
                load = wait_load(args.max_load, args.quiet_timeout)
                top = busiest()
                background = wait_quiet(host, args.max_background, args.quiet_timeout)
                part = measure(server, scenario, args, sampler, data['references'], directory,
                               command_override=(lambda port: [str(server[1]), 'run', str(ROOT/'bench/bun/server.ts'), str(port)]) if server[0] == 'Bun' else None,
                               host=host, tag=f'-r{round_index+1}')
                part['round'] = round_index + 1; part['background_before_cores'] = background
                part['load_before'] = load; part['busiest_before'] = top
                data['parts'].append(part)
                same = [q for q in data['parts'] if q['server'] == server[0] and q['scenario'] == scenario[0]]
                data['results'] = [r for r in data['results'] if not (r['server'] == server[0] and r['scenario'] == scenario[0])] + [merge(same)]
                (directory/'measurements.json').write_text(portable(data))
                write_report(data, report)
                r = part['runs'][-1]
                print(f"{part['server']:12s} {part['median_rps']:>10,.0f} req/s  CPU {part['cpu_us_per_request']:>7.2f} µs/req  p99 {latency_text(part['median_p99_us'])}  other {r.get('other_cores', 0):.2f} cores (before {background:.2f})  load {load[0]:.2f}  busiest {top[0][1]} {top[0][0]:.0f}%  valid={part['valid']}", flush=True)
            time.sleep(.5)
    metadata['finished'] = datetime.datetime.now(ZoneInfo('Europe/Madrid')).isoformat()
    metadata['load_end'] = os.getloadavg()
    (directory/'measurements.json').write_text(portable(data))
    write_report(data, report)
    print('\nReport:', report, flush=True)


def portable(data):
    """JSON with paths inside the checkout made relative and the home directory shortened, so results can be committed."""
    text = json.dumps(data, indent=2).replace(json.dumps(str(ROOT) + '/')[1:-1], '')
    return text.replace(json.dumps(str(Path.home()))[1:-1], '~')


def latency_text(value): return 'n/a' if value is None else f'{value:,.0f} µs'


if __name__ == '__main__': main()
