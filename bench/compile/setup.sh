# setup.sh : toolchains for the compile-time benchmark on a fresh Ubuntu x86-64 box, as root
# (clang 18 from the distribution, Go 1.25.14, Rust 1.99.1, Zig 0.17.0, Bun 1.3.13 for CI)
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends clang lld llvm build-essential binutils time git curl ca-certificates xz-utils openssl unzip pkg-config >/root/apt.log 2>&1
cd /root
curl -sSfLO https://ziglang.org/download/0.17.0/zig-x86_64-linux-0.17.0.tar.xz
echo "1cbe9df9f27e6b78d14ccbca43b6703a404ef79ef1c463de901d7f088d4e2026  zig-x86_64-linux-0.17.0.tar.xz" | sha256sum -c
rm -rf zig-x86_64-linux-0.17.0 && tar xf zig-x86_64-linux-0.17.0.tar.xz && ln -sf /root/zig-x86_64-linux-0.17.0/zig /usr/local/bin/zig
curl -sSfLO https://go.dev/dl/go1.25.14.linux-amd64.tar.gz
echo "a21ae5633a269bcd7e90cf767e48225633795e99d831742cbf3397064fee7712  go1.25.14.linux-amd64.tar.gz" | sha256sum -c
rm -rf /usr/local/go && tar -C /usr/local -xzf go1.25.14.linux-amd64.tar.gz && ln -sf /usr/local/go/bin/go /usr/local/bin/go
curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain 1.99.1 > /root/rustup.log 2>&1
curl -fsSL https://bun.sh/install | bash -s bun-v1.3.13 > /root/bun.log 2>&1 && ln -sf /root/.bun/bin/bun /usr/local/bin/bun
echo SETUP-OK
uname -r; zig version; go version; /root/.cargo/bin/rustc -V; /root/.cargo/bin/cargo -V; bun --version; clang --version | head -1
lscpu | grep -E "Model name|^CPU\(s\)|Thread|Core|L3"; free -m
