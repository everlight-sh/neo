#!/usr/bin/env python3
"""hab2.py ROUNDS PATH OUT.json 'name|ENV=.. cmd' ... : interleaved run_http.py-style runs of several servers
(fresh server, wrk -c64 2 s warm-up + 10 s; SERVER_CPUS/CLIENT_CPUS/WRK_THREADS default 0 / 1 / 1).
Per run: req/s, p50/p99, server CPU us/request and CPUs used (session user+sys / wall),
client CPUs used (wrk user+sys from rusage / wall), and every CPU's busy share (/proc/stat).
Rounds alternate the order. Prints per-run lines, then medians with ranges."""
import json, os, re, resource, shlex, signal, socket, statistics, subprocess, sys, time
rounds, path, out_path = int(sys.argv[1]), sys.argv[2], sys.argv[3]
variants = [a.split('|', 1) for a in sys.argv[4:]]
SC, CC, WT = os.environ.get('SERVER_CPUS', '0'), os.environ.get('CLIENT_CPUS', '1'), os.environ.get('WRK_THREADS', '1')
TICK = os.sysconf('SC_CLK_TCK')
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
def cpu(g):
    u = s = 0
    for d in os.listdir('/proc'):
        if not d.isdigit(): continue
        try: f = open(f'/proc/{d}/stat').read().rsplit(')', 1)[1].split()
        except OSError: continue
        if int(f[2]) == g: u += int(f[11]); s += int(f[12])
    return (u + s) / TICK
def stat():
    out = {}
    for l in open('/proc/stat'):
        if re.match(r'cpu\d', l):
            f = l.split(); v = list(map(int, f[1:9])); out[f[0]] = (sum(v) - v[3] - v[4], sum(v))
    return out
def unit(v):
    m = re.match(r'([\d.]+)(us|ms|s)', v); return float(m[1]) * {'us': 1, 'ms': 1000, 's': 1e6}[m[2]]
def wrk(port, d):
    cmd = ['taskset', '-c', CC, 'wrk', '-t' + WT, '-c64', f'-d{d}', '--latency', '--timeout', '5s', f'http://127.0.0.1:{port}{path}']
    return subprocess.run(cmd, capture_output=True, text=True).stdout
res = {n: [] for n, _ in variants}
for r in range(rounds):
    for name, spec in (variants if r % 2 == 0 else variants[::-1]):
        words = shlex.split(spec); env = dict(os.environ)
        while words and '=' in words[0] and not words[0].startswith('/'):
            k, v = words.pop(0).split('=', 1); env[k] = v
        port = free_port()
        srv = subprocess.Popen(['taskset', '-c', SC, *words, str(port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        for _ in range(300):
            try: socket.create_connection(('127.0.0.1', port), timeout=.1).close(); break
            except OSError: time.sleep(.01)
        time.sleep(.2); wrk(port, '2s')
        s0 = cpu(srv.pid); p0 = stat(); c0 = resource.getrusage(resource.RUSAGE_CHILDREN); t0 = time.perf_counter()
        out = wrk(port, '10s')
        wall = time.perf_counter() - t0; c1 = resource.getrusage(resource.RUSAGE_CHILDREN); p1 = stat(); s1 = cpu(srv.pid)
        os.killpg(srv.pid, signal.SIGTERM); srv.wait()
        n = int(re.search(r'(\d+) requests in', out)[1]); rps = float(re.search(r'Requests/sec:\s+([\d.]+)', out)[1])
        pct = {k: unit(v) for k, v in re.findall(r'^\s+(50|99)%\s+(\S+)', out, re.M)}
        busy = {c: round((p1[c][0] - p0[c][0]) / max(1, p1[c][1] - p0[c][1]), 3) for c in p1}
        row = {'rps': rps, 'p50': pct['50'], 'p99': pct['99'], 'cpu_us': (s1 - s0) / n * 1e6, 'server_cpu': (s1 - s0) / wall,
               'client_cpu': (c1.ru_utime - c0.ru_utime + c1.ru_stime - c0.ru_stime) / wall, 'busy': busy, 'errors': bool(re.search(r'Socket errors|Non-2xx', out))}
        res[name].append(row)
        print(f"{name:12s} {rps:9.0f} req/s p50 {row['p50']:6.0f} p99 {row['p99']:6.0f} us  srv {row['cpu_us']:5.2f} us/req {row['server_cpu']:.2f} CPU  wrk {row['client_cpu']:.2f} CPU  busy {' '.join(f'{c[3:]}:{b:.2f}' for c, b in busy.items())}{' ERR' if row['errors'] else ''}", flush=True)
        json.dump({'rounds': rounds, 'path': path, 'server_cpus': SC, 'client_cpus': CC, 'wrk_threads': WT, 'variants': dict(variants), 'results': res}, open(out_path, 'w'), indent=1)
for name, rs in res.items():
    m = lambda k: statistics.median(x[k] for x in rs)
    print(f"== {name:12s} median {m('rps'):9.0f} req/s (range {min(x['rps'] for x in rs):.0f}-{max(x['rps'] for x in rs):.0f})  p50 {m('p50'):5.0f} p99 {m('p99'):6.0f} us"
          f"  srv {m('cpu_us'):.2f} us/req {m('server_cpu'):.2f} CPU  wrk {m('client_cpu'):.2f} CPU  busy " +
          ' '.join(f"{c[3:]}:{statistics.median(x['busy'][c] for x in rs):.2f}" for c in rs[0]['busy']), flush=True)
