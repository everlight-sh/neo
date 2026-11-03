# setup.sh : toolchains for the compile-time benchmark on a fresh Ubuntu x86-64 box, as root
# (clang 18 from the distribution, Go 1.25.x, Rust 1.99.1, Zig 0.17.0, Bun 1.3.13 for CI)
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends clang lld llvm python3 build-essential binutils time git curl ca-certificates xz-utils openssl unzip pkg-config >/root/apt.log 2>&1
cd /root
curl -sSfLO https://ziglang.org/download/0.17.0/zig-x86_64-linux-0.17.0.tar.xz
echo "1cbe9df9f27e6b78d14ccbca43b6703a404ef79ef1c463de901d7f088d4e2026  zig-x86_64-linux-0.17.0.tar.xz" | sha256sum -c
rm -rf zig-x86_64-linux-0.17.0 && tar xf zig-x86_64-linux-0.17.0.tar.xz && ln -sf /root/zig-x86_64-linux-0.17.0/zig /usr/local/bin/zig
GO=$(curl -sSf 'https://go.dev/dl/?mode=json&include=all' | python3 -c '
import json, sys
rs = [r for r in json.load(sys.stdin) if r["stable"] and r["version"].startswith("go1.25.")]
r = max(rs, key=lambda r: int(r["version"].split(".")[2]))
f = [f for f in r["files"] if f["os"] == "linux" and f["arch"] == "amd64" and f["kind"] == "archive"][0]
print(f["filename"], f["sha256"])')
set -- $GO; curl -sSfL https://go.dev/dl/$1 -o $1; echo "$2  $1" | sha256sum -c
rm -rf /usr/local/go && tar -C /usr/local -xzf $1 && ln -sf /usr/local/go/bin/go /usr/local/bin/go
curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain 1.99.1 > /root/rustup.log 2>&1
curl -fsSL https://bun.sh/install | bash -s bun-v1.3.13 > /root/bun.log 2>&1 && ln -sf /root/.bun/bin/bun /usr/local/bin/bun
echo SETUP-OK
uname -r; zig version; go version; /root/.cargo/bin/rustc -V; /root/.cargo/bin/cargo -V; bun --version; clang --version | head -1; python3 --version
lscpu | grep -E "Model name|^CPU\(s\)|Thread|Core|L3"; free -m
