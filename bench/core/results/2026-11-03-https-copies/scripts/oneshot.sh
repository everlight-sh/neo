#!/bin/bash
# Interleaved one request per process (GET /hello over HTTPS, new connection): main's client against the new one.
R=${R:-$(ls -d /root/main/bench/fetch/results/*/ | tail -1)}; R=${R%/}
taskset -c 0 $R/go_server 18080 18443 $R/leaf.pem $R/leaf.key >/dev/null 2>&1 & SERVER=$!
for i in $(seq 1 100); do (exec 3<>/dev/tcp/127.0.0.1/18443) 2>/dev/null && break; sleep 0.1; done
python3 - "$R" <<'PY'
import subprocess, sys, time, statistics
R = sys.argv[1]
bins = {'main': '/root/fetch_main', 'new': '/root/fetch_new'}
walls = {k: [] for k in bins}
for k in range(402):
    for name, b in (bins.items() if k % 2 == 0 else reversed(list(bins.items()))):
        cmd = ['taskset', '-c', '0', b, '18443', '/hello', '1', '13', '0', R + '/ca.der']
        t = time.perf_counter(); subprocess.run(cmd, capture_output=True, check=True); w = time.perf_counter() - t
        if k >= 2: walls[name].append(w * 1000)
for name, w in walls.items():
    w.sort(); print(name, 'median %.3f ms  p10 %.3f  p90 %.3f  n=%d' % (statistics.median(w), w[len(w)//10], w[len(w)*9//10], len(w)))
PY
kill $SERVER
echo ONESHOT-DONE
