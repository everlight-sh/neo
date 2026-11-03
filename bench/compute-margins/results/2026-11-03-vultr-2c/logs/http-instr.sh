# HTTP example before/after on a 2-vCPU box: user-space instructions retired per request (perf stat
# attached to the one-worker server during a 5 s wrk run) and req/s. Server on CPU 0, wrk on CPU 1
# (its SMT sibling), so req/s is indicative only; instructions per request do not depend on load.
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -q wrk curl linux-tools-common linux-tools-$(uname -r) >/dev/null
mkdir -p /root/base && tar xzf /root/base.tgz -C /root/base 2>/dev/null
cd /root/base && ./neo build examples/http.neo -o /root/http-before --no-cache >/dev/null
cd /root/ci && ./neo build examples/http.neo -o /root/http-after --no-cache >/dev/null
set +e
sha256sum /root/http-before /root/http-after
perf stat -e instructions:u -x, true 2>&1 | tail -2
P=18090
up() { NEO_THREADS=1 taskset -c 0 /root/http-$1 $P >/dev/null 2>&1 & S=$!; for i in $(seq 50); do curl -s -o /dev/null http://127.0.0.1:$P/ && break; sleep 0.1; done; }
for path in / /smooth/1000 /smooth/10000; do
  for v in before after; do up $v; echo "$v $path $(curl -s http://127.0.0.1:$P$path | md5sum)"; kill $S; wait $S 2>/dev/null; done
done
for path in / /smooth/1000 /smooth/10000; do
  for r in 1 2 3 4 5; do
    order="before after"; [ $((r % 2)) = 0 ] && order="after before"
    for v in $order; do
      up $v
      perf stat -e instructions:u -x, -o /tmp/ps.txt -p $S -- sleep 6.5 &
      PS=$!; sleep 0.3
      out=$(taskset -c 1 wrk -t1 -c16 -d5s http://127.0.0.1:$P$path)
      wait $PS; kill $S; wait $S 2>/dev/null
      reqs=$(echo "$out" | sed -n 's/^ *\([0-9]*\) requests in.*/\1/p'); rps=$(echo "$out" | sed -n 's/^Requests\/sec: *//p')
      ins=$(grep instructions /tmp/ps.txt | cut -d, -f1)
      echo "path=$path round=$r variant=$v requests=$reqs req_per_s=$rps instructions_u=$ins per_request=$(python3 -c "print(round($ins/$reqs) if '$ins'.isdigit() and $reqs else 'na')")"
    done
  done
done
echo HTTP-DONE
