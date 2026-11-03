# build.sh [neo-only] : unpack base.tgz (before) and head.tgz (after), build the Neo JSON programs from both,
# and (unless neo-only) the Rust, Go and Zig competitors.
set -e
. /root/.cargo/env
cd /root
for t in base axon; do rm -rf /root/$t; mkdir /root/$t; done
tar xzf base.tgz -C /root/base; tar xzf head.tgz -C /root/axon
build_neo() {
  rm -rf /root/$2; mkdir -p /root/$2; cd /root/$1
  for p in bench/core/document_decoder bench/core/orders_decoder examples/library_bench bench/core/orders_json; do
    ./neo build $p.neo -o /root/$2/$(basename $p) --no-cache --report > /root/$2/$(basename $p).report.json
  done
}
build_neo base before
build_neo axon after
if [ "$1" != neo-only ]; then
  rm -rf /root/rust /root/go-bin /root/zig-baseline /root/zig-native /root/.cache/zig; mkdir -p /root/rust /root/go-bin
  cd /root/axon/bench/rust && rm -rf target && cargo build --release --locked --bin typed_json --bin usability > /root/build-rust.log 2>&1
  cp target/release/typed_json target/release/usability /root/rust/
  export GOWORK=off GOTOOLCHAIN=local CGO_ENABLED=0
  cd /root/axon/bench/core && go build -o /root/go-bin/json json.go
  cd /root/axon/bench/zig && rm -rf zig-out .zig-cache
  zig build -Doptimize=ReleaseFast -Dcpu=baseline --prefix /root/zig-baseline > /root/build-zig.log 2>&1
  zig build -Doptimize=ReleaseFast --prefix /root/zig-native >> /root/build-zig.log 2>&1
fi
ls -la /root/before /root/after /root/rust /root/go-bin /root/zig-baseline/bin /root/zig-native/bin
echo BUILD-OK
