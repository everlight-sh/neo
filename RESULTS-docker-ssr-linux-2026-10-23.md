# Docker SSR: Axon, Rust, Bun direct and Bun React

Measured 2026-10-23T21:37:17.855456+00:00 on ARM64 Linux in an 8-vCPU, 6-GiB Colima VM on Apple M1 Pro. Docker Engine 28.4.0. Runtime images are linux/arm64; no CPU emulation.

Every server renders the same 518-byte /page/3 HTML body on every request, without caching. Axon compiles the shared TSX subset to native functions. Rust uses direct String rendering with Hyper/Tokio. Two Rust builds use identical source: static musl and dynamic glibc. Bun direct uses string rendering; Bun React executes the same TSX through renderToStaticMarkup. Both Bun variants share their route/server implementation. This compares complete stacks, not language speed alone.

Axon and static Rust use scratch images containing only the executable; Rust statically includes musl, while Axon has no libc imports. The glibc Rust image also starts from scratch but copies the executable and its required loader/shared libraries. Bun uses the pinned official 1.3.13-alpine base; React/react-dom are 19.2.8. Image IDs, base digest, binary/source hashes, tool versions and build logs are retained.

Servers run as UID/GID 65532, read-only root filesystem, all capabilities dropped, no-new-privileges, 1024 MiB RAM with swap disabled. The one-worker test uses CPU 0 and a one-CPU quota; four-worker tests use CPUs 0–3 and a four-CPU quota. The load container and sampler use CPUs 4–7. Traffic crosses the same Docker bridge entirely inside Linux; there are no host port mappings or macOS forwarding paths.

Axon uses worker processes (1 or 4 total). Rust uses one process with 1 or 4 Tokio worker threads plus the main thread. Bun uses one serving process, or a supervisor plus four serving processes sharing a port with SO_REUSEPORT. Container CPU and memory include all workers, supervisors and threads.

Each server/budget is checked against all 1,000 valid prop values from React, plus routing, escaping/Unicode, 100 concurrent requests and 129 pipelined responses. Performance is wrk -t4 -c64, no pipelining, 5 runs of 10s after 3s warm-up. Server order is shuffled. Latencies are closed-loop and can hide coordinated omission.

Memory is sampled during measured loads, after warm-up: container cgroup usage minus inactive file cache (Docker-style working set), not RSS/PSS; it includes charged kernel memory. Startup and warm-up spikes are not included in the table peaks. Raw usage and samples are retained. CPU/request uses cgroup CPU nanoseconds, including user/kernel time for the complete container. Sampled peaks may miss shorter spikes. Quota throttling and client CPU usage are recorded.

## Image size

| Image | Uncompressed file payload MiB | gzip docker-save archive MiB |
|---|---:|---:|
| Axon JSX | 0.0226 | 0.0147 |
| Rust Hyper | 0.7540 | 0.4019 |
| Rust Hyper glibc | 3.2216 | 1.5777 |
| Bun direct | 104.4398 | 43.9074 |
| Bun React | 111.6639 | 45.1731 |

The gzip column is a locally compressed docker-save archive, including image metadata; it is not measured registry transfer size. Uncompressed payload sums regular files in an exported fresh root filesystem, excluding Docker-injected host/resolver files and .dockerenv. It excludes tar padding and metadata, and is not allocated disk usage. Shared Bun layers are counted for each standalone image. Docker/containerd also reports image content size separately in the raw manifest. Build tools are excluded.

## 1 CPU(s), 1 rendering worker(s)

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Measured-load peak working set MiB | Start→first response ms | Client CPU cores | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 146,718 | 142,764–170,577 | 6.60 | 393 | 960 | 1.55 | 76.0 | 1.54 | 0 / 0 | True |
| Rust Hyper | 169,936 | 166,757–172,258 | 5.88 | 358 | 570 | 1.90 | 120.2 | 1.28 | 0 / 0 | True |
| Rust Hyper glibc | 168,443 | 151,750–172,644 | 6.00 | 359 | 604 | 2.04 | 77.5 | 1.29 | 0 / 0 | True |
| Bun direct | 78,714 | 77,692–80,661 | 12.61 | 753 | 1590 | 15.58 | 79.9 | 0.70 | 0 / 0 | True |
| Bun React | 40,884 | 40,436–42,834 | 24.10 | 1480 | 3140 | 53.21 | 104.3 | 0.48 | 0 / 0 | True |

## 4 CPU(s), 4 rendering worker(s)

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Measured-load peak working set MiB | Start→first response ms | Client CPU cores | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 612,113 | 597,882–618,227 | 6.14 | 73 | 671 | 2.32 | 89.3 | 3.85 | 0 / 0 | True |
| Rust Hyper | 169,545 | 155,173–175,049 | 20.18 | 368 | 770 | 2.81 | 79.3 | 1.75 | 0 / 0 | True |
| Rust Hyper glibc | 367,487 | 349,001–375,659 | 9.12 | 156 | 398 | 3.17 | 81.5 | 2.91 | 0 / 0 | True |
| Bun direct | 275,444 | 265,690–295,977 | 14.28 | 204 | 1000 | 64.60 | 89.9 | 2.41 | 0 / 0 | True |
| Bun React | 140,885 | 135,682–149,469 | 27.90 | 402 | 1340 | 216.81 | 116.7 | 1.57 | 0 / 0 | True |

Startup is the median of 5 fresh-container starts with images already cached, measured from the Docker start API call until the first response with verified HTML; container creation, pulls and builds are excluded. Polling, Docker control-plane latency and bridge setup are included. For multicore it measures the first ready worker, not the entire pool.

Results are local VM measurements on a shared physical machine. Inspect run ranges and load-client CPU consumption before interpreting small gaps or multicore limits. No energy or universal language-performance claims follow from this one small SSR page.

Raw artifacts: `bench/http/results/2026-10-23-213717-docker-ssr`.

## Observations

- All 10 main comparisons were valid: 50 measured runs plus 10 warm-ups had zero socket errors and zero non-2xx responses. Each configuration passed the full 1,000-input React parity and HTTP behavior checks.
- Rust had the highest one-CPU median throughput, about 168–170k req/s versus Axon 147k. Run ranges overlap in some cases, and the Axon one-CPU range was relatively wide; do not interpret the median gap as a guaranteed ordering on another host.
- With four workers, observed Axon throughput was 612k req/s, Rust glibc 367k, static-musl Rust 170k, Bun direct 275k and Bun React 141k. These configurations use different concurrency models. The glibc result demonstrates that the Rust runtime-library/package choice materially affects this workload; it does not isolate the allocator as the sole cause.
- The four-worker Axon load client averaged 3.85 out of four available CPUs. That case may be load-generator-limited, so 612k req/s is observed capacity in this setup, not a proven maximum server rate.
- An initial 512-MiB preflight OOM-killed the four-worker Bun/React container during warm-up. The main comparison therefore gives every stack the same 1-GiB limit. See [the low-memory preflight record](PREFLIGHT-docker-512MiB-2026-10-23.md). The measured-load memory peaks here exclude startup/warm-up spikes and do not negate that transient failure.
- The measurement-time driver is archived as measurement-harness.py. Later source changes only clarify memory-window labels in report rendering; report_renderer_sha256 records the renderer used for this report.
