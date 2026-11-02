# diag2c.sh : 2-vCPU hello diagnosis: topology, client/server CPU use, Vif after vs before vs single-change reverts (interleaved)
R=/root/results; mkdir -p $R
bash /root/meta.sh $R/meta-2c.txt
V=("vif|AXON_THREADS=1 /root/bin/vif-http" "before|AXON_THREADS=1 /root/bin-before/vif-http")
for v in pollfirst accept1 nocore noalign nollvm; do if cmp -s /root/bin/vif-http /root/bin-$v/vif-http; then echo "$v: binary identical to after, not run"; else V+=("$v|AXON_THREADS=1 /root/bin-$v/vif-http"); fi; done | tee $R/hello-2c-skipped.txt
for v in pollfirst accept1 nocore noalign nollvm; do cmp -s /root/bin/vif-http /root/bin-$v/vif-http || V+=("$v|AXON_THREADS=1 /root/bin-$v/vif-http"); done
V+=("epoll|AXON_THREADS=1 AXON_HTTP_URING=0 /root/bin/vif-http" "httpz|/root/zig-baseline/bin/http_httpz" "httpz-1+1|HTTPZ_WORKERS=1 HTTPZ_POOL=1 /root/zig-baseline/bin/http_httpz")
date; python3 /root/hab2.py 13 / $R/hello-2c-variants.json "${V[@]}" > $R/hello-2c-variants.txt 2>&1; date
grep '^==' $R/hello-2c-variants.txt
