set -e
rm -rf /root/w-fin2 && cp -r /root/base /root/w-fin2 && tar xzf /root/fin2.tgz -C /root/w-fin2 2>/dev/null
mkdir -p /root/bin-after2 && cd /root/w-fin2
for p in examples/stencil.neo examples/sieve.neo examples/mandel.neo examples/nbody.neo examples/library_bench.neo bench/core/orders_json.neo examples/http.neo bench/compute-margins/strided_flip.neo bench/compute-margins/strided_random.neo; do
  b=$(basename $p .neo); ./neo build $p -o /root/bin-after2/neo-$b --no-cache > /root/bin-after2/$b-report.json; done
cd /root/w-fin && ./neo build examples/http.neo -o /root/bin-after/neo-http --no-cache > /dev/null
set +e
echo "## identical to the measured 'after' binaries?"
for b in stencil sieve mandel nbody library_bench orders_json http strided_flip strided_random; do
  if cmp -s /root/bin-after/neo-$b /root/bin-after2/neo-$b; then echo "$b identical"; else echo "$b DIFFERS"; fi; done
for a in "2" "1000" "99991" "100000000"; do echo "sieve $a: after2=$(/root/bin-after2/neo-sieve $a) before=$(/root/bin-base/neo-sieve $a)"; done
echo "strided: $(/root/bin-after2/neo-strided_flip 1000 7 3) $(/root/bin-after2/neo-strided_random 1000 7 3)"
mkdir -p /root/sieve-only && cp /root/bin-after2/neo-sieve /root/sieve-only/neo-sieve
echo "## sieve rows"
NEO_AFTER=/root/sieve-only NEO_BEFORE=/root/bin-base ZIG=/root/zig-baseline/bin ZIG_NATIVE=/root/zig-native/bin RUST=/root/rust \
  python3 /root/w-fin2/bench/compute-margins/run.py /root/final-2c-sieve.json 9 1,2 madvise,never sieve:100000000
echo "## sieve isolation (ab.py, w=1)"
for thp in madvise never; do echo $thp > /sys/kernel/mm/transparent_hugepage/enabled; echo "# THP $thp"
  python3 /root/ab.py 9 0 1 "final=/root/bin-after2/neo-sieve 100000000" "bytes=/root/bin-after/neo-sieve 100000000" "uc64=/root/bin-uc64/neo-sieve 100000000" "u=/root/bin-u/neo-sieve 100000000" "c16=/root/bin-c16/neo-sieve 100000000" "before=/root/bin-base/neo-sieve 100000000"
done
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
echo "## strided downside (THP madvise, 64e6 flags, 3 rounds)"
for s in 64 256; do for p in strided_flip strided_random; do echo "# $p step $s"
  python3 /root/ab.py 7 0 1 "after=/root/bin-after2/neo-$p 64000000 $s 3" "before=/root/bin-base/neo-$p 64000000 $s 3"; done; done
echo FINAL2-DONE
