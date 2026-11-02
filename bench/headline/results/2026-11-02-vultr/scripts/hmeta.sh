# hmeta.sh OUT : machine, versions, build flags and binary hashes
. /root/.cargo/env
{ echo "## machine"; uname -a; grep PRETTY /etc/os-release; lscpu | grep -E "Model name|^CPU\(s\)|Thread|Core|Socket|L1d|L2|L3|MHz"; free -m | head -2
  echo "## topology"; lscpu -e; for c in /sys/devices/system/cpu/cpu[0-9]*; do echo "$(basename $c) thread_siblings_list=$(cat $c/topology/thread_siblings_list)"; done
  echo "## THP"; cat /sys/kernel/mm/transparent_hugepage/enabled /sys/kernel/mm/transparent_hugepage/defrag
  echo "## io_uring_disabled"; cat /proc/sys/kernel/io_uring_disabled 2>/dev/null
  echo "## versions"; zig version; go version; rustc -vV; cargo -V; echo "bun $(bun --version) $(bun --revision 2>/dev/null)"; clang --version | head -1; wrk --version 2>&1 | head -1; python3 --version
  echo "http.zig: $(grep -o 'http.zig#[0-9a-f]*' /root/axon/bench/zig/build.zig.zon)"
  echo "## build"; echo "Vif: ./axon build examples/{http,nbody,library_bench}.ax --no-cache"
  echo "Rust: cargo build --release --locked (profile.release: $(sed -n '/profile.release/,/^$/p' /root/axon/bench/rust/Cargo.toml | tr '\n' ' '))"; echo "RUSTFLAGS='${RUSTFLAGS}'"
  echo "Go: GOWORK=off GOTOOLCHAIN=local CGO_ENABLED=0 go build (bench/go/http, bench/go/nbody, bench/core/json.go)"
  echo "Zig: zig build -Doptimize=ReleaseFast -Dcpu=baseline and zig build -Doptimize=ReleaseFast (native)"
  echo "## sha256"; sha256sum /root/head.tgz /root/bin/vif-* /root/rust/* /root/go-bin/* /root/zig-baseline/bin/http_* /root/zig-baseline/bin/json /root/zig-baseline/bin/nbody /root/zig-native/bin/json /root/zig-native/bin/nbody "$(readlink -f /root/.bun/bin/bun)" /root/axon/bench/bun/server.ts /root/axon/bench/usability/bun.ts /root/axon/bench/core/compute.ts /root/axon/bench/headline/run_headline.py
  echo "## sizes"; ls -l /root/bin /root/rust /root/go-bin /root/zig-baseline/bin /root/zig-native/bin
} > $1 2>&1
