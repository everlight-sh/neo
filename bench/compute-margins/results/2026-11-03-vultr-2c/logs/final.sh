set -e
rm -rf /root/w-fin && cp -r /root/base /root/w-fin && tar xzf /root/fin.tgz -C /root/w-fin 2>/dev/null
mkdir -p /root/bin-after /root/base/bench/compute-margins
cp /root/w-fin/bench/compute-margins/strided_*.neo /root/base/bench/compute-margins/
cd /root/w-fin
for p in examples/stencil.neo examples/sieve.neo examples/mandel.neo examples/nbody.neo examples/library_bench.neo bench/core/orders_json.neo bench/compute-margins/strided_flip.neo bench/compute-margins/strided_random.neo; do
  b=$(basename $p .neo); ./neo build $p -o /root/bin-after/neo-$b --no-cache > /root/bin-after/$b-report.json; done
cd /root/base
for p in examples/library_bench.neo bench/core/orders_json.neo bench/compute-margins/strided_flip.neo bench/compute-margins/strided_random.neo; do
  b=$(basename $p .neo); ./neo build $p -o /root/bin-base/neo-$b --no-cache > /root/bin-base/$b-report.json; done
set +e
echo "## sanity"
for a in "sieve 2" "sieve 1000" "sieve 99991" "stencil 1 1" "stencil 7 3" "stencil 1000 5" "mandel 30 20 50" "nbody 8 2"; do
  set -- $a; p=$1; shift
  echo "$p $*: after=$(/root/bin-after/neo-$p "$@") before=$(/root/bin-base/neo-$p "$@") zig=$(/root/zig-baseline/bin/$p "$@") rust=$(/root/rust/$p "$@")"
done
for a in "strided_flip 1000 7 3" "strided_random 1000 7 3" "strided_flip 70000000 64 1"; do set -- $a; p=$1; shift
  echo "$p $*: after=$(/root/bin-after/neo-$p "$@") before=$(/root/bin-base/neo-$p "$@")"; done
echo "library_bench: after=$(/root/bin-after/neo-library_bench 0 1000 | md5sum) before=$(/root/bin-base/neo-library_bench 0 1000 | md5sum)"
echo "orders_json: after=$(/root/bin-after/neo-orders_json 100 10 | md5sum) before=$(/root/bin-base/neo-orders_json 100 10 | md5sum)"
echo "## compute rows"
NEO_AFTER=/root/bin-after NEO_BEFORE=/root/bin-base ZIG=/root/zig-baseline/bin ZIG_NATIVE=/root/zig-native/bin RUST=/root/rust \
  python3 /root/w-fin/bench/compute-margins/run.py /root/final-2c.json 9 1,2 madvise,never
echo "## json rows (w=1)"
for thp in madvise never; do echo $thp > /sys/kernel/mm/transparent_hugepage/enabled; echo "# THP $thp"
  echo "doc x1M"; python3 /root/ab.py 9 0 1 "after=/root/bin-after/neo-library_bench 0 1000000" "before=/root/bin-base/neo-library_bench 0 1000000"
  echo "orders 1000 x1000"; python3 /root/ab.py 9 0 1 "after=/root/bin-after/neo-orders_json 1000 1000" "before=/root/bin-base/neo-orders_json 1000 1000"
done
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
echo "## strided downside (THP madvise, 64e6 flags, 3 rounds)"
for s in 64 256; do for p in strided_flip strided_random; do echo "# $p step $s"
  python3 /root/ab.py 7 0 1 "after=/root/bin-after/neo-$p 64000000 $s 3" "before=/root/bin-base/neo-$p 64000000 $s 3"; done; done
echo FINAL-DONE
