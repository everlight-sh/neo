set -x
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q clang lld python3 binutils git unzip time jq curl xz-utils
apt-get install -y -q linux-tools-common linux-tools-$(uname -r) || true
cd /root
curl -fsSLO https://ziglang.org/download/0.17.0/zig-x86_64-linux-0.17.0.tar.xz
sha256sum zig-x86_64-linux-0.17.0.tar.xz
tar xf zig-x86_64-linux-0.17.0.tar.xz && ln -sfn /root/zig-x86_64-linux-0.17.0/zig /usr/local/bin/zig
zig version
curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal
. /root/.cargo/env; rustc --version
mkdir -p /root/main /root/branch && tar xzf /root/main.tgz -C /root/main && tar xzf /root/commit.tgz -C /root/branch
echo SETUP-DONE
