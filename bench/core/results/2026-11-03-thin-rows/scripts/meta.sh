#!/bin/bash
# meta.sh OUT : machine, toolchains, source and binary hashes for this round
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
{
echo "## machine"; lscpu | grep -E "^CPU\(s\)|Model name|Thread|Core\(s\)|Flags"; uname -r; grep PRETTY /etc/os-release
echo "THP enabled: $(cat /sys/kernel/mm/transparent_hugepage/enabled)"; echo "THP defrag: $(cat /sys/kernel/mm/transparent_hugepage/defrag)"
echo "## toolchains"; clang --version | head -1; go version; rustc --version; bun --version; ls /root/zig*/zig >/dev/null 2>&1 && /root/zig-*/zig version 2>/dev/null | head -1; python3 --version
echo "## sources"; (cd /root/main && git log --oneline -1 2>/dev/null); sha256sum /root/*.tgz 2>/dev/null | sed 's#/root/##'
echo "## binaries (sha256)"; cd /root && sha256sum bin-main/* bin-final/* fetch_main fetch_new 2>/dev/null
} > $1
