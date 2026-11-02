#!/usr/bin/env python3
"""The benchmarks page's five headline rows on one x86-64 Linux box: Vif, Rust, Go, Bun and Zig
in the same interleaved rounds.

http: hello and 16-deep pipelined GET / against one-worker servers. Every server is confined to
  SERVER_CPUS (default 0; leave its SMT sibling idle) and wrk -t WRK_THREADS -c64 runs on
  CLIENT_CPUS (default 2,3: the other physical core of a 4-vCPU box). Method of
  RESULTS-zig-x86-linux-2026-11-02.md: a fresh server per run, a 2 s warm-up, a 10 s
  measured run, order alternating each round. Server CPU and memory cover the server's whole
  process tree (/proc/PID/task/*/children, every 100 ms during the measured run): CPU is user +
  system time, memory is the summed Pss of smaps_rollup (bench/http/compare.py's aggregate PSS)
  and the summed Rss. Client CPU is wrk's user + system time (getrusage). Each server is
  validated first: GET / must answer 200 "Hello, World!" with a correct Content-Length, and 16
  pipelined GETs on one socket must get 16 such responses (servers that fail that are not run
  in the pipelined scenario).
cli: complete-process wall time of the JSON workflow (1M small documents: build, parse, read,
  checksum) and n-body 4096 x 10, every process pinned to CPU 0 with one worker
  (NEO_THREADS / GOMAXPROCS / RAYON_NUM_THREADS / ZIG_THREADS = 1); 2 warm-up rounds, then
  ROUNDS rounds in a shuffled order (fixed seed). CPU time comes from wait4, peak RSS from GNU
  time (see run_cli). Every output is checked.

usage: run_headline.py http OUT.json ROUNDS | cli OUT.json ROUNDS
Binary locations: VIF (/root/bin), RUST (/root/rust), GO (/root/go-bin), ZIG
(/root/zig-baseline/bin), ZIGN (/root/zig-native/bin), AXON (/root/axon: bench sources).
"""
import json, math, os, random, re, resource, signal, socket, statistics, subprocess, sys, tempfile, threading, time
from pathlib import Path

E = os.environ.get
VIF, RUST, GO = Path(E('VIF', '/root/bin')), Path(E('RUST', '/root/rust')), Path(E('GO', '/root/go-bin'))
ZIG, ZIGN, AXON = Path(E('ZIG', '/root/zig-baseline/bin')), Path(E('ZIGN', '/root/zig-native/bin')), Path(E('AXON', '/root/axon'))
SERVER_CPUS, CLIENT_CPUS, WRK_THREADS = E('SERVER_CPUS', '0'), E('CLIENT_CPUS', '2,3'), E('WRK_THREADS', '2')
TICK = os.sysconf('SC_CLK_TCK')
ONE = {'NEO_THREADS': '1', 'GOMAXPROCS': '1', 'RAYON_NUM_THREADS': '1', 'ZIG_THREADS': '1', 'TOKIO_WORKER_THREADS': '1'}

SERVERS = {  # name -> (argv before the port, extra environment)
    'Vif': ([VIF / 'vif-http'], {'NEO_THREADS': '1'}),
    'Rust hyper': ([RUST / 'http_hyper'], {'TOKIO_WORKER_THREADS': '1', 'HYPER_PIPELINE_FLUSH': '1'}),
    'Go net/http': ([GO / 'http'], {'GOMAXPROCS': '1'}),
    'Bun': (['bun', 'run', AXON / 'bench/bun/server.ts'], {}),
    'Zig http.zig default': ([ZIG / 'http_httpz'], {}),
    'Zig http.zig 1+1': ([ZIG / 'http_httpz'], {'HTTPZ_WORKERS': '1', 'HTTPZ_POOL': '1'}),
    'Zig std.http': ([ZIG / 'http_std'], {}),
}
SCENARIOS = {'hello': (None, []), 'pipeline-16': (AXON / 'bench/http/pipeline.lua', ['--', '16'])}

