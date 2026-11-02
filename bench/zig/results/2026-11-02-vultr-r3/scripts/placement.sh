# placement.sh : sieve under provoked placements: N bytes of NOPs at main's entry (executed once) shift
# main's loops; each IR compiled with LLVM's default 16-byte loop alignment and with -falign-loops=32.
set -e
mkdir -p /root/place; rm -f /root/place/*; cd /root/axon-after
./axon build examples/sieve.ax -o /tmp/sv --no-cache --report > /tmp/r.json
IR=$(python3 -c "import json;print(json.load(open('/tmp/r.json'))['ir'])")
for n in 0 8 16 24 32 40 48 56; do
  python3 - "$IR" $n /tmp/pad.ll <<'PY'
import sys, re
ir, n, out = open(sys.argv[1]).read().split('\n'), int(sys.argv[2]), sys.argv[3]
i = next(k for k, l in enumerate(ir) if l.startswith('define') and '@main(' in l)
j = next(k for k in range(i + 1, len(ir)) if re.match(r'^[A-Za-z0-9_.]+:', ir[k]))
if n: ir.insert(j + 1, f'  call void asm sideeffect ".nops {n}", ""()')
open(out, 'w').write('\n'.join(ir))
PY
  for a in 16 32; do
    flag=""; [ $a = 32 ] && flag="-falign-loops=32"
    clang --target=x86_64-unknown-linux-gnu -O3 -ffunction-sections -fdata-sections /tmp/pad.ll -nostdlib -static -Wl,-e,_start -Wl,--no-undefined -Wl,--gc-sections $flag -o /root/place/s-n$n-a$a 2>/dev/null
    echo "n$n a$a: mark loop at $(objdump -d --no-show-raw-insn /root/place/s-n$n-a$a | awk '/<main>:/,/^$/' | grep -B2 'movb   $0x0,(%r' | head -1 | awk '{print $1}')"
  done
done
cd /root
V=(); for f in /root/place/s-*; do V+=("$(basename $f)=$f 100000000"); done
python3 ab.py 7 0 1 "${V[@]}" "zig=/root/zig-baseline/bin/sieve 100000000" > /root/place-w1.txt
python3 ab.py 7 0-1 2 "${V[@]}" "zig=/root/zig-baseline/bin/sieve 100000000" > /root/place-w2.txt
echo "== 1 worker"; sort -k3 -n /root/place-w1.txt; echo "== 2 workers"; sort -k3 -n /root/place-w2.txt
