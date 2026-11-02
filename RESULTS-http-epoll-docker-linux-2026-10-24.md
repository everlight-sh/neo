# Docker SSR: Axon, Rust, Bun direct and Bun React

Measured 2026-10-23T22:12:52.865173+00:00 on ARM64 Linux in an 8-vCPU, 6-GiB Colima VM on Apple M1 Pro. Docker Engine 28.4.0. Runtime images are linux/arm64; no CPU emulation.

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
| Axon JSX | 190,430 | 186,829–193,104 | 5.25 | 298 | 777 | 1.58 | 74.8 | 1.52 | 0 / 0 | True |
| Rust Hyper | 168,483 | 166,229–169,614 | 5.94 | 361 | 553 | 1.89 | 75.9 | 1.24 | 0 / 0 | True |
| Rust Hyper glibc | 174,804 | 161,886–176,626 | 5.81 | 342 | 960 | 2.10 | 75.1 | 1.26 | 0 / 0 | True |
| Bun direct | 80,023 | 77,981–83,936 | 12.41 | 750 | 1600 | 15.77 | 79.9 | 0.69 | 0 / 0 | True |
| Bun React | 41,666 | 41,083–41,924 | 23.79 | 1440 | 3290 | 51.75 | 100.1 | 0.46 | 0 / 0 | True |
| Axon poll baseline | 162,731 | 147,976–200,842 | 5.95 | 347 | 890 | 1.55 | 78.3 | 1.54 | 0 / 0 | True |
| Axon current poll | 158,108 | 151,939–163,783 | 6.29 | 358 | 910 | 1.55 | 79.3 | 1.53 | 0 / 0 | True |

## 4 CPU(s), 4 rendering worker(s)

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Measured-load peak working set MiB | Start→first response ms | Client CPU cores | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 641,513 | 634,253–642,029 | 5.48 | 70 | 293 | 2.36 | 70.4 | 3.95 | 0 / 0 | True |
| Rust Hyper | 174,797 | 156,203–179,915 | 19.71 | 357 | 766 | 2.82 | 79.0 | 1.73 | 0 / 0 | True |
| Rust Hyper glibc | 381,721 | 376,828–384,287 | 8.85 | 152 | 356 | 3.52 | 80.1 | 2.90 | 0 / 0 | True |
| Bun direct | 298,558 | 286,814–302,104 | 13.34 | 187 | 930 | 65.46 | 89.6 | 2.35 | 0 / 0 | True |
| Bun React | 144,036 | 140,670–145,002 | 27.83 | 413 | 1400 | 217.19 | 122.2 | 1.55 | 0 / 0 | True |
| Axon poll baseline | 649,986 | 648,133–656,520 | 5.77 | 69 | 426 | 2.09 | 84.2 | 3.89 | 0 / 0 | True |
| Axon current poll | 674,091 | 671,089–684,995 | 5.57 | 65 | 269 | 2.09 | 82.6 | 3.93 | 0 / 0 | True |

Startup is the median of 5 fresh-container starts with images already cached, measured from the Docker start API call until the first response with verified HTML; container creation, pulls and builds are excluded. Polling, Docker control-plane latency and bridge setup are included. For multicore it measures the first ready worker, not the entire pool.

Results are local VM measurements on a shared physical machine. Inspect run ranges and load-client CPU consumption before interpreting small gaps or multicore limits. No energy or universal language-performance claims follow from this one small SSR page.

Raw artifacts: `bench/http/results/2026-10-23-221252-docker-ssr`.

## Observations

- On one CPU, Axon epoll's 190,430 req/s median exceeds Rust musl by 13.0% and Rust glibc by 8.9%. In these five runs its minimum exceeds either Rust build's maximum. These are measurements of this SSR workload and stack configuration, not a general language ranking.
- The same Axon executable is 20.4% faster with epoll than AXON_HTTP_POLL=1 and uses 16.6% less server CPU/request. User CPU changes from 0.582 to 0.560 microseconds/request; kernel CPU from 5.712 to 4.692. This supports the backend improvement without relying on traced timings. The preserved original poll image is noisier: one run reaches 200,842 req/s, higher than epoll's median; the table keeps that outlier.
- On four CPUs, epoll reaches 641,513 req/s, 68.1% above the faster Rust build, but 4.8% below the same-binary poll fallback. It uses 1.7% less server CPU/request. All three multicore Axon cases consume 3.89–3.95 of the four available load-client CPUs, plus sampler overhead. Do not present epoll as a multicore throughput improvement or any of these rates as maximum server capacity. The poll fallback remains available for workload-specific comparison.
- The current Axon binary/image file payload is 26,224 bytes, versus the preserved baseline's 23,728 bytes. readelf reports no dynamic section, interpreter or NEEDED entries; nm -u is empty. The server passes in an otherwise empty root as well as the restricted scratch container. No C runtime, libc, libSystem or external event-loop library was added. Python/LLVM and the TSX translator remain build tools; Linux is the required kernel ABI.
- The separate strace profiles show roughly one read and one send per request in all stacks. Baseline Axon makes 606 ppoll calls for 35,876 completed requests; epoll makes 579 waits and only 65 epoll_ctl calls for 34,788 completed requests. Control calls are amortized over connections, not issued for each ordinary request. Counts cannot by themselves assign the observed savings to a particular kernel operation; tracing changes scheduling and timing.
- All 14 final configurations passed correctness validation; all 70 timed runs and 14 warmups had zero reported socket errors or non-success responses. Timed runs completed 198,687,803 responses. New regression checks cover ready-batch closes, slot compaction/descriptor reuse and draining 80 large responses through backpressure before a different final response. Existing pipelining/framing/slow-reader tests pass. Captured Linux and macOS validation logs are retained under the raw artifact directory.
- An earlier attempt at 2026-10-23-221057-docker-ssr failed Bun direct validation with a bare AssertionError. Its cause was not established; that attempt was stopped, excluded and preserved, including the interrupted report. Thirty subsequent complete Bun direct validations passed, followed by this full clean rerun. This is not evidence of a measured Bun throughput failure, and the later success does not explain the original assertion. The short 2026-10-23-220824-docker-ssr pilot is also retained separately.

## HTTP backend comparison

Current Axon uses persistent level-triggered epoll registrations through direct Linux syscalls. The poll baseline is the preserved executable/image from before this change, rerun in this same session with identical resource and load settings. Framing, rendering and the 64-response batching policy are unchanged. Raw image manifests retain both source/binary hashes.

The syscall-count profiles are intrusive strace runs, separate from these untraced measurements. Both backends already use approximately one read and one send per unpipelined request. Registration persistence avoids rebuilding and attaching a wait set for all open sockets on each wait; counts alone do not measure that cost or establish how much of the gain comes from kernel versus user-space dispatch.