JSON_N = '1000000'
CLI = {  # case -> (variants {name: argv}, expected integer output, or None for float energies)
    'json-1M': ({
        'Vif': [VIF / 'vif-library_bench', '0', JSON_N],
        'Rust serde_json::Value': [RUST / 'usability', 'parse', JSON_N],
        'Go encoding/json': [GO / 'json', JSON_N],
        'Bun JSON.parse': ['bun', AXON / 'bench/usability/bun.ts', 'parse', JSON_N],
        'Zig std.json Value': [ZIG / 'json', 'doc-value', JSON_N],
        'Zig std.json Value arena': [ZIG / 'json', 'doc-value-arena', JSON_N],
        'Zig std.json typed': [ZIG / 'json', 'doc-typed', JSON_N],
        'Zig std.json typed arena': [ZIG / 'json', 'doc-typed-arena', JSON_N],
        'Zig std.json typed arena native': [ZIGN / 'json', 'doc-typed-arena', JSON_N],
    }, 513500 * (int(JSON_N) // 1000)),  # independent checksum of the field report
    'nbody-4096-10': ({
        'Vif': [VIF / 'vif-nbody', '4096', '10'],
        'Rust': [RUST / 'nbody', '4096', '10'],
        'Go': [GO / 'nbody', '4096', '10'],
        'Bun': ['bun', AXON / 'bench/core/compute.ts', 'nbody', '4096', '10'],
        'Zig': [ZIG / 'nbody', '4096', '10'],
        'Zig native': [ZIGN / 'nbody', '4096', '10'],
    }, None),  # energies must agree within relative 1e-9
}


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def tree(root):
    """PIDs of root and every descendant (children of every thread)."""
    out, pending = [], [root]
    while pending:
        pid = pending.pop()
        if pid in out: continue
        out.append(pid)
        try:
            for t in os.listdir(f'/proc/{pid}/task'):
                try: pending += map(int, open(f'/proc/{pid}/task/{t}/children').read().split())
                except OSError: pass
        except OSError: pass
    return out


class Tree:
    """CPU (keeping each PID's last value, so exits never subtract) and summed Pss/Rss."""
    def __init__(self, root): self.root, self.cpu = root, {}
    def snapshot(self):
        pss = rss = 0; pids = tree(self.root)
        for pid in pids:
            try:
                f = open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()
                roll = open(f'/proc/{pid}/smaps_rollup').read()
            except OSError: continue
            self.cpu[pid] = (int(f[11]) / TICK, int(f[12]) / TICK)
            pss += int(re.search(r'^Pss:\s+(\d+)', roll, re.M)[1]) * 1024
            rss += int(re.search(r'^Rss:\s+(\d+)', roll, re.M)[1]) * 1024
        return {'user': sum(u for u, _ in self.cpu.values()), 'sys': sum(s for _, s in self.cpu.values()), 'pss': pss, 'rss': rss, 'pids': len(pids)}


def responses(sock, count):
    """Read count complete HTTP/1.1 responses; returns [(status, body)]."""
    data, out = b'', []
    while len(out) < count:
        while b'\r\n\r\n' not in data:
            chunk = sock.recv(65536)
            if not chunk: return out
            data += chunk
        head, data = data.split(b'\r\n\r\n', 1)
        lines = head.split(b'\r\n'); status = int(lines[0].split()[1])
        length = [int(l.split(b':', 1)[1]) for l in lines[1:] if l.lower().startswith(b'content-length:')]
        if not length: return out + [(status, None)]
        while len(data) < length[0]:
            chunk = sock.recv(65536)
            if not chunk: return out
            data += chunk
        out.append((status, data[:length[0]])); data = data[length[0]:]
    return out


def uring_fds(root):
    """io_uring instances open in the server's process tree."""
    n = 0
    for pid in tree(root):
        try: n += sum(os.readlink(f'/proc/{pid}/fd/{fd}') == 'anon_inode:[io_uring]' for fd in os.listdir(f'/proc/{pid}/fd'))
        except OSError: pass
    return n


def validate(port):
    """(hello ok, pipelined ok)"""
    req = b'GET / HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n'
    with socket.create_connection(('127.0.0.1', port), timeout=5) as s:
        s.sendall(req); hello = responses(s, 1) == [(200, b'Hello, World!')]
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=3) as s:
            s.sendall(req * 16); pipelined = responses(s, 16) == [(200, b'Hello, World!')] * 16
    except OSError:
        pipelined = False
    return hello, pipelined


def start(name):
    argv, extra = SERVERS[name]; port = free_port()
    env = {k: v for k, v in os.environ.items() if k not in ONE and k not in ('HYPER_PIPELINE_FLUSH', 'HTTPZ_WORKERS', 'HTTPZ_POOL')}
    env.update(extra)
    srv = subprocess.Popen(['taskset', '-c', SERVER_CPUS, *map(str, argv), str(port)], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(1000):
        try: socket.create_connection(('127.0.0.1', port), timeout=.1).close(); break
        except OSError: time.sleep(.01)
    time.sleep(.3)
    return srv, port


def stop(srv):
    try: os.killpg(srv.pid, signal.SIGTERM)
    except ProcessLookupError: pass
    try: srv.wait(timeout=3)
    except subprocess.TimeoutExpired: os.killpg(srv.pid, signal.SIGKILL); srv.wait()


def unit(v):
    m = re.match(r'([\d.]+)(us|ms|s)', v); return float(m[1]) * {'us': 1, 'ms': 1000, 's': 1e6}[m[2]]


def wrk(port, scenario, duration):
    script, extra = SCENARIOS[scenario]
    cmd = ['taskset', '-c', CLIENT_CPUS, 'wrk', '-t' + WRK_THREADS, '-c64', f'-d{duration}', '--latency', '--timeout', '5s']
    if script: cmd += ['-s', str(script)]
    cmd += [f'http://127.0.0.1:{port}/', *extra]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout


def run_http(name, scenario):
    srv, port = start(name)
    try:
        t = Tree(srv.pid); idle = t.snapshot()
        wrk(port, scenario, '2s')
        peak = {'pss': 0, 'rss': 0, 'pids': 0}; done = threading.Event()
        def sample():
            while not done.is_set():
                s = t.snapshot(); peak.update({k: max(peak[k], s[k]) for k in peak}); done.wait(.1)
        s0 = t.snapshot(); th = threading.Thread(target=sample); th.start()
        c0 = resource.getrusage(resource.RUSAGE_CHILDREN); w0 = time.perf_counter()
        out = wrk(port, scenario, '10s')
        wall = time.perf_counter() - w0; c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        s1 = t.snapshot(); done.set(); th.join()
        threads = len(os.listdir(f'/proc/{srv.pid}/task')) if os.path.exists(f'/proc/{srv.pid}/task') else 0
    finally:
        stop(srv)
    n = int(re.search(r'(\d+) requests in', out)[1])
    pct = {k: unit(v) for k, v in re.findall(r'^\s+(50|99)%\s+(\S+)', out, re.M)}
    return {'rps': float(re.search(r'Requests/sec:\s+([\d.]+)', out)[1]), 'requests': n,
            'p50_us': pct.get('50'), 'p99_us': pct.get('99'),
            'user_us': (s1['user'] - s0['user']) / n * 1e6, 'sys_us': (s1['sys'] - s0['sys']) / n * 1e6,
            'server_cpu': (s1['user'] - s0['user'] + s1['sys'] - s0['sys']) / wall,
            'client_cpu': (c1.ru_utime - c0.ru_utime + c1.ru_stime - c0.ru_stime) / wall,
            'idle_pss': idle['pss'], 'peak_pss': peak['pss'], 'peak_rss': peak['rss'], 'processes': peak['pids'],
            'threads': threads, 'bad': bool(re.search(r'Socket errors|Non-2xx', out)), 'wrk': out}


def http_main(out_path, rounds):
    names = list(SERVERS); ok = {}
    for name in names:
        srv, port = start(name)
        try: ok[name] = (*validate(port), uring_fds(srv.pid))
        finally: stop(srv)
        print('validated', name, 'hello', ok[name][0], 'pipelined', ok[name][1], 'io_uring fds', ok[name][2], flush=True)
        assert ok[name][0], name
    data = {'servers': {n: [str(a) for a in SERVERS[n][0]] + [f'{k}={v}' for k, v in SERVERS[n][1].items()] for n in names},
            'validation': {n: {'hello': ok[n][0], 'pipelined_16': ok[n][1], 'io_uring_fds': ok[n][2]} for n in names},
            'server_cpus': SERVER_CPUS, 'client_cpus': CLIENT_CPUS, 'wrk_threads': WRK_THREADS, 'rounds': rounds, 'results': {}}
    for scenario in SCENARIOS:
        active = [n for n in names if scenario == 'hello' or ok[n][1]]
        rows = {n: [] for n in active}
        for r in range(rounds):
            for name in (active if r % 2 == 0 else active[::-1]):
                rows[name].append(run_http(name, scenario))
                out_path.write_text(json.dumps(data | {'partial': {scenario: rows}}, indent=1))
        data['results'][scenario] = rows
        print('==', scenario, flush=True)
        for name, rs in rows.items():
            med = lambda k: statistics.median(x[k] for x in rs)
            print(f"  {name:22s} req/s {med('rps'):10.0f} ({min(x['rps'] for x in rs):.0f}-{max(x['rps'] for x in rs):.0f})"
                  f"  p50 {med('p50_us') or 0:6.0f} p99 {med('p99_us') or 0:6.0f} us  CPU/req {med('user_us'):.2f}+{med('sys_us'):.2f}"
                  f"  CPUs server {med('server_cpu'):.2f} client {med('client_cpu'):.2f}"
                  f"  peak PSS {med('peak_pss')/2**20:.2f} MiB (max {max(x['peak_pss'] for x in rs)/2**20:.2f})"
                  f"  peak RSS {med('peak_rss')/2**20:.2f} MiB  procs {rs[0]['processes']} threads {rs[0]['threads']}"
                  f"{'  ERRORS' if any(x['bad'] for x in rs) else ''}", flush=True)
        out_path.write_text(json.dumps(data, indent=1))


def run_cli(argv):
    """Wall time of the whole process. CPU time comes from wait4 (the program plus GNU time's negligible own
    share). Peak RSS is GNU time's %M: Linux carries a process's pre-exec high-water mark across exec, so
    rusage of a child forked from this Python driver would never read below the driver's own RSS; time's
    fork starts from a much smaller image (so values under about 2 MiB are still a floor, not exact)."""
    env = {**os.environ, **ONE}
    with tempfile.TemporaryFile() as err, tempfile.NamedTemporaryFile('r') as tf:
        t0 = time.perf_counter()
        p = subprocess.Popen(['/usr/bin/time', '-f', '%M', '-o', tf.name, 'taskset', '-c', '0', *map(str, argv)], env=env,
                             stdout=subprocess.PIPE, stderr=err)
        stdout = p.stdout.read()
        _, status, usage = os.wait4(p.pid, 0); wall = time.perf_counter() - t0
        p.stdout.close(); err.seek(0); stderr = err.read(); maxrss = tf.read().split()
    p.returncode = os.waitstatus_to_exitcode(status)
    assert p.returncode == 0, (argv, stderr[-500:])
    return {'wall_ms': wall * 1000, 'cpu_ms': (usage.ru_utime + usage.ru_stime) * 1000, 'peak_rss_kib': int(maxrss[-1]),
            'output': stdout.decode().strip()}


def cli_main(out_path, rounds):
    rng = random.Random(20261102)
    data = {'rounds': rounds, 'warmups': 2, 'seed': 20261102, 'pinning': 'taskset -c 0', 'env': ONE, 'results': {}}
    for case, (variants, expected) in CLI.items():
        reference = expected
        def check(name, output):
            nonlocal reference
            value = int(output) if expected is not None else float(output.split()[-1])
            if reference is None: reference = value
            if not ((value == reference) if expected is not None else math.isclose(value, reference, rel_tol=1e-9)):
                mismatches.append([name, output]); print('MISMATCH', case, name, output, 'reference', reference, flush=True)
        runs, mismatches = {n: [] for n in variants}, []
        for r in range(rounds + 2):
            order = list(variants); rng.shuffle(order)
            for name in order:
                x = run_cli(variants[name]); check(name, x['output'])
                if r >= 2: runs[name].append(x)
        data['results'][case] = {'variants': {n: list(map(str, a)) for n, a in variants.items()}, 'reference': reference, 'mismatches': mismatches, 'runs': runs}
        out_path.write_text(json.dumps(data, indent=1))
        print('==', case, 'output', reference, 'mismatches', len(mismatches), flush=True)
        for name, rs in runs.items():
            w = [x['wall_ms'] for x in rs]
            print(f"  {name:32s} {statistics.median(w):9.1f} ms ({min(w):.1f}-{max(w):.1f})  cpu {statistics.median(x['cpu_ms'] for x in rs):9.1f}"
                  f"  peak RSS {max(x['peak_rss_kib'] for x in rs)/1024:7.1f} MiB", flush=True)


if __name__ == '__main__':
    mode, out, rounds = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
    # The driver and its samplers share the client's CPUs; the server's CPU and its SMT sibling stay free.
    os.sched_setaffinity(0, {int(c) for c in CLIENT_CPUS.split(',')})
    {'http': http_main, 'cli': cli_main}[mode](out, rounds)
