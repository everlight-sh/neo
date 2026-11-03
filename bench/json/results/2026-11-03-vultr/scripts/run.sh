# run.sh : the measured run (after setup.sh and build.sh), then the counters in counters.txt
cd /root && mkdir -p /root/final && . /root/.cargo/env
export PATH=$PATH:/root/.bun/bin:/usr/local/go/bin:/root/zig-x86_64-linux-0.17.0
WARMUP=2 python3 /root/axon/bench/json/x86.py /root/final/runs.json 21 doc-typed orders-typed doc-dynamic orders-dynamic
for p in "document_decoder 1000000" "orders_decoder 1000 1000" "library_bench 0 1000000" "orders_json 1000 1000"; do
  for d in before after; do
    echo "$d $p $(NEO_THREADS=1 perf stat -x, -e instructions:u,cycles:u taskset -c 1 /root/$d/$p 2>&1 >/dev/null | cut -d, -f1 | tr '\n' ' ')"
  done
done
