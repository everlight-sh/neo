#!/bin/bash
# keep-ab.sh ROUNDS: kept-alive HTTPS GET /1m, main's client against the new one,
# alternating which goes first. Per process: the p50 and mean of 100 requests
# (us), and the client's own task-clock, cycles, instructions, context switches
# and page faults from perf stat. PERF=0 runs the clients without perf stat and
# prints only the timings.
R=${R:-$(ls -d /root/main/bench/fetch/results/*/ | tail -1)}; R=${R%/}
taskset -c 0 $R/go_server 18080 18443 $R/leaf.pem $R/leaf.key >/dev/null 2>&1 & SERVER=$!
for i in $(seq 1 100); do (exec 3<>/dev/tcp/127.0.0.1/18443) 2>/dev/null && break; sleep 0.1; done
one() {
  if [ "${PERF:-1}" = 0 ]; then
    taskset -c 0 /root/fetch_$1 18443 /1m 100 1048576 1 $R/ca.der > /root/keep-out.txt; : > /root/keep-perf.csv
  else perf stat -x, -o /root/keep-perf.csv -e task-clock,cycles,instructions,context-switches,page-faults -- taskset -c 0 /root/fetch_$1 18443 /1m 100 1048576 1 $R/ca.der > /root/keep-out.txt; fi
  python3 - $1 <<'PY'
import sys
l = open('/root/keep-out.txt').read().splitlines(); v = sorted(int(x) for x in l[1].split())
assert int(l[0].split()[1]) == len(v) == 100, l[0]
p = {f.split(',')[2]: float(f.split(',')[0]) for f in open('/root/keep-perf.csv') if f.count(',') > 3}
t = f"{sys.argv[1]} p50={v[49]/1000:.1f} mean={sum(v)/len(v)/1000:.1f}"
print(t if not p else t + f" task_ms={p['task-clock']:.1f} cycles_M={p['cycles']/1e6:.1f} instructions_M={p['instructions']/1e6:.1f} switches={p['context-switches']:.0f} faults={p['page-faults']:.0f}")
PY
}
for round in $(seq 1 ${1:-15}); do
  if [ $((round % 2)) -eq 1 ]; then one main; one new; else one new; one main; fi
done
kill $SERVER
echo KEEP-DONE
