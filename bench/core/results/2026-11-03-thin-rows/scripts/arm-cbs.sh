#!/bin/bash
# ARM: check-before-store in the strided lowering (x86-only today) on Linux AArch64.
set -u
rm -rf /root/new2 && cp -a /root/new /root/new2 && cd /root/new2
python3 - <<'PY'
p='neoc/strided.py'; s=open(p).read()
old="    if gen.triple.startswith('x86_64') and t.elem in (S.BOOL, S.U8, S.I64):"
assert s.count(old)==1
s=s.replace(old,"    if (gen.triple.startswith('x86_64') or (gen.triple.startswith('aarch64') and 'linux' in gen.triple)) and t.elem in (S.BOOL, S.U8, S.I64):")
open(p,'w').write(s)
PY
mkdir -p /root/bin-cbs /root/bin-sd-new /root/bin-sd-cbs
./neo build examples/sieve.neo -o /root/bin-cbs/neo-sieve --no-cache >/dev/null && echo built-sieve
for p in strided_flip strided_random; do
  ./neo build bench/compute-margins/$p.neo -o /root/bin-sd-cbs/$p --no-cache >/dev/null
  (cd /root/new && ./neo build bench/compute-margins/$p.neo -o /root/bin-sd-new/$p --no-cache >/dev/null)
done; ls /root/bin-cbs /root/bin-sd-new /root/bin-sd-cbs
for thp in madvise never; do echo $thp > /sys/kernel/mm/transparent_hugepage/enabled
  echo "## THP $thp: sieve 1e8, 1 worker, 9 interleaved rounds (ms)"
  for r in $(seq 0 9); do for v in new cbs; do b=/root/bin-$v/neo-sieve; [ $v = new ] && b=/root/bin-new/neo-sieve
    s=$(date +%s%N); NEO_THREADS=1 taskset -c 0 $b 100000000 >/tmp/o-$v; e=$(date +%s%N); [ $r -gt 0 ] && echo "$v $(( (e-s)/1000 ))"; done; done | awk '{a[$1]=a[$1]" "$2/1000} END {for (k in a) print k, a[k]}'
  cat /tmp/o-new /tmp/o-cbs
done
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
echo "## strided downside, 64M flags, 3 rounds, THP madvise (ms, 5 interleaved runs)"
for spec in "strided_flip 67108864 64 3" "strided_random 67108864 64 3" "strided_flip 67108864 256 3" "strided_random 67108864 256 3"; do set -- $spec
  for r in 1 2 3 4 5; do for v in new cbs; do s=$(date +%s%N); NEO_THREADS=1 taskset -c 0 /root/bin-sd-$v/$1 $2 $3 $4 >/tmp/sd-$v; e=$(date +%s%N); echo "$v $(( (e-s)/1000 ))"; done; done | awk -v c="$*" '{a[$1]=a[$1]" "$2/1000} END {for (k in a) print c, k, a[k]}'
  cmp -s /tmp/sd-new /tmp/sd-cbs && echo "  outputs agree" || echo "  OUTPUT MISMATCH"
done
echo CBS-DONE
