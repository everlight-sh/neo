# Container SSR comparison

The builder (`build.py`), load driver (`compare.py`) and syscall profiler
(`profile_http.py`) described below were Python. They were removed with the
rest of the repository's Python and are still in the `v0.2.3` tag; run them
from a checkout of that tag. This directory keeps the Dockerfiles and server
sources they used.

Five ARM64 Linux runtime images render the same document from request props:

- Axon: the optimized `examples/jsx-ssr/page.tsx` translator output, static
  executable in `scratch`, with no libc imports.
- Rust: direct HTML generation with Hyper/Tokio, statically linked with musl,
  in `scratch`. Rust's musl is part of that executable, not Axon's runtime.
- Rust glibc: the same Rust source with its dynamic loader and shared libraries
  copied into `scratch`, to separate library/allocator behavior from language
  and image-size effects.
- Bun direct: direct HTML generation without React packages.
- Bun React: the same TSX source rendered with `renderToStaticMarkup`.

Both Bun images use `oven/bun:1.3.13-alpine`; React/react-dom are 19.2.8.
The Rust Cargo lock pins library versions. Runtime images contain no compiler
or benchmark tools. The build manifest records exact image IDs and base digest.

## Build locally

The existing ARM64 Linux tools container must mount the repository at `/axon`
and contain Python (for the `v0.2.3` builder), Clang, Bun, Rust, `readelf`, `musl-tools`, and the
`aarch64-unknown-linux-musl` Rust target. With the workspace benchmark VM:

```sh
colima start --profile axon-bench --activate=false
docker --context colima-axon-bench start axon-kernel-bench-tools
docker --context colima-axon-bench exec axon-kernel-bench-tools sh -c 'apt-get update -qq && apt-get install -y --no-install-recommends musl-tools && rustup target add aarch64-unknown-linux-musl'
```

Run from the repository root. The builder compiles Axon from TSX and Rust
with release/LTO settings, audits the static executables, builds all five
images, and records filesystem payload and compressed archive sizes under
`.kernel-build/docker-ssr/`. The image-size archive is a gzip-compressed
`docker save`, not a measured registry download. Uncompressed payload sums
regular files from an exported fresh root filesystem; it excludes tar padding,
metadata, symlink storage and Docker-injected resolver/host files.

## Run

The driver uses the Docker Engine API through its Unix socket. The load and
sampling container needs that socket and the repository mount; the five
application containers do not receive either mount.

```sh
docker --context colima-axon-bench network create axon-ssr-comparison
docker --context colima-axon-bench run --name axon-docker-ssr-run \
  --cpuset-cpus 4-7 --memory 1g --network axon-ssr-comparison \
  --mount type=bind,src="$PWD",dst=/axon \
  --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  -e BENCH_NETWORK=axon-ssr-comparison \
  axon-kernel-bench:20261023 COMMAND
```

where COMMAND runs `bench/docker/compare.py` from the `v0.2.3` checkout
mounted at `/axon`.

The VM needs eight CPUs. Servers get CPUs 0 or 0–3, a matching one/four-CPU
quota, 1 GiB RAM and no swap. Each runs as numeric UID/GID 65532, with a
read-only root, no capabilities and no-new-privileges. Traffic stays on a
Docker bridge inside Linux and never passes through macOS port forwarding.

Axon uses one/four worker processes, Rust one process with one/four rendering
threads, and Bun one process or a supervisor plus four serving processes with
port reuse. CPU/memory accounting covers the entire server container. Docker
working set is cgroup usage minus inactive file cache, not RSS or PSS.
Sampling covers measured loads after warm-up; startup/warm-up memory spikes
are excluded from the table peaks.
Use `--memory-mib 512` for the tighter memory-budget experiment. The initial
512 MiB preflight OOM-killed four Bun/React workers; that failure is preserved
separately, and the main comparison gives every server the same 1 GiB limit.

For each image and CPU budget, the test compares all 1,000 valid counts with
actual React output, plus error routes, queries, escaping, UTF-8, 100 concurrent
requests and 129 pipelined responses. Timing uses five ten-second wrk runs
after three seconds of warm-up, 64 connections, four load threads, no
pipelining. The count changes text/conditionals; it does not grow the tree.
Five fresh-container starts measure start-API-call to first valid response
with the image already cached, excluding creation/build/pull time. Multicore
startup measures the first ready worker, not the entire worker pool.

The report is `RESULTS-docker-ssr-linux-2026-10-23.md`; raw commands,
reference output, image/build manifests, startup inspections, cgroup samples,
per-run logs and invalid outcomes are under `bench/http/results/*-docker-ssr/`.
Short local VM results are not production capacity or energy measurements.

The driver removes each application container after testing. Remove the
stopped load container and task network when finished; the runtime images and
result files can remain for inspection and reruns. Always use the explicit
Docker context so the user's normal context stays unchanged.

## Linux HTTP backend comparison

Linux containers serve with an Axon epoll loop with persistent registrations:
Docker's default seccomp profile blocks io_uring, which x86-64 Linux otherwise
uses by default. Set `NEO_HTTP_POLL=1` to exercise the previous ppoll loop in
the same executable.
Neither backend imports libc or a foreign event-loop library.

Before rebuilding, preserve the previous `images.json`, Axon executable and
image (tag its immutable ID so Docker does not prune it). The driver accepts
`--include-poll-baseline /axon/path/to/old/images.json` to rerun that image as
`Axon poll baseline`. `--include-current-poll` also tests the current executable
with the fallback selected, which isolates backend choice from binary changes.
Use `--report /axon/RESULTS-new-name.md` to preserve earlier reports. Optional
`--workers 1` and `--servers 'Axon JSX' 'Rust Hyper'` support focused pilots.
Retain pilots separately from the full five-run comparison.

`profile_http.py` records intrusive syscall counts in a separate tool container
with the host PID namespace, SYS_PTRACE and ptrace permitted by its seccomp
policy. Application containers retain their ordinary restrictions. It expects
the `axon-http-profile` network and `strace` in the tool container, and accepts
`--stage NAME --axon-image TAG`. Tracing changes timing and scheduling; its
rates and syscall durations must not be used as untraced performance results.

Measured results: [full report](../../RESULTS-docker-ssr-linux-2026-10-23.md).
The later [epoll comparison](../../RESULTS-http-epoll-docker-linux-2026-10-24.md)
reruns both Rust builds and Bun variants alongside the preserved poll image
and the current executable's poll fallback. It records the one-CPU improvement,
lower four-CPU throughput than the fallback, and the near-saturated load client.
The initial low-memory failure is documented in the
[512-MiB preflight record](../../PREFLIGHT-docker-512MiB-2026-10-23.md).
