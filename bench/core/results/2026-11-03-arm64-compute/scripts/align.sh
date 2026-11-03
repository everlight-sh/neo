# align.sh : final tree vs final tree with -falign-loops=32 on AArch64 (cli.py patched in a copy), compute + JSON probes
set -e
export PATH=/root/.bun/bin:/usr/local/go/bin:$PATH
rm -rf /root/final-al && cp -r /root/final /root/final-al
sed -i "s/if target.startswith('x86_64'):cmd += \['-falign-loops=32'\]/if target.startswith(('x86_64','aarch64')):cmd += ['-falign-loops=32']/" /root/final-al/neoc/cli.py
grep -n "falign-loops" /root/final-al/neoc/cli.py
sh /root/build.sh /root/final-al /root/bin-al >/dev/null
for t in final final-al; do o=/root/bin-final; [ $t = final-al ] && o=/root/bin-al; (cd /root/$t && ./neo build examples/library_bench.neo -o $o/neo-library_bench --no-cache >/dev/null && ./neo build bench/core/orders_json.neo -o $o/neo-orders_json --no-cache >/dev/null); done
sha256sum /root/bin-al/* /root/bin-final/* > /root/results/align-sha256.txt
cd /root/final && python3 bench/core/compute_compare.py /root/results/align.json 9 --variant final=/root/bin-final --variant align32=/root/bin-al --cases all --workers 1,4
echo "## JSON doc x1M, CPU 0"; python3 /root/ab.py 15 0 1 "final=/root/bin-final/neo-library_bench 0 1000000" "align32=/root/bin-al/neo-library_bench 0 1000000"
echo "## orders 1000 x1000, CPU 0"; python3 /root/ab.py 15 0 1 "final=/root/bin-final/neo-orders_json 1000 1000" "align32=/root/bin-al/neo-orders_json 1000 1000"
