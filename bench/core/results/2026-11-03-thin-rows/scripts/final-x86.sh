#!/bin/bash
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
lscpu | grep -E "Model name|^CPU\(s\)"; uname -r
mkdir -p /root/bin-final && cd /root/new && for p in stencil sieve nbody mandel; do ./neo build examples/$p.neo -o /root/bin-final/neo-$p --no-cache >/dev/null || echo "build fail $p"; done
NEO_AFTER=/root/bin-final NEO_BEFORE=/root/bin-main ZIG=/root/zig-baseline/bin ZIG_NATIVE=/root/zig-native/bin RUST=/root/main/bench/rust/target/release \
  python3 bench/compute-margins/run.py /root/final-x86.json 7 1,4 madvise,never 2>&1 | tail -5
python3 /root/rng.py /root/final-x86.json
cat /sys/kernel/mm/transparent_hugepage/enabled
python3 bench/fetch/run.py --rounds 5 --schemes https 2>&1 | tail -3
ls -d bench/fetch/results/20*/ | tail -1
echo FINALX86-DONE
