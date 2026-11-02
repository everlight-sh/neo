# hbuild.sh : unpack the checkout as-is and build every binary of the headline run
set -e
. /root/.cargo/env
cd /root; rm -rf axon bin rust go-bin zig-baseline zig-native /root/.cache/zig; mkdir axon bin rust go-bin; tar xzf head.tgz -C axon
cd /root/axon
for p in http nbody library_bench; do ./axon build examples/$p.ax -o /root/bin/vif-$p --no-cache; done
cd /root/axon/bench/rust && rm -rf target && cargo build --release --locked --bin http_hyper --bin nbody --bin usability > /root/build-rust.log 2>&1
cp target/release/http_hyper target/release/nbody target/release/usability /root/rust/
export GOWORK=off GOTOOLCHAIN=local CGO_ENABLED=0
cd /root/axon/bench/go && go build -o /root/go-bin/http ./http && go build -o /root/go-bin/nbody ./nbody
cd /root/axon/bench/core && go build -o /root/go-bin/json json.go
cd /root/axon/bench/zig && rm -rf zig-out .zig-cache
zig build -Doptimize=ReleaseFast -Dcpu=baseline --prefix /root/zig-baseline > /root/build-zig.log 2>&1
zig build -Doptimize=ReleaseFast --prefix /root/zig-native >> /root/build-zig.log 2>&1
ls -la /root/bin /root/rust /root/go-bin /root/zig-baseline/bin /root/zig-native/bin
echo BUILD-OK
