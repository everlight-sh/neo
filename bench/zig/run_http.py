#!/usr/bin/env python3
"""Vif vs Zig HTTP servers on a 2-vCPU Linux box.

Method follows the 2-vCPU runs of RESULTS-http-uring-x86-linux-2026-10-31.md
and bench/http/compare.py: the server is pinned to CPU 0 with one worker, wrk -t1
-c64 is pinned to CPU 1; every run starts a fresh server, 2 s warm-up, then a
10 s measured run; rounds alternate the server order; medians are reported.
Server CPU per request is user + system time of every process in the
server's session (/proc), divided by completed requests. Memory is the peak
of Rss summed over the session's processes (smaps_rollup), sampled every
250 ms during the measured run. Every server is validated against Python
references (the compare.py ones plus /page/50 against React's output) first.

SERVER_CPUS, CLIENT_CPUS and WRK_THREADS override the 0 / 1 / 1 defaults (the
4-vCPU setup: SERVER_CPUS=0 CLIENT_CPUS=2,3 WRK_THREADS=2, see
RESULTS-zig-x86-linux-2026-11-02.md). Each run also records the client's
CPU use (wrk's user + system time over the measured 10 s, in CPUs) and the
server's (its session's time over the same 10 s), which show which side
limited the run.

With BIN_BEFORE set, a 'Vif before' server (examples/http.neo built by an
earlier compiler/runtime) runs in the same rounds.

usage: run_http.py OUT.json ROUNDS [scenario ...]
"""
import http.client, json, math, os, re, resource, signal, socket, statistics, subprocess, sys, threading, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'bench/http'
BIN = Path(os.environ.get('BIN', '/root/bin'))
ZIG = Path(os.environ.get('ZIGBIN', '/root/zig-baseline/bin'))
SERVER_CPUS = os.environ.get('SERVER_CPUS', '0')
CLIENT_CPUS = os.environ.get('CLIENT_CPUS', '1')
WRK_THREADS = os.environ.get('WRK_THREADS', '1')
TICK = os.sysconf('SC_CLK_TCK')

SERVERS = {
    'Vif': ([BIN / 'vif-http'], {'NEO_THREADS': '1'}),
    'Zig std.http': ([ZIG / 'http_std'], {}),
    'Zig http.zig 1+1': ([ZIG / 'http_httpz'], {'HTTPZ_WORKERS': '1', 'HTTPZ_POOL': '1'}),
    'Zig http.zig default': ([ZIG / 'http_httpz'], {}),
}
if os.environ.get('BIN_BEFORE'): SERVERS['Vif before'] = ([Path(os.environ['BIN_BEFORE']) / 'vif-http'], {'NEO_THREADS': '1'})
# VIF_EPOLL=1 adds the same Vif binary on its epoll backend (NEO_HTTP_URING=0).
if os.environ.get('VIF_EPOLL') == '1': SERVERS['Vif epoll'] = ([BIN / 'vif-http'], {'NEO_THREADS': '1', 'NEO_HTTP_URING': '0'})
# name -> (path, wrk lua script or None, extra wrk args)
SCENARIOS = {
    'hello': ('/', None, []),
    'pipeline-16': ('/', HERE / 'pipeline.lua', ['--', '16']),
    'smooth-10000': ('/smooth/10000', None, []),
    'nbody-256-4': ('/nbody', HERE / 'post_nbody.lua', []),
    'page-50': ('/page/50', None, []),
}
# http.zig answers only the first request of a pipelined write (checked by
# hand: 16 pipelined GETs on one socket get 1 response), so wrk's pipeline
# script stalls on it until its 5 s timeout; it is not run there.
SKIP = {('pipeline-16', 'Zig http.zig 1+1'), ('pipeline-16', 'Zig http.zig default')}


def checksum(n):
    a = [(i * 2654435761) % 1000003 for i in range(n)]
    for _ in range(32):
        a = [a[i] if i == 0 or i + 1 == n else (a[i-1] + 2*a[i] + a[i+1]) % 1000003 for i in range(n)]
    return sum(a)


