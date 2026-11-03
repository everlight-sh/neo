#!/bin/bash
# ab.sh PATH SIZE COUNT: interleaved rounds of main's fetch_neo against the new
# tree's, with Bun, Rust and Go in the same rounds, over HTTPS and plain HTTP.
# Prints each client's per-request p50 (us) from its own timings.
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
P=$1; SIZE=$2; COUNT=$3
R=${R:-$(ls -d /root/main/bench/fetch/results/*/ | tail -1)}; R=${R%/}
[ -x /root/fetch_new ] || { cd /root/new && ./neo build bench/fetch/fetch.neo -o /root/fetch_new --no-cache >/dev/null || exit 1; }
[ -x /root/fetch_main ] || cp $R/fetch_neo /root/fetch_main
taskset -c 0 $R/go_server 18080 18443 $R/leaf.pem $R/leaf.key >/dev/null 2>&1 & SERVER=$!
for i in $(seq 1 100); do (exec 3<>/dev/tcp/127.0.0.1/18443) 2>/dev/null && break; sleep 0.1; done
p50() { python3 -c "import sys;l=sys.stdin.read().splitlines();v=sorted(int(x) for x in l[1].split());assert int(l[0].split()[1])==len(v),l[0];print(f'{v[len(v)//2-1]/1000:.1f}')"; }
B="bun /root/main/bench/fetch/fetch.ts"
for round in $(seq 1 ${ROUNDS:-5}); do
  line="round $round"
  for spec in "s-main-new|/root/fetch_main|0|18443|ca.der" "s-new-new|/root/fetch_new|0|18443|ca.der" "s-bun-new|$B|0|18443|ca.pem" "s-rust-new|$R/rust_client|0|18443|ca.pem" "s-go-new|$R/go_client|0|18443|ca.pem" \
              "s-main-keep|/root/fetch_main|1|18443|ca.der" "s-new-keep|/root/fetch_new|1|18443|ca.der" "s-bun-keep|$B|1|18443|ca.pem" "s-rust-keep|$R/rust_client|1|18443|ca.pem" "s-go-keep|$R/go_client|1|18443|ca.pem" \
              "s-main-res|/root/fetch_main|2|18443|ca.der" "s-new-res|/root/fetch_new|2|18443|ca.der" \
              "p-main-new|/root/fetch_main|0|18080|" "p-new-new|/root/fetch_new|0|18080|" "p-bun-new|$B|0|18080|" "p-rust-new|$R/rust_client|0|18080|" "p-go-new|$R/go_client|0|18080|" \
              "p-main-keep|/root/fetch_main|1|18080|" "p-new-keep|/root/fetch_new|1|18080|" "p-bun-keep|$B|1|18080|" "p-rust-keep|$R/rust_client|1|18080|" "p-go-keep|$R/go_client|1|18080|"; do
    IFS='|' read name cmd mode port ca <<< "$spec"
    v=$(taskset -c 0 $cmd $port $P $COUNT $SIZE $mode ${ca:+$R/$ca} | p50)
    line="$line  $name=$v"
  done
  echo "$line"
done
kill $SERVER
echo AB-DONE
