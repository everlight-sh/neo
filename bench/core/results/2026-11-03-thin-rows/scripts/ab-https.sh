#!/bin/bash
# Interleaved A/B of the HTTPS /1m rows: main's fetch_neo against the patched
# tree's, with Bun and Rust in the same rounds. Prints per-request p50 (us)
# from each client's own timings, 100 requests per run.
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
R=${R:-/root/main/bench/fetch/results/2026-11-03-073606}
cd /root/new && ./neo build bench/fetch/fetch.neo -o /root/fetch_new --no-cache >/dev/null || exit 1
cp $R/fetch_neo /root/fetch_main
taskset -c 0 $R/go_server 18080 18443 $R/leaf.pem $R/leaf.key >/dev/null 2>&1 & SERVER=$!
for i in $(seq 1 100); do (exec 3<>/dev/tcp/127.0.0.1/18443) 2>/dev/null && break; sleep 0.1; done
p50() { python3 -c "import sys;l=sys.stdin.read().splitlines();v=sorted(int(x) for x in l[1].split());assert int(l[0].split()[1])==len(v),l[0];print(f'{v[len(v)//2-1]/1000:.1f}')"; }
for round in $(seq 1 ${ROUNDS:-7}); do
  line="round $round"
  for spec in "main-new|/root/fetch_main|0|ca.der" "new-new|/root/fetch_new|0|ca.der" "bun-new|bun /root/main/bench/fetch/fetch.ts|0|ca.pem" \
              "main-keep|/root/fetch_main|1|ca.der" "new-keep|/root/fetch_new|1|ca.der" "rust-keep|$R/rust_client|1|ca.pem" "bun-keep|bun /root/main/bench/fetch/fetch.ts|1|ca.pem" \
              "main-res|/root/fetch_main|2|ca.der" "new-res|/root/fetch_new|2|ca.der" "rust-new|$R/rust_client|0|ca.pem" "go-new|$R/go_client|0|ca.pem" "go-keep|$R/go_client|1|ca.pem"; do
    IFS='|' read name cmd mode ca <<< "$spec"
    v=$(taskset -c 0 $cmd 18443 /1m 100 1048576 $mode $R/$ca | p50)
    line="$line  $name=$v"
  done
  echo "$line"
done
kill $SERVER
echo AB-DONE
