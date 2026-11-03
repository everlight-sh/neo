set -e
export PATH=/root/.cargo/bin:/usr/local/go/bin:$PATH
sh /root/build.sh /root/main /root/bin-main
cd /root/main/bench/rust && cargo build --release 2>&1 | tail -3
cd /root/main/bench/go && for p in mandel stencil nbody; do GOTOOLCHAIN=local GOWORK=off go build -o ${p}_bin ./$p; done; ls -la
mkdir -p /root/comp/rust /root/comp/go
cp /root/main/bench/rust/target/release/mandel /root/main/bench/rust/target/release/stencil /root/main/bench/rust/target/release/nbody /root/comp/rust/
cp /root/main/bench/go/*_bin /root/comp/go/
sha256sum /root/comp/rust/* /root/comp/go/* /root/bin-main/*
echo BUILD-OK

