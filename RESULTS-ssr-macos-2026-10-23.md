# SSR: pure Axon versus Bun + React

Measured 2026-10-23T22:03:32.700459+02:00; Apple M1 Pro; 10 logical CPUs; Darwin 27.0.0.

Both serve the same catalog page: generated product rows, formatted prices and total, and escaped HTML text. Every measured route renders from its request parameter; responses are not cached. Axon constructs HTML with pure functions and its own HTTP runtime. Bun runs React components through react-dom/server renderToString with NODE_ENV=production. Neither sends client JavaScript or hydrates.

Bun 1.3.13; React/react-dom 19.2.8; Apple clang version 21.0.0 (clang-2100.3.34.2). Three page sizes: 3, 50 and 1,000 rows. 3 runs of 5s after 2s warm-up, wrk with 4 threads and 64 connections. Server order is shuffled with seed 20261023.

Before each comparison, output for nine page sizes is checked byte-for-byte against an independent Python renderer, along with content type/length, escaped text, route validation and keep-alive. Runtime tests additionally cover concurrent requests and pipelining. The client shares the machine with the server; these are short saturation measurements, not production capacity or energy measurements.

Axon (1 worker) and Bun + React are the comparison with one rendering worker each. Axon (default) uses one process per configured CPU and shows additional parallel capacity; Bun here has one process/event loop. Worker counts are not CPU affinity. React builds a general component tree; Axon directly assembles HTML for this page, so this measures that implementation tradeoff rather than universal language speed.

CPU/request includes every worker process and all its threads, user + kernel time. Memory is sampled every 100 ms across all workers; the footprint column is macOS physical footprint. Aggregate RSS can count shared pages more than once. Linux uses smaps_rollup for RSS/PSS and procfs CPU; Mac uses calibrated libproc counters. Latencies are closed-loop wrk values and can hide coordinated omission.

## Deployment size

| Server | Executable and app/dependencies MiB |
|---|---:|
| Axon (1 worker) | 0.05 |
| Axon (default) | 0.05 |
| Bun + React | 67.38 |

Axon size is its executable. Bun size includes the Bun executable, example source and installed react/react-dom/scheduler packages; build tools and OS libraries are excluded.

## /page/3

HTML body: 613 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon (1 worker) | 103,375 | 103,373–105,307 | 9.54 | 636 | 1100 | 1 | 3.27 | 2.80 | True |
| Axon (default) | 111,254 | 111,074–111,566 | 19.04 | 552 | 758 | 10 | 4.86 | 4.64 | True |
| Bun + React | 36,521 | 35,763–36,813 | 25.91 | 1570 | 6410 | 1 | 248.64 | 57.58 | True |

## /page/50

HTML body: 5,379 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon (1 worker) | 75,344 | 74,998–75,721 | 13.17 | 860 | 1200 | 1 | 2.59 | 3.16 | True |
| Axon (default) | 106,290 | 98,191–106,548 | 23.73 | 582 | 738 | 10 | 5.64 | 5.42 | True |
| Bun + React | 10,223 | 9,993–10,420 | 89.33 | 5520 | 14230 | 1 | 258.45 | 82.16 | True |

## /page/1000

HTML body: 103,032 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon (1 worker) | 11,764 | 11,600–11,837 | 84.49 | 5340 | 11010 | 1 | 13.84 | 13.38 | True |
| Axon (default) | 43,229 | 43,026–43,564 | 113.15 | 1360 | 2420 | 10 | 18.77 | 18.56 | True |
| Bun + React | 773 | 769–816 | 1328.13 | 80460 | 122620 | 1 | 317.16 | 145.91 | True |


## Runtime dependencies

The Axon application and runtime are Axon source with direct ARM64 kernel syscalls. Linux is static with no libc, CRT, ELF interpreter or shared libraries. Mac imports no libc functions but retains the required libSystem/dyld loader dependency. Python/LLVM are build tools. The Bun example requires Bun and its React packages. The Axon HTTP subset is narrower than Bun’s HTTP implementation.

Raw commands, hashes, measurements, CPU/memory samples and logs: `bench/http/results/2026-10-23-220332-ssr`.

## Reading this run

- All nine comparisons and 27 measured runs completed with zero warm-up or measured socket errors/non-2xx responses. Sampled process counts matched the budgets: one Axon worker, ten default Axon workers, or one Bun process.
- For 50 rows and one rendering worker, Axon reached 75,344 versus Bun/React’s 10,223 requests/s (7.4 times), at 13.17 versus 89.33 CPU microseconds/request. Default Axon workers reached 106,290 requests/s, with a different worker budget.
- For 1,000 rows, single-worker Axon reached 11,764 versus Bun/React’s 773 requests/s; default Axon workers reached 43,229. Every response contains the same 103,032-byte HTML body.
- Both servers passed exact-output checks against an independent Python renderer for nine page sizes, escaped text, routing, invalid counts, headers, keep-alive, 100 concurrent requests, 129 ordered pipelined pages and a large response. Axon was tested with one and four workers; Bun/React ran in production mode. All 28 compiler unit tests also passed.
- Axon imports no libc functions; the required Mac libSystem/dyld loader dependency remains. Its separate Linux build is a 27.0 KiB static ELF and passed SSR inside an otherwise empty root filesystem. Runtime source was not changed for this example.
- The test VM was stopped during these native M1 Pro measurements. Client and server share the machine; this environment is separate from the Linux VM report.
- The measurement-time driver is preserved as measurement-harness.py and matches the recorded hash. The report renderer received a later blank-line formatting fix; no measurements changed.
- React/react-dom are pinned at 19.2.8 with NODE_ENV=production. React builds a general component tree, while Axon directly constructs HTML. This compares that implementation tradeoff; neither example sends client JavaScript or hydrates.
