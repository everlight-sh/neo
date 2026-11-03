#!/bin/bash
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
R=/root/main/bench/fetch/results/2026-11-03-073606
cat /sys/kernel/mm/transparent_hugepage/enabled
taskset -c 0 $R/go_server 18080 18443 $R/leaf.pem $R/leaf.key >/dev/null 2>&1 & SERVER=$!
for i in $(seq 1 100); do (exec 3<>/dev/tcp/127.0.0.1/18443) 2>/dev/null && break; sleep 0.1; done
for v in main new; do
  echo "== perf stat $v keep"
  perf stat -e task-clock,cycles,instructions,page-faults -- taskset -c 0 /root/fetch_$v 18443 /1m 200 1048576 1 $R/ca.der 2>&1 >/dev/null | grep -E 'task-clock|cycles|instructions|faults|elapsed|user|sys' | sed 's/  */ /g'
  perf record -q -o /root/ab-$v.data -- taskset -c 0 /root/fetch_$v 18443 /1m 200 1048576 1 $R/ca.der >/dev/null 2>&1
  perf report -i /root/ab-$v.data --comm fetch_$v --no-children --sort sym --stdio 2>/dev/null | grep -E '^ +[0-9]' | head -14
done
kill $SERVER
echo PROFAB-DONE
