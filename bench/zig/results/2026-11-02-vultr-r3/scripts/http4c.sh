# http4c.sh : HTTP rows on the 4-vCPU box: server on CPU 0 (its SMT sibling left idle), wrk -t2 -c64 on the other core
R=/root/results; mkdir -p $R
bash /root/meta.sh $R/meta-4c.txt
SIB=$(cat /sys/devices/system/cpu/cpu0/topology/thread_siblings_list)
CLIENT=$(python3 -c "
import sys
def parse(s): return {int(x) for part in s.split(',') for x in (range(int(part.split('-')[0]), int(part.split('-')[-1]) + 1))}
sib = parse('$SIB'); allc = parse(open('/sys/devices/system/cpu/online').read().strip())
print(','.join(map(str, sorted(allc - sib))))")
export SERVER_CPUS=0 CLIENT_CPUS=$CLIENT WRK_THREADS=2
echo "server CPU 0 (siblings $SIB, sibling idle), client CPUs $CLIENT, wrk -t2 -c64" | tee $R/setup-4c.txt
echo "== headers"; date
{ for srv in "Vif|env AXON_THREADS=1 /root/bin/vif-http" "Zig std.http|/root/zig-baseline/bin/http_std" "Zig http.zig|/root/zig-baseline/bin/http_httpz"; do
    name=${srv%%|*}; cmd=${srv#*|}; ( $cmd 8999 >/dev/null 2>&1 & ); sleep 0.5
    for path in / /page/50 /smooth/1000; do echo "$name GET $path: $(python3 /root/hdr.py 8999 $path)"; done
    pkill -f " 8999\$" || true; sleep 0.5; done; } > $R/headers.txt 2>&1; cat $R/headers.txt
echo "== hello variants"; date
python3 /root/hab2.py 11 / $R/hello-4c-variants.json "vif|AXON_THREADS=1 /root/bin/vif-http" "before|AXON_THREADS=1 /root/bin-before/vif-http" \
  "pollfirst|AXON_THREADS=1 /root/bin-pollfirst/vif-http" "accept1|AXON_THREADS=1 /root/bin-accept1/vif-http" "nocore|AXON_THREADS=1 /root/bin-nocore/vif-http" \
  "epoll|AXON_THREADS=1 AXON_HTTP_URING=0 /root/bin/vif-http" "httpz|/root/zig-baseline/bin/http_httpz" > $R/hello-4c-variants.txt 2>&1
grep '^==' $R/hello-4c-variants.txt
echo "== run_http all rows"; date
cd /root/axon-after/bench/zig && BIN=/root/bin BIN_BEFORE=/root/bin-before python3 run_http.py $R/http-4c.json 11 > $R/http-4c.txt 2>&1; cat $R/http-4c.txt
date; echo ALL-DONE
