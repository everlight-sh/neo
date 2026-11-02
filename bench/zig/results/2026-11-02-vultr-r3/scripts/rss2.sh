# rss2.sh : peak RSS of the VifDB-like allocation pattern, before/after trees (GNU time %M)
R=/root/results; mkdir -p /root/rss
(cd /root/w-before && ./axon build /root/rss/alloc_pattern.ax -o /root/rss/ap-before --no-cache >/dev/null) && (cd /root/axon-after && ./axon build /root/rss/alloc_pattern.ax -o /root/rss/ap-after --no-cache >/dev/null) || exit 1
{ cd /root/rss; for args in '20000 40 0' '20000 40 10000000' '2000 400 0' '50000 24 20000000'; do for t in 1 2; do for b in ap-before ap-after; do
  echo "$b threads=$t args=$args: $(AXON_THREADS=$t timeout 120 /usr/bin/time -f 'maxrss_kib %M minflt %R wall %e' ./$b $args 2>&1 | tr '\n' ' ')"
  done; done; done; } > $R/rss-alloc-pattern.log 2>&1; cat $R/rss-alloc-pattern.log
