set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q clang lld python3 binutils openssl git unzip time curl xz-utils build-essential linux-tools-common linux-tools-$(uname -r) || apt-get install -y -q clang lld python3 binutils openssl git unzip time curl xz-utils build-essential
GOV=$(curl -s 'https://go.dev/dl/?mode=json&include=all' | python3 -c "import json,sys;v=[r['version'] for r in json.load(sys.stdin) if r['version'].startswith('go1.25.') and r['stable']];print(sorted(v,key=lambda s:int(s.split('.')[2]))[-1])")
echo GOV=$GOV
curl -sSL https://go.dev/dl/$GOV.linux-$(dpkg --print-architecture).tar.gz -o /tmp/go.tgz
rm -rf /usr/local/go && tar -C /usr/local -xzf /tmp/go.tgz
ln -sf /usr/local/go/bin/go /usr/local/bin/go; ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt
curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
curl -fsSL https://bun.sh/install | bash -s bun-v1.3.13
ln -sf /root/.bun/bin/bun /usr/local/bin/bun
ln -sf /root/.cargo/bin/cargo /usr/local/bin/cargo; ln -sf /root/.cargo/bin/rustc /usr/local/bin/rustc
clang --version | head -1; go version; rustc --version; cargo --version; bun --version
echo SETUP-DONE