def nbody_reference(n=256, steps=4):
    bodies = [[(i*2654435761) % 1009/1009, (i*40503) % 1013/1013, (i*69069) % 1019/1019, 0., 0., 0., 1/n] for i in range(n)]
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


REFS = {1000: checksum(1000), 10000: checksum(10000), 'nbody': nbody_reference(),
        'page': (ROOT / 'bench/react/reference_50.html').read_bytes()}


def validate(port):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
    try:
        c.request('GET', '/'); r = c.getresponse()
        assert (r.status, r.read()) == (200, b'Hello, World!')
        c.request('GET', '/missing'); r = c.getresponse(); r.read(); assert r.status == 404, r.status
        for n in (1000, 10000):
            c.request('GET', f'/smooth/{n}'); r = c.getresponse(); raw = r.read(); body = json.loads(raw)
            assert r.status == 200 and body == {'n': n, 'passes': 32, 'checksum': REFS[n]}, body
            assert raw == json.dumps(body, separators=(',', ':')).encode(), raw
            assert r.getheader('Content-Type', '').startswith('application/json')
        c.request('GET', '/smooth/abc'); r = c.getresponse(); r.read(); assert r.status == 400, r.status
        c.request('POST', '/nbody', body='{"n":256,"steps":4}', headers={'Content-Type': 'application/json'})
        r = c.getresponse(); body = json.loads(r.read())
        assert r.status == 200 and body['n'] == 256 and body['steps'] == 4 and math.isclose(body['energy'], REFS['nbody'], abs_tol=1e-9), body
        c.request('POST', '/nbody', body='{"n":0}', headers={'Content-Type': 'application/json'})
        r = c.getresponse(); r.read(); assert r.status == 400, r.status
        c.request('GET', '/page/50'); r = c.getresponse(); body = r.read()
        assert r.status == 200 and body == REFS['page'], (r.status, len(body))
        assert r.getheader('Content-Type', '').lower().startswith('text/html')
        c.request('GET', '/page/0'); r = c.getresponse(); r.read(); assert r.status == 400, r.status
    finally:
        c.close()


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def unit(v):
    m = re.match(r'([\d.]+)(us|ms|s)', v); x = float(m[1]); return x*{'us': 1, 'ms': 1000, 's': 1e6}[m[2]]


def session(group):
    out = []
    for d in os.listdir('/proc'):
        if not d.isdigit(): continue
        try: f = open(f'/proc/{d}/stat').read().rsplit(')', 1)[1].split()
        except OSError: continue
        if int(f[2]) == group: out.append((int(d), int(f[11]), int(f[12])))
    return out


def cpu(group):
    rows = session(group)
    return sum(r[1] for r in rows)/TICK, sum(r[2] for r in rows)/TICK


def rss(group):
    total = 0
    for pid, _, _ in session(group):
        try: total += int(re.search(r'^Rss:\s+(\d+)', open(f'/proc/{pid}/smaps_rollup').read(), re.M)[1])*1024
        except (OSError, TypeError): pass
    return total


def threads(pid):
    try: return int(re.search(r'^Threads:\s+(\d+)', open(f'/proc/{pid}/status').read(), re.M)[1])
    except OSError: return 0


