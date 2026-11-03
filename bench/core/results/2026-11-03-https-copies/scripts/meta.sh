#!/bin/bash
# meta.sh OUT : machine, toolchains, source and binary hashes for this round
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
{
echo "## machine"; lscpu | grep -E "^CPU\(s\)|Model name|Thread|Core\(s\)|Flags"; uname -r; grep PRETTY /etc/os-release
echo "## toolchains"; clang --version | head -1; go version; rustc --version; bun --version; python3 --version; openssl version
echo "## sources"; sha256sum /root/*.tgz | sed 's#/root/##'
echo "## binaries (sha256)"; cd /root && sha256sum fetch_main fetch_new
} > $1
