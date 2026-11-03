#!/bin/bash
# ARM: the final tree (After) vs main (Before) vs Rust and Go under both THP settings, then the HTTPS harness.
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
lscpu | grep -E "Model name|^CPU\(s\)|Flags"; uname -r
mkdir -p /root/bin-final && cd /root/new && for p in stencil sieve nbody mandel; do ./neo build examples/$p.neo -o /root/bin-final/neo-$p --no-cache >/dev/null || echo "build fail $p"; done
for thp in madvise never; do
  echo $thp > /sys/kernel/mm/transparent_hugepage/enabled
  echo "######## THP $thp"
  python3 bench/core/compute_compare.py /root/final-arm-$thp.json 7 --variant After=/root/bin-final --variant Before=/root/bin-main --rust /root/comp/rust --go /root/comp/go --workers 1,4 --cases all 2>&1 | tail -3
  python3 /root/ranges.py /root/final-arm-$thp.json | sed "s/^/$thp /"
done
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
python3 bench/fetch/run.py --rounds 5 --schemes https 2>&1 | tail -3
ls -d bench/fetch/results/20*/ | tail -1
echo FINALARM-DONE
