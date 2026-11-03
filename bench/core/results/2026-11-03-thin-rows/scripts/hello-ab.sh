#!/bin/bash
# Interleaved A/B of GET /hello (13 bytes): main's client against the patched one, new and resumed connections,
# with Bun and Rust in the same rounds. Per-request p50 (us), 300 requests per run.
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
R=${R:-/root/main/bench/fetch/results/2026-11-03-080649}
taskset -c 0 $R/go_server 18080 18443 $R/leaf.pem $R/leaf.key >/dev/null 2>&1 & SERVER=$!
for i in $(seq 1 100); do (exec 3<>/dev/tcp/127.0.0.1/18443) 2>/dev/null && break; sleep 0.1; done
p50() { python3 -c "import sys;l=sys.stdin.read().splitlines();v=sorted(int(x) for x in l[1].split());assert int(l[0].split()[1])==len(v),l[0];print(f'{v[len(v)//2-1]/1000:.1f}')"; }
for round in $(seq 1 ${ROUNDS:-5}); do
  line="round $round"
  for spec in "main-new|/root/fetch_main|0|ca.der" "new-new|/root/fetch_new|0|ca.der" "bun-new|bun /root/main/bench/fetch/fetch.ts|0|ca.pem" \
              "main-res|/root/fetch_main|2|ca.der" "new-res|/root/fetch_new|2|ca.der" "rust-new|$R/rust_client|0|ca.pem" \
              "main-keep|/root/fetch_main|1|ca.der" "new-keep|/root/fetch_new|1|ca.der"; do
    IFS='|' read name cmd mode ca <<< "$spec"
    v=$(taskset -c 0 $cmd 18443 /hello 300 13 $mode $R/$ca | p50)
    line="$line  $name=$v"
  done
  echo "$line"
done
kill $SERVER
echo HELLO-DONE
