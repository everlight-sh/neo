# build_x86.sh : x86-64 variants for the codegen check + Rust/Go. /root/dev is the experiment copy with
# NEO_SUM_WIDTH / NEO_SUM_LANES / NEO_ARRAY_WIDTH hooks; /root/final is the committed tree.
set -e
export PATH=/root/.cargo/bin:/usr/local/go/bin:$PATH
sh /root/build.sh /root/main /root/bin-main
sh /root/build.sh /root/dev /root/bin-dev
sh /root/build.sh /root/final /root/bin-final
for p in mandel stencil nbody sieve; do cmp /root/bin-final/neo-$p /root/bin-dev/neo-$p && echo "$p final == dev (hooks unset)"; done
NEO_SUM_WIDTH=2 sh /root/build.sh /root/dev /root/bin-w2
NEO_SUM_LANES=4 NEO_SUM_WIDTH=2 sh /root/build.sh /root/dev /root/bin-k4w2
NEO_ARRAY_WIDTH=2 sh /root/build.sh /root/dev /root/bin-aw2
cd /root/main/bench/rust && cargo build --release 2>&1 | tail -3
cd /root/main/bench/go && for p in mandel stencil nbody; do GOTOOLCHAIN=local GOWORK=off go build -o ${p}_bin ./$p; done
mkdir -p /root/comp/rust /root/comp/go
cp /root/main/bench/rust/target/release/mandel /root/main/bench/rust/target/release/stencil /root/main/bench/rust/target/release/nbody /root/comp/rust/
cp /root/main/bench/go/*_bin /root/comp/go/
sha256sum /root/comp/rust/* /root/comp/go/* /root/bin-*/* > /root/sha256.txt; cat /root/sha256.txt
echo BUILD-OK
