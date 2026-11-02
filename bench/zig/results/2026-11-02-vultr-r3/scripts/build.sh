# build.sh full|http : unpack the final tree and the variant overlays; build Vif (after, before, HTTP variants) and Zig
set -e
cd /root; rm -rf axon-after variants w-*; mkdir axon-after; tar xzf after.tgz -C axon-after; tar xzf variants.tgz
for v in before pollfirst accept1 nocore noalign nollvm; do cp -r /root/axon-after /root/w-$v; cp -r /root/variants/$v/. /root/w-$v/; done
ln -sfn /root/axon-after /root/w-after
for v in after before pollfirst accept1 nocore noalign nollvm; do
  out=/root/bin-$v; [ $v = after ] && out=/root/bin; mkdir -p $out
  (cd /root/w-$v && ./axon build examples/http.ax -o $out/vif-http --no-cache --report > $out/http-report.json)
  python3 -c "import json,re,sys;r=json.load(open('$out/http-report.json'));ir=open(r['ir']).read();print('$v',re.search(r'@ax_default_heap_mode = .*',ir)[0], 'nsw-sum-adds', ir.count('add nsw i64'))" || true
done
if [ "$1" = full ]; then
  sh /root/build_vif.sh /root/axon-after /root/bin > /root/build-after.log 2>&1
  sh /root/build_vif.sh /root/w-before /root/bin-before > /root/build-before.log 2>&1
  (cd /root/w-noalign && for p in sieve stencil; do ./axon build examples/$p.ax -o /root/bin-noalign/vif-$p --no-cache; done; ./axon build examples/library_bench.ax -o /root/bin-noalign/vif-library_bench --no-cache; ./axon build bench/core/orders_json.ax -o /root/bin-noalign/vif-orders_json --no-cache)
fi
rm -rf /root/zig-baseline /root/zig-native /root/.cache/zig
cd /root/axon-after/bench/zig && rm -rf zig-out .zig-cache
zig build -Doptimize=ReleaseFast -Dcpu=baseline --prefix /root/zig-baseline > /root/build-zig.log 2>&1
[ "$1" = full ] && zig build -Doptimize=ReleaseFast --prefix /root/zig-native >> /root/build-zig.log 2>&1
sha256sum /root/bin*/vif-http
ls /root/bin* /root/zig-*/bin
echo BUILD-OK
