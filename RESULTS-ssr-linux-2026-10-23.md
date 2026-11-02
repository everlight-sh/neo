# SSR: pure Axon versus Bun + React

Measured 2026-10-23T22:00:13.515502+02:00; aarch64 Linux VM; 8 logical CPUs; Linux 6.8.0-64-generic.

Both serve the same catalog page: generated product rows, formatted prices and total, and escaped HTML text. Every measured route renders from its request parameter; responses are not cached. Axon constructs HTML with pure functions and its own HTTP runtime. Bun runs React components through react-dom/server renderToString with NODE_ENV=production. Neither sends client JavaScript or hydrates.

Bun 1.3.13; React/react-dom 19.2.8; Ubuntu clang version 18.1.3 (1ubuntu1). Three page sizes: 3, 50 and 1,000 rows. 3 runs of 5s after 2s warm-up, wrk with 4 threads and 64 connections. Server order is shuffled with seed 20261023.

Before each comparison, output for nine page sizes is checked byte-for-byte against an independent Python renderer, along with content type/length, escaped text, route validation and keep-alive. Runtime tests additionally cover concurrent requests and pipelining. The client shares the machine with the server; these are short saturation measurements, not production capacity or energy measurements.

Axon (1 worker) and Bun + React are the comparison with one rendering worker each. Axon (default) uses one process per configured CPU and shows additional parallel capacity; Bun here has one process/event loop. Worker counts are not CPU affinity. React builds a general component tree; Axon directly assembles HTML for this page, so this measures that implementation tradeoff rather than universal language speed.

CPU/request includes every worker process and all its threads, user + kernel time. Memory is sampled every 100 ms across all workers; the footprint column is Linux PSS. Aggregate RSS can count shared pages more than once. Linux uses smaps_rollup for RSS/PSS and procfs CPU; Mac uses calibrated libproc counters. Latencies are closed-loop wrk values and can hide coordinated omission.

## Deployment size

| Server | Executable and app/dependencies MiB |
|---|---:|
| Axon (1 worker) | 0.03 |
| Axon (default) | 0.03 |
| Bun + React | 103.84 |

Axon size is its executable. Bun size includes the Bun executable, example source and installed react/react-dom/scheduler packages; build tools and OS libraries are excluded.

## /page/3

HTML body: 613 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Processes | Aggregate RSS MiB | Linux PSS MiB | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon (1 worker) | 197,945 | 192,830–251,424 | 4.64 | 320 | 762 | 1 | 0.86 | 0.86 | True |
| Axon (default) | 567,826 | 542,096–585,846 | 6.33 | 67 | 1620 | 8 | 1.27 | 1.02 | True |
| Bun + React | 36,987 | 35,653–38,218 | 28.46 | 1580 | 3260 | 1 | 105.43 | 104.24 | True |

## /page/50

HTML body: 5,379 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Processes | Aggregate RSS MiB | Linux PSS MiB | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon (1 worker) | 103,405 | 98,072–116,088 | 9.45 | 617 | 1260 | 1 | 1.20 | 1.20 | True |
| Axon (default) | 456,394 | 392,154–471,510 | 10.02 | 71 | 2140 | 8 | 1.88 | 1.60 | True |
| Bun + React | 10,019 | 10,007–10,026 | 107.49 | 6300 | 12140 | 1 | 143.30 | 142.12 | True |

## /page/1000

HTML body: 103,032 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Processes | Aggregate RSS MiB | Linux PSS MiB | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon (1 worker) | 11,773 | 11,739–11,827 | 84.89 | 5370 | 11220 | 1 | 11.14 | 11.14 | True |
| Axon (default) | 73,118 | 71,087–73,467 | 85.43 | 656 | 4200 | 8 | 13.96 | 13.71 | True |
| Bun + React | 677 | 677–684 | 1687.46 | 91310 | 168550 | 1 | 230.35 | 229.16 | True |


## Runtime dependencies

The Axon application and runtime are Axon source with direct ARM64 kernel syscalls. Linux is static with no libc, CRT, ELF interpreter or shared libraries. Mac imports no libc functions but retains the required libSystem/dyld loader dependency. Python/LLVM are build tools. The Bun example requires Bun and its React packages. The Axon HTTP subset is narrower than Bun’s HTTP implementation.

Raw commands, hashes, measurements, CPU/memory samples and logs: `/axon/bench/http/results/2026-10-23-220013-ssr`.

## Reading this run

- All nine comparisons and 27 measured runs completed with zero warm-up or measured socket errors/non-2xx responses. All sampled process counts matched: one Axon worker, eight default Axon workers, or one Bun process.
- For 50 rows with one rendering worker, Axon reached 103,405 versus Bun/React’s 10,019 requests/s (10.3 times). CPU cost was 9.45 versus 107.49 microseconds/request, and sampled PSS 1.20 versus 142.12 MiB. Axon default workers reached 456,394 requests/s; that parallel result has a different worker budget.
- For 1,000 rows, single-worker Axon reached 11,773 versus Bun/React’s 677 requests/s. Default Axon workers reached 73,118. All return the same 103,032-byte HTML body.
- The Axon executable is 27,656 bytes (27.0 KiB), static with no undefined imports, interpreter or shared libraries. The exact benchmark binary passed the SSR smoke suite inside an otherwise empty Linux filesystem.
- Smoke checks passed for both servers: nine page sizes against an independent Python renderer, escaped text, route validation, keep-alive, 100 concurrent requests, 129 ordered pipelined pages and a large response. Axon was checked with one and four workers; Bun/React used production mode. Logs are included beside measurements.json.
- This is an eight-vCPU ARM64 Ubuntu Colima VZ VM on the M1 Pro host. Client and server share its CPUs. The /axon mount is this repository; host raw artifacts are bench/http/results/2026-10-23-220013-ssr.
- The measurement-time benchmark driver is preserved as measurement-harness.py and matches its recorded source hash. The report renderer later received a blank-line formatting fix; no measurements changed.
- Framework overhead and worker budgets matter: React builds a component tree and Axon directly assembles HTML. These examples do not provide equivalent UI frameworks. React/react-dom are pinned at 19.2.8 and run with NODE_ENV=production; neither response contains client JavaScript.
