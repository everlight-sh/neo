# Docker SSR: Axon, Rust, Bun direct and Bun React

Measured 2026-10-24T08:29:23.910929+00:00 on ARM64 Linux in an 8-vCPU, 6-GiB Colima VM on Apple M1 Pro. Docker Engine 28.4.0. Runtime images are linux/arm64; no CPU emulation.

Every server renders the same 518-byte /page/3 HTML body on every request, without caching. Axon compiles the shared TSX subset to native functions. Rust uses direct String rendering with Hyper/Tokio. Two Rust builds use identical source: static musl and dynamic glibc. Bun direct uses string rendering; Bun React executes the same TSX through renderToStaticMarkup. Both Bun variants share their route/server implementation. This compares complete stacks, not language speed alone.

Axon and static Rust use scratch images containing only the executable; Rust statically includes musl, while Axon has no libc imports. The glibc Rust image also starts from scratch but copies the executable and its required loader/shared libraries. Bun uses the pinned official 1.3.13-alpine base; React/react-dom are 19.2.8. Image IDs, base digest, binary/source hashes, tool versions and build logs are retained.

Servers run as UID/GID 65532, read-only root filesystem, all capabilities dropped, no-new-privileges, 1024 MiB RAM with swap disabled. The one-worker test uses CPU 0 and a one-CPU quota; four-worker tests use CPUs 0–3 and a four-CPU quota. The load container and sampler use CPUs 4–7. Traffic crosses the same Docker bridge entirely inside Linux; there are no host port mappings or macOS forwarding paths.

Axon uses worker processes (1 or 4 total). Rust uses one process with 1 or 4 Tokio worker threads plus the main thread. Bun uses one serving process, or a supervisor plus four serving processes sharing a port with SO_REUSEPORT. Container CPU and memory include all workers, supervisors and threads.

Each server/budget is checked against all 1,000 valid prop values from React, plus routing, escaping/Unicode, 100 concurrent requests and 129 pipelined responses. Performance is wrk -t4 -c64, no pipelining, 5 runs of 5s after 3s warm-up. Server order is shuffled. Latencies are closed-loop and can hide coordinated omission.

Memory is sampled during measured loads, after warm-up: container cgroup usage minus inactive file cache (Docker-style working set), not RSS/PSS; it includes charged kernel memory. Startup and warm-up spikes are not included in the table peaks. Raw usage and samples are retained. CPU/request uses cgroup CPU nanoseconds, including user/kernel time for the complete container. Sampled peaks may miss shorter spikes. Quota throttling and client CPU usage are recorded.

## Image size

| Image | Uncompressed file payload MiB | gzip docker-save archive MiB |
|---|---:|---:|
| Axon JSX | 0.0259 | 0.0162 |
| Rust Hyper | 0.7540 | 0.4017 |
| Rust Hyper glibc | 3.2216 | 1.5773 |
| Bun direct | 104.4398 | 43.9074 |
| Bun React | 111.6639 | 45.1731 |
| Axon prior epoll | 0.0250 | 0.0159 |

The gzip column is a locally compressed docker-save archive, including image metadata; it is not measured registry transfer size. Uncompressed payload sums regular files in an exported fresh root filesystem, excluding Docker-injected host/resolver files and .dockerenv. It excludes tar padding and metadata, and is not allocated disk usage. Shared Bun layers are counted for each standalone image. Docker/containerd also reports image content size separately in the raw manifest. Build tools are excluded.

## 1 CPU(s), 1 rendering worker(s)

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Measured-load peak working set MiB | Start→first response ms | Client CPU cores | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 152,598 | 128,768–161,592 | 6.18 | 356 | 7440 | 1.57 | 170.4 | 1.43 | 0 / 0 | True |
| Rust Hyper | 128,705 | 74,076–134,642 | 7.96 | 457 | 2060 | 1.89 | 220.7 | 1.29 | 0 / 0 | True |
| Rust Hyper glibc | 143,148 | 126,914–150,030 | 6.99 | 434 | 3370 | 2.34 | 96.8 | 1.28 | 0 / 0 | True |
| Bun direct | 54,893 | 45,085–62,219 | 17.60 | 980 | 26460 | 14.50 | 104.5 | 0.75 | 0 / 0 | True |
| Bun React | 11,966 | 10,599–33,618 | 58.83 | 3670 | 184390 | 49.68 | 203.8 | 0.37 | 0 / 0 | True |
| Axon prior epoll | 158,487 | 145,967–167,635 | 5.96 | 350 | 6130 | 1.57 | 95.9 | 1.43 | 0 / 0 | True |

## 4 CPU(s), 4 rendering worker(s)

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Measured-load peak working set MiB | Start→first response ms | Client CPU cores | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 450,859 | 326,924–527,193 | 6.76 | 87 | 1220 | 2.11 | 121.3 | 3.22 | 0 / 0 | True |
| Rust Hyper | 79,818 | 43,050–129,971 | 32.03 | 575 | 66320 | 2.81 | 81.7 | 1.48 | 0 / 0 | True |
| Rust Hyper glibc | 231,815 | 167,274–242,938 | 11.72 | 209 | 3500 | 3.94 | 102.4 | 2.11 | 0 / 0 | True |
| Bun direct | 126,211 | 101,003–214,919 | 21.54 | 303 | 25350 | 64.57 | 126.3 | 1.90 | 0 / 0 | True |
| Bun React | 124,164 | 119,069–130,793 | 30.64 | 440 | 8250 | 225.55 | 154.4 | 1.55 | 0 / 0 | True |
| Axon prior epoll | 330,634 | 114,320–387,991 | 9.02 | 106 | 17030 | 2.10 | 108.5 | 2.68 | 0 / 0 | True |

Startup is the median of 5 fresh-container starts with images already cached, measured from the Docker start API call until the first response with verified HTML; container creation, pulls and builds are excluded. Polling, Docker control-plane latency and bridge setup are included. For multicore it measures the first ready worker, not the entire pool.

Results are local VM measurements on a shared physical machine. Inspect run ranges and load-client CPU consumption before interpreting small gaps or multicore limits. No energy or universal language-performance claims follow from this one small SSR page.

Raw artifacts: `bench/http/results/2026-10-24-082923-docker-ssr`.

## Observations

- All 12 server/budget configurations passed output/protocol validation and had zero measured socket or non-success errors.
- Run ranges are broad. Server order is shuffled, but each implementation runs its five measurements consecutively; host drift can affect comparisons. These measurements do not establish a causal speedup over the preserved Axon executable.
- Axon throughput and footprint compare favorably here, but its one-CPU p99 latency (7.44 ms) exceeds Rust/glibc (3.37 ms). Throughput alone does not describe service quality.
- The four-CPU Rust/musl range is unusually low and variable (43k–130k requests/s). Retain the glibc result and the full ranges when comparing stacks; do not generalize that result to Rust as a language.
