# compute2c.sh : the 2-vCPU compute/JSON table on the final tree (after vs before vs Zig), loop-alignment A/Bs,
# bench/run.py workloads, sieve placement, allocation-pattern RSS, the full suite
R=/root/results; mkdir -p $R
echo "== faults"; date
{ for c in "stencil 50000000 20" "stencil 1000000 20" "sieve 100000000"; do set -- $c; p=$1; shift
    for t in 1 2; do for b in /root/bin/vif-$p /root/bin-before/vif-$p /root/zig-baseline/bin/$p; do
      echo "== $b $* threads=$t"; AXON_THREADS=$t ZIG_THREADS=$t /usr/bin/time -f 'wall %e s user %U s sys %S s maxrss %M KiB minor faults %R' taskset -c 0-$((t-1)) $b "$@" > /tmp/out.txt 2>/tmp/err.txt; cat /tmp/out.txt /tmp/err.txt
      done; done; done
  echo "thp_fault_alloc $(grep thp_fault_alloc /proc/vmstat)"; } > $R/faults.log 2>&1
cd /root/axon-after/bench/zig
echo "== compute"; date
BIN=/root/bin BIN_BEFORE=/root/bin-before python3 run_cli.py compute $R/compute.json 7 > $R/compute.txt 2>&1; tail -20 $R/compute.txt
echo "== json"; date
BIN=/root/bin BIN_BEFORE=/root/bin-before python3 run_cli.py json $R/json.json 9 > $R/json.txt 2>&1; tail -20 $R/json.txt
cd /root
echo "== loop alignment A/B (align32 = final, align16 = final without -falign-loops=32)"; date
{ echo "## JSON doc x1M, CPU 0"; python3 ab.py 15 0 1 "align32=/root/bin/vif-library_bench 0 1000000" "align16=/root/bin-noalign/vif-library_bench 0 1000000" "before=/root/bin-before/vif-library_bench 0 1000000"
  echo "## orders 1000 x1000, CPU 0"; python3 ab.py 15 0 1 "align32=/root/bin/vif-orders_json 1000 1000" "align16=/root/bin-noalign/vif-orders_json 1000 1000" "before=/root/bin-before/vif-orders_json 1000 1000"
  echo "## sieve 1e8, 1 worker"; python3 ab.py 11 0 1 "align32=/root/bin/vif-sieve 100000000" "align16=/root/bin-noalign/vif-sieve 100000000"
  echo "## sieve 1e8, 2 workers"; python3 ab.py 11 0-1 2 "align32=/root/bin/vif-sieve 100000000" "align16=/root/bin-noalign/vif-sieve 100000000"
  echo "## stencil 50M x20, 1 worker"; python3 ab.py 7 0 1 "align32=/root/bin/vif-stencil 50000000 20" "align16=/root/bin-noalign/vif-stencil 50000000 20"
} > $R/align-ab.txt 2>&1; cat $R/align-ab.txt
echo "== bench/run.py workloads"; date
cd /root/axon-after/bench/go && for p in mandel stencil nbody; do GOTOOLCHAIN=local GOWORK=off go build -o /root/go-$p ./$p; done
cd /root
{ go version
  echo "## mandel 3000 3000 2000"; python3 ab.py 7 0-1 2 after=bin/vif-mandel\ 3000\ 3000\ 2000 before=bin-before/vif-mandel\ 3000\ 3000\ 2000 go=go-mandel\ 3000\ 3000\ 2000
  echo "## stencil 50000000 20"; python3 ab.py 7 0-1 2 after=bin/vif-stencil\ 50000000\ 20 before=bin-before/vif-stencil\ 50000000\ 20 go=go-stencil\ 50000000\ 20
  echo "## stencil_small 1000000 2000"; python3 ab.py 7 0-1 2 after=bin/vif-stencil\ 1000000\ 2000 before=bin-before/vif-stencil\ 1000000\ 2000 go=go-stencil\ 1000000\ 2000
  echo "## nbody 16384 10"; python3 ab.py 5 0-1 2 after=bin/vif-nbody\ 16384\ 10 before=bin-before/vif-nbody\ 16384\ 10 go=go-nbody\ 16384\ 10
} > $R/runpy.txt 2>&1; cat $R/runpy.txt
echo "== placement"; date
bash /root/placement.sh > $R/placement.txt 2>&1; tail -40 $R/placement.txt
echo "== rss"; date
mkdir -p /root/rss; (cd /root/w-before && ./axon build /root/rss/alloc_pattern.ax -o /root/rss/ap-before --no-cache >/dev/null) && (cd /root/axon-after && ./axon build /root/rss/alloc_pattern.ax -o /root/rss/ap-after --no-cache >/dev/null)
{ cd /root/rss; for args in '20000 40 0' '20000 40 10000000' '2000 400 0' '50000 24 20000000'; do for t in 1 2; do for b in ap-before ap-after; do
  echo "$b threads=$t args=$args: $(AXON_THREADS=$t timeout 120 /usr/bin/time -f 'maxrss_kib %M minflt %R wall %e' ./$b $args 2>&1 | tr '\n' ' ')"
  done; done; done; } > $R/rss-alloc-pattern.log 2>&1; cat $R/rss-alloc-pattern.log
objdump -d --no-show-raw-insn /root/bin/vif-sieve | awk '/<main>:/,/^$/' | grep -B2 -A3 'movb   $0x0,(%r' > $R/sieve-mark-loop.txt
echo "== suite"; date
rm -rf /root/suite-tree && cp -r /root/axon-after /root/suite-tree && bash /root/suite.sh /root/suite-tree > $R/suite.txt 2>&1; cp /root/jobs/suite-axon-test.log $R/suite-axon-test-tail.log; cat $R/suite.txt
date; echo ALL-DONE
