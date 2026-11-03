set -e
mkdir -p /root/bin-main /root/bin-branch /root/rust
cd /root/main && for p in stencil; do ./neo build examples/$p.neo -o /root/bin-main/neo-$p --no-cache > /root/bin-main/$p-report.json; done
cd /root/branch && for p in stencil; do ./neo build examples/$p.neo -o /root/bin-branch/neo-$p --no-cache > /root/bin-branch/$p-report.json; done
cd /root/branch/bench/rust && . /root/.cargo/env && cargo build --release --bin stencil 2>&1 | tail -2 && cp target/release/stencil /root/rust/
cd /root/branch/bench/zig && zig build -Doptimize=ReleaseFast -Dcpu=baseline --prefix /root/zig-baseline 2>&1 | tail -3
zig build -Doptimize=ReleaseFast --prefix /root/zig-native 2>&1 | tail -3
set +e
for a in "1 1" "7 3" "1000 5" "1000001 2"; do echo "stencil $a: branch=$(NEO_THREADS=4 /root/bin-branch/neo-stencil $a) main=$(NEO_THREADS=4 /root/bin-main/neo-stencil $a) zig=$(ZIG_THREADS=4 /root/zig-baseline/bin/stencil $a) rust=$(RAYON_NUM_THREADS=4 /root/rust/stencil $a)"; done
{ echo "## machine"; lscpu | grep -E "Model name|^CPU\(s\)|Thread|Core|Socket|NUMA node\(s\)|L2|L3"; lscpu -e; uname -r; grep PRETTY /etc/os-release; echo "THP enabled: $(cat /sys/kernel/mm/transparent_hugepage/enabled)"; echo "THP defrag: $(cat /sys/kernel/mm/transparent_hugepage/defrag)"; echo "## toolchains"; clang --version | head -1; zig version; . /root/.cargo/env; rustc --version; cargo --version; python3 --version; echo "## sources"; sha256sum /root/main.tgz /root/commit.tgz; echo "## binaries (sha256)"; cd /root; sha256sum bin-main/neo-stencil bin-branch/neo-stencil rust/stencil zig-baseline/bin/stencil zig-native/bin/stencil; } > /root/meta-4c.txt 2>&1
cat /root/meta-4c.txt
echo "## 4-worker stencil"
NEO_AFTER=/root/bin-branch NEO_BEFORE=/root/bin-main ZIG=/root/zig-baseline/bin ZIG_NATIVE=/root/zig-native/bin RUST=/root/rust \
  python3 /root/branch/bench/compute-margins/run.py /root/final-4c.json 15 4 madvise,never stencil:1000000:20 stencil:50000000:20
echo FOUR-DONE
