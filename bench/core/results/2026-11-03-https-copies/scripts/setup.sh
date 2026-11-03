#!/bin/bash
# Tools (bench/core/results/2026-11-03-arm64-compute/scripts/setup.sh), then the main and new trees.
bash /root/setup-tools.sh > /root/setup-tools.log 2>&1; tail -6 /root/setup-tools.log
apt-get install -y -q jq strace >/dev/null 2>&1
mkdir -p /root/main /root/new && tar xzf /root/main.tgz -C /root/main && tar xzf /root/new.tgz -C /root/new
lscpu | grep -E "Model name|^CPU\(s\)"; uname -r; cat /sys/kernel/mm/transparent_hugepage/enabled; which perf
echo SETUP-OK
