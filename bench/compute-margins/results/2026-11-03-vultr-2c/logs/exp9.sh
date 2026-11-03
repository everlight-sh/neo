set -e
rm -rf /root/w-nopop2 && cp -r /root/w-fin /root/w-nopop2 && cp /root/base/runtime/core.neo /root/w-nopop2/runtime/core.neo
mkdir -p /root/bin-np && cd /root/w-nopop2 && ./neo build examples/library_bench.neo -o /root/bin-np/neo-library_bench --no-cache >/dev/null && ./neo build examples/sieve.neo -o /root/bin-np/neo-sieve --no-cache >/dev/null
set +e
echo "np sieve $(/root/bin-np/neo-sieve 100000000) json $(/root/bin-np/neo-library_bench 0 1000 | md5sum)"
for thp in madvise never; do echo $thp > /sys/kernel/mm/transparent_hugepage/enabled; echo "## THP $thp"
  echo "# sieve 1e8 w=1 (uc64 = before the bool-byte change)"; python3 /root/ab.py 9 0 1 "after=/root/bin-after/neo-sieve 100000000" "uc64=/root/bin-uc64/neo-sieve 100000000" "nopop=/root/bin-np/neo-sieve 100000000" "before=/root/bin-base/neo-sieve 100000000"
  echo "# json doc x1M w=1"; python3 /root/ab.py 15 0 1 "after=/root/bin-after/neo-library_bench 0 1000000" "nopop=/root/bin-np/neo-library_bench 0 1000000" "before=/root/bin-base/neo-library_bench 0 1000000"
done
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
for b in after np base; do echo "$b json rss/faults: $( /usr/bin/time -f '%M KiB %R minflt %e s' taskset -c 0 env NEO_THREADS=1 /root/bin-$b/neo-library_bench 0 1000000 2>&1 >/dev/null)"; done
echo EXP9-DONE