def start(name):
    cmd, extra = SERVERS[name]; p = free_port()
    env = {**os.environ, **extra}
    srv = subprocess.Popen(['taskset', '-c', SERVER_CPUS, *map(str, cmd), str(p)], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(500):
        try: socket.create_connection(('127.0.0.1', p), timeout=.1).close(); break
        except OSError: time.sleep(.01)
    time.sleep(.2)
    return srv, p


def stop(srv):
    os.killpg(srv.pid, signal.SIGTERM)
    try: srv.wait(timeout=3)
    except subprocess.TimeoutExpired: os.killpg(srv.pid, signal.SIGKILL); srv.wait()


def wrk(port, scenario, duration):
    path, script, extra = SCENARIOS[scenario]
    cmd = ['taskset', '-c', CLIENT_CPUS, 'wrk', '-t' + WRK_THREADS, '-c64', f'-d{duration}', '--latency', '--timeout', '5s']
    if script: cmd += ['-s', str(script)]
    cmd += [f'http://127.0.0.1:{port}{path}', *extra]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout


def run(name, scenario):
    srv, port = start(name)
    try:
        idle = rss(srv.pid)
        wrk(port, scenario, '2s')
        peak = [0]; done = threading.Event()
        def sample():
            while not done.is_set():
                peak[0] = max(peak[0], rss(srv.pid)); done.wait(.25)
        t = threading.Thread(target=sample); u0, s0 = cpu(srv.pid); t.start()
        c0 = resource.getrusage(resource.RUSAGE_CHILDREN); w0 = time.perf_counter()
        out = wrk(port, scenario, '10s')
        u1, s1 = cpu(srv.pid); done.set(); t.join()
        c1 = resource.getrusage(resource.RUSAGE_CHILDREN); wall = time.perf_counter() - w0
        nthreads = threads(srv.pid)
    finally:
        stop(srv)
    n = int(re.search(r'(\d+) requests in', out)[1])
    pct = {k: unit(v) for k, v in re.findall(r'^\s+(50|90|99)%\s+(\S+)', out, re.M)}
    bad = bool(re.search(r'Socket errors|Non-2xx', out))
    return {'rps': float(re.search(r'Requests/sec:\s+([\d.]+)', out)[1]), 'requests': n,
            'p50': pct.get('50'), 'p99': pct.get('99'), 'user_us': (u1-u0)/n*1e6, 'sys_us': (s1-s0)/n*1e6,
            'client_cpu': (c1.ru_utime - c0.ru_utime + c1.ru_stime - c0.ru_stime) / wall,
            'server_cpu': (u1 - u0 + s1 - s0) / wall,
            'idle_rss': idle, 'peak_rss': peak[0], 'threads': nthreads, 'bad': bad, 'wrk': out}


def main():
    out_path, rounds = Path(sys.argv[1]), int(sys.argv[2])
    scenarios = sys.argv[3:] or list(SCENARIOS)
    names = list(SERVERS)
    for name in names:
        srv, port = start(name)
        try: validate(port)
        finally: stop(srv)
        print('validated', name, flush=True)
    data = {'servers': {n: [str(c) for c in SERVERS[n][0]] + [f'{k}={v}' for k, v in SERVERS[n][1].items()] for n in names},
            'server_cpus': SERVER_CPUS, 'client_cpus': CLIENT_CPUS, 'wrk_threads': WRK_THREADS, 'rounds': rounds, 'results': {}}
    for scenario in scenarios:
        active = [n for n in names if (scenario, n) not in SKIP]
        rows = {n: [] for n in active}
        for r in range(rounds):
            for name in (active if r % 2 == 0 else active[::-1]):
                rows[name].append(run(name, scenario))
                out_path.write_text(json.dumps(data | {'partial': {scenario: rows}}, indent=1))
        data['results'][scenario] = rows
        print('==', scenario, flush=True)
        for name, rs in rows.items():
            med = lambda k: statistics.median(x[k] for x in rs)
            print(f"  {name:22s} req/s {med('rps'):9.0f} (runs {min(x['rps'] for x in rs):.0f}-{max(x['rps'] for x in rs):.0f})"
                  f"  p50 {med('p50'):7.0f}  p99 {med('p99'):7.0f} us  CPU/req {med('user_us'):.2f}+{med('sys_us'):.2f}"
                  f"  CPUs server {med('server_cpu'):.2f} client {med('client_cpu'):.2f}"
                  f"  peak RSS {max(x['peak_rss'] for x in rs)/2**20:.1f} MiB  threads {rs[0]['threads']}"
                  f"{'  ERRORS' if any(x['bad'] for x in rs) else ''}", flush=True)
        out_path.write_text(json.dumps(data, indent=1))


if __name__ == '__main__':
    main()
