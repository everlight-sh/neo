# Docker SSR: Axon, Rust, Bun direct and Bun React

Measured 2026-10-23T22:10:57.249576+00:00 on ARM64 Linux in an 8-vCPU, 6-GiB Colima VM on Apple M1 Pro. Docker Engine 28.4.0. Runtime images are linux/arm64; no CPU emulation.

Every server renders the same 518-byte /page/3 HTML body on every request, without caching. Axon compiles the shared TSX subset to native functions. Rust uses direct String rendering with Hyper/Tokio. Two Rust builds use identical source: static musl and dynamic glibc. Bun direct uses string rendering; Bun React executes the same TSX through renderToStaticMarkup. Both Bun variants share their route/server implementation. This compares complete stacks, not language speed alone.

Axon and static Rust use scratch images containing only the executable; Rust statically includes musl, while Axon has no libc imports. The glibc Rust image also starts from scratch but copies the executable and its required loader/shared libraries. Bun uses the pinned official 1.3.13-alpine base; React/react-dom are 19.2.8. Image IDs, base digest, binary/source hashes, tool versions and build logs are retained.

Servers run as UID/GID 65532, read-only root filesystem, all capabilities dropped, no-new-privileges, 1024 MiB RAM with swap disabled. The one-worker test uses CPU 0 and a one-CPU quota; four-worker tests use CPUs 0–3 and a four-CPU quota. The load container and sampler use CPUs 4–7. Traffic crosses the same Docker bridge entirely inside Linux; there are no host port mappings or macOS forwarding paths.

Axon uses worker processes (1 or 4 total). Rust uses one process with 1 or 4 Tokio worker threads plus the main thread. Bun uses one serving process, or a supervisor plus four serving processes sharing a port with SO_REUSEPORT. Container CPU and memory include all workers, supervisors and threads.

Each server/budget is checked against all 1,000 valid prop values from React, plus routing, escaping/Unicode, 100 concurrent requests and 129 pipelined responses. Performance is wrk -t4 -c64, no pipelining, 5 runs of 10s after 3s warm-up. Server order is shuffled. Latencies are closed-loop and can hide coordinated omission.

Memory is sampled during measured loads, after warm-up: container cgroup usage minus inactive file cache (Docker-style working set), not RSS/PSS; it includes charged kernel memory. Startup and warm-up spikes are not included in the table peaks. Raw usage and samples are retained. CPU/request uses cgroup CPU nanoseconds, including user/kernel time for the complete container. Sampled peaks may miss shorter spikes. Quota throttling and client CPU usage are recorded.

## Image size

| Image | Uncompressed file payload MiB | gzip docker-save archive MiB |
|---|---:|---:|
| Axon JSX | 0.0250 | 0.0159 |
| Rust Hyper | 0.7540 | 0.4017 |
| Rust Hyper glibc | 3.2216 | 1.5778 |
| Bun direct | 104.4398 | 43.9075 |
| Bun React | 111.6639 | 45.1728 |
| Axon poll baseline | 0.0226 | 0.0147 |
| Axon current poll | 0.0250 | 0.0159 |

The gzip column is a locally compressed docker-save archive, including image metadata; it is not measured registry transfer size. Uncompressed payload sums regular files in an exported fresh root filesystem, excluding Docker-injected host/resolver files and .dockerenv. It excludes tar padding and metadata, and is not allocated disk usage. Shared Bun layers are counted for each standalone image. Docker/containerd also reports image content size separately in the raw manifest. Build tools are excluded.

## 1 CPU(s), 1 rendering worker(s)

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Measured-load peak working set MiB | Start→first response ms | Client CPU cores | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Bun direct | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | failed | False |

## 4 CPU(s), 4 rendering worker(s)

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Measured-load peak working set MiB | Start→first response ms | Client CPU cores | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

Startup is the median of 5 fresh-container starts with images already cached, measured from the Docker start API call until the first response with verified HTML; container creation, pulls and builds are excluded. Polling, Docker control-plane latency and bridge setup are included. For multicore it measures the first ready worker, not the entire pool.

Results are local VM measurements on a shared physical machine. Inspect run ranges and load-client CPU consumption before interpreting small gaps or multicore limits. No energy or universal language-performance claims follow from this one small SSR page.

Raw artifacts: `/axon/bench/http/results/2026-10-23-221057-docker-ssr`.

## HTTP backend comparison

Current Axon uses persistent level-triggered epoll registrations through direct Linux syscalls. The poll baseline is the preserved executable/image from before this change, rerun in this same session with identical resource and load settings. Framing, rendering and the 64-response batching policy are unchanged. Raw image manifests retain both source/binary hashes.

The syscall-count profiles are intrusive strace runs, separate from these untraced measurements. Both backends already use approximately one read and one send per unpipelined request. Registration persistence avoids rebuilding and attaching a wait set for all open sockets on each wait; counts alone do not measure that cost or establish how much of the gain comes from kernel versus user-space dispatch.
