# fma_align.sh : dev tree with FMA contraction / loop alignment overrides (clang flags only), measured against dev
set -e
export PATH=/root/.bun/bin:/usr/local/go/bin:$PATH
cd /root/dev2
for v in "fma:-ffp-contract=fast" "al32:-falign-loops=32" "al64:-falign-loops=64"; do n=${v%%:*}; f=${v#*:}; NEO_CLANG_FLAGS="$f" sh /root/build.sh /root/dev2 /root/bin-$n >/dev/null; done
for n in fma al32 al64; do for p in mandel stencil nbody; do cmp -s /root/bin-dev1/neo-$p /root/bin-$n/neo-$p && echo "$n $p identical to dev" || true; done; done
/usr/bin/objdump -d /root/bin-fma/neo-mandel | grep -c "fmadd\|fmsub\|fmla\|fmls" || true
/usr/bin/objdump -d /root/bin-fma/neo-nbody | grep -c "fmadd\|fmsub\|fmla\|fmls" || true
/usr/bin/objdump -d /root/bin-dev1/neo-mandel | grep -c "fmadd\|fmsub\|fmla\|fmls" || true
/usr/bin/objdump -d /root/comp/go/mandel_bin | grep -c "FMADD\|FMSUB\|fmadd\|fmsub\|fmla\|fmls" || true
python3 bench/core/compute_compare.py /root/results/fma-align.json 7 --variant dev=/root/bin-dev1 --variant fma=/root/bin-fma --variant al32=/root/bin-al32 --variant al64=/root/bin-al64 --rust /root/comp/rust --go /root/comp/go --workers 1
