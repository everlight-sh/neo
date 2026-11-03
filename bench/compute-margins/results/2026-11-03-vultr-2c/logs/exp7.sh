set -e
rm -rf /root/w-cur3 && cp -r /root/base /root/w-cur3 && tar xzf /root/cur3.tgz -C /root/w-cur3 2>/dev/null
cd /root/w-cur3
for v in u uc8 uc16 uc32 uc64; do mkdir -p /root/bin-$v
 t=${v#uc}; [ "$v" = u ] && t=
 for p in examples/sieve.neo bench/compute-margins/strided_flip.neo bench/compute-margins/strided_random.neo; do
  b=$(basename $p .neo)
  if [ -n "$t" ]; then NEO_EXP_CHECK=$t ./neo build $p -o /root/bin-$v/neo-$b --no-cache >/dev/null; else ./neo build $p -o /root/bin-$v/neo-$b --no-cache >/dev/null; fi
 done; done
set +e
for v in u uc8 uc16 uc32 uc64; do echo "$v $(/root/bin-$v/neo-sieve 100000000) $(/root/bin-$v/neo-sieve 1000) $(/root/bin-$v/neo-sieve 2) $(/root/bin-$v/neo-sieve 99991) flip $(/root/bin-$v/neo-strided_flip 1000 7 3) rnd $(/root/bin-$v/neo-strided_random 1000 7 3)"; done
for thp in madvise never; do echo $thp > /sys/kernel/mm/transparent_hugepage/enabled; echo "## THP $thp"
 echo "# sieve 1e8 w=1"; python3 /root/ab.py 9 0 1 "u=/root/bin-u/neo-sieve 100000000" "uc8=/root/bin-uc8/neo-sieve 100000000" "uc16=/root/bin-uc16/neo-sieve 100000000" "uc32=/root/bin-uc32/neo-sieve 100000000" "uc64=/root/bin-uc64/neo-sieve 100000000" "zig=/root/zig-baseline/bin/sieve 100000000"
done
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
for s in 16 64 256; do
 echo "# flip 64e6 step $s x3"; python3 /root/ab.py 5 0 1 "u=/root/bin-u/neo-strided_flip 64000000 $s 3" "uc16=/root/bin-uc16/neo-strided_flip 64000000 $s 3" "uc64=/root/bin-uc64/neo-strided_flip 64000000 $s 3"
 echo "# random 64e6 step $s x3"; python3 /root/ab.py 5 0 1 "u=/root/bin-u/neo-strided_random 64000000 $s 3" "uc16=/root/bin-uc16/neo-strided_random 64000000 $s 3" "uc64=/root/bin-uc64/neo-strided_random 64000000 $s 3"
done
echo EXP7-DONE
