#!/bin/bash
# account.sh ROUNDS [KEEP]: where the wall time of 100 HTTPS GET /1m goes, main's
# client against the new one, alternating which goes first. Per client process:
# wall ms, the client's CPU ms (rusage), the Go server's CPU ms over the same span
# (summed /proc schedstat of its threads), what is left of CPU 0 (wall - both),
# and the p50 of the requests (us). KEEP is fetch.neo's mode, 1 (kept-alive) by default.
R=${R:-$(ls -d /root/main/bench/fetch/results/*/ | tail -1)}; R=${R%/}
taskset -c 0 $R/go_server 18080 18443 $R/leaf.pem $R/leaf.key >/dev/null 2>&1 & SERVER=$!
for i in $(seq 1 100); do (exec 3<>/dev/tcp/127.0.0.1/18443) 2>/dev/null && break; sleep 0.1; done
python3 - "$R" "$SERVER" "${1:-10}" "${2:-1}" <<'PY'
import glob, resource, statistics, subprocess, sys, time
R, server, rounds, keep = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
def server_ns():
    total = 0
    for f in glob.glob(f'/proc/{server}/task/*/schedstat'):
        try: total += int(open(f).read().split()[0])
        except OSError: pass
    return total
rows = {'main': [], 'new': []}
for k in range(rounds):
    for name in (['main', 'new'] if k % 2 == 0 else ['new', 'main']):
        before = resource.getrusage(resource.RUSAGE_CHILDREN); s0 = server_ns(); t0 = time.perf_counter()
        out = subprocess.run(['taskset', '-c', '0', f'/root/fetch_{name}', '18443', '/1m', '100', '1048576', keep, R + '/ca.der'], capture_output=True, text=True, check=True).stdout
        wall = (time.perf_counter() - t0) * 1000; s1 = server_ns(); after = resource.getrusage(resource.RUSAGE_CHILDREN)
        lines = out.splitlines(); v = sorted(int(x) for x in lines[1].split()); assert int(lines[0].split()[1]) == len(v) == 100, lines[0]
        client = (after.ru_utime - before.ru_utime + after.ru_stime - before.ru_stime) * 1000; srv = (s1 - s0) / 1e6
        row = (wall, client, srv, wall - client - srv, v[49] / 1000); rows[name].append(row)
        print(f'{name} wall_ms={row[0]:.1f} client_ms={row[1]:.1f} server_ms={row[2]:.1f} rest_ms={row[3]:.1f} p50_us={row[4]:.1f}', flush=True)
for name, r in rows.items():
    print(f'median {name}', ' '.join(f'{k}={statistics.median(x[i] for x in r):.1f}' for i, k in enumerate(('wall_ms', 'client_ms', 'server_ms', 'rest_ms', 'p50_us'))))
PY
kill $SERVER
echo ACCOUNT-DONE
