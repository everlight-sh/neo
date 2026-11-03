# HTTP benchmarks: Neo, Rust, Go and Bun

Measured 2026-11-03T01:58:25.887108+01:00. Apple M1 Pro; 10 logical CPUs; 16.00 GiB RAM; Darwin 27.2.0.

wrk wrk 4.2.0 [kqueue] Copyright (C) 2012 Will Glozer, 4 client threads. 3 round(s); in each, every scenario runs every server once in a freshly shuffled order (seed 20261023), with 1 measured run(s) of 5s after a 2s warm-up per start. Client and server share this machine.

Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Neo runs one process per worker. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set NEO_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. "Other cores" is the machine's busy CPU during each run minus the server, wrk and this script: load from the rest of the machine (median over runs). Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is macOS physical footprint. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission; p99 is the median of the runs' p99, with the worst run's p99 beside it.

Pipelined latency percentiles are omitted: the macOS wrk build emits invalid/nonmonotonic values for them. Pipeline throughput and CPU use the request and CPU counters.

Versions: Neo: kqueue worker processes, examples/http.neo; Neo (before): supplied binary neo-main; Clang: Apple clang version 21.0.0 (clang-2100.4.1.1); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 darwin/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle macOS physical footprint MiB | Startup ms |
|---|---:|---:|---:|---:|
| Neo | 0.08 | 3.02 | 2.75 | 11.8 |
| Neo (before) | 0.08 | 2.72 | 2.45 | 12.1 |
| Rust | 0.91 | 2.39 | 1.47 | 12.1 |
| Go | 7.73 | 9.52 | 3.37 | 27.0 |
| Bun | 60.15 | 25.37 | 9.70 | 30.1 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 147,515 | 147,093–147,587 | 414 | 548 (574) | 14.51 | 2.13 | 3.77 | 10 | 4.88 | 4.63 | 0 / 0 |
| Neo (before) | 142,939 | 137,800–146,840 | 426 | 568 (6690) | 17.98 | 2.56 | 2.64 | 10 | 4.69 | 4.47 | 0 / 0 |
| Rust | 152,629 | 150,237–153,826 | 376 | 570 (582) | 22.93 | 3.48 | 2.86 | 1 | 4.70 | 3.75 | 0 / 0 |
| Go | 139,924 | 138,708–142,952 | 321 | 1350 (2380) | 30.68 | 4.30 | 2.85 | 1 | 21.83 | 13.67 | 0 / 0 |
| Bun | 94,896 | 93,943–98,978 | 678 | 1320 (1340) | 10.37 | 0.99 | 2.15 | 1 | 43.56 | 16.03 | 0 / 0 |

## hello-256

Route `/`; 256 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 150,081 | 149,281–152,812 | 1650 | 2150 (2910) | 14.76 | 2.22 | 3.34 | 10 | 8.69 | 8.33 | 0 / 0 |
| Neo (before) | 148,992 | 146,271–150,034 | 1610 | 2190 (2270) | 30.38 | 4.50 | 2.33 | 10 | 8.45 | 8.24 | 0 / 0 |
| Rust | 151,648 | 147,514–153,361 | 1580 | 2160 (2290) | 25.20 | 3.79 | 2.63 | 1 | 32.16 | 31.22 | 0 / 0 |
| Go | 146,470 | 146,238–151,276 | 1230 | 4580 (17430) | 30.16 | 4.46 | 2.62 | 1 | 26.23 | 18.58 | 0 / 0 |
| Bun | 93,932 | 92,591–100,496 | 2800 | 3190 (3240) | 10.41 | 0.99 | 3.31 | 1 | 45.08 | 17.09 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 2,299,218 | 2,297,102–2,304,166 | n/a | n/a | 1.03 | 2.38 | 3.13 | 10 | 4.88 | 4.50 | 0 / 0 |
| Neo (before) | 2,195,819 | 2,125,606–2,252,525 | n/a | n/a | 1.32 | 2.88 | 3.35 | 10 | 4.69 | 4.47 | 0 / 0 |
| Rust | 2,362,877 | 2,346,977–2,391,174 | n/a | n/a | 1.83 | 4.33 | 2.18 | 1 | 4.86 | 3.91 | 0 / 0 |
| Go | 355,251 | 349,787–363,646 | n/a | n/a | 16.42 | 5.84 | 2.49 | 1 | 27.95 | 16.42 | 0 / 0 |
| Bun | 32,411 | 32,409–33,202 | n/a | n/a | 30.31 | 0.99 | 3.31 | 1 | 42.95 | 15.02 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 148,839 | 148,479–152,289 | 430 | 545 (548) | 6.54 | 0.98 | 3.42 | 1 | 3.22 | 2.66 | 0 / 0 |
| Neo (before) | 147,396 | 146,753–149,538 | 438 | 760 (762) | 6.74 | 1.00 | 3.81 | 1 | 3.20 | 2.64 | 0 / 0 |
| Rust | 141,845 | 141,414–142,634 | 438 | 610 (611) | 6.96 | 0.99 | 3.52 | 1 | 4.12 | 3.16 | 0 / 0 |
| Go | 88,097 | 88,066–88,802 | 712 | 1220 (1230) | 11.23 | 0.99 | 3.36 | 1 | 15.58 | 8.86 | 0 / 0 |
| Bun | 92,996 | 92,804–94,547 | 687 | 1330 (1330) | 10.69 | 1.00 | 3.16 | 1 | 45.12 | 15.84 | 0 / 0 |

## smooth-1000-one-worker

Route `/smooth/1000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 29,035 | 28,899–29,244 | 2210 | 2360 (2390) | 34.10 | 0.99 | 2.85 | 1 | 3.22 | 2.66 | 0 / 0 |
| Neo (before) | 28,931 | 28,832–29,053 | 2190 | 4260 (4260) | 34.25 | 0.99 | 1.81 | 1 | 3.20 | 2.64 | 0 / 0 |
| Rust | 39,797 | 39,491–39,862 | 1630 | 1770 (1800) | 24.77 | 0.98 | 2.12 | 1 | 4.31 | 3.34 | 0 / 0 |
| Go | 17,679 | 17,666–17,752 | 3640 | 5590 (5610) | 56.47 | 1.00 | 1.69 | 1 | 16.09 | 9.33 | 0 / 0 |
| Bun | 9,294 | 9,229–9,315 | 6750 | 13170 (13210) | 108.05 | 1.00 | 1.67 | 1 | 47.09 | 19.14 | 0 / 0 |

## smooth-10000-one-worker

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 3,263 | 3,237–3,313 | 19470 | 20130 (20420) | 306.17 | 1.00 | 2.17 | 1 | 3.25 | 2.69 | 0 / 0 |
| Neo (before) | 3,255 | 3,228–3,304 | 19180 | 289350 (293010) | 306.13 | 1.00 | 2.46 | 1 | 3.23 | 2.67 | 0 / 0 |
| Rust | 4,886 | 4,883–4,892 | 13230 | 13780 (13840) | 204.80 | 1.00 | 2.50 | 1 | 4.59 | 3.64 | 0 / 0 |
| Go | 2,110 | 2,095–2,117 | 28130 | 98770 (100370) | 475.73 | 1.00 | 1.86 | 1 | 15.89 | 9.05 | 0 / 0 |
| Bun | 853 | 850–856 | 73870 | 100460 (103970) | 1176.67 | 1.00 | 2.45 | 1 | 57.50 | 22.92 | 0 / 0 |

## smooth-10000-default

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 25,471 | 25,308–25,882 | 1900 | 7770 (8420) | 354.05 | 9.03 | 0.80 | 10 | 6.66 | 6.22 | 0 / 0 |
| Neo (before) | 25,582 | 25,289–25,590 | 1920 | 8350 (8870) | 355.59 | 9.04 | 0.79 | 10 | 6.50 | 6.06 | 0 / 0 |
| Rust | 35,002 | 34,665–35,209 | 1750 | 3660 (3870) | 250.70 | 8.74 | 0.96 | 1 | 7.62 | 6.69 | 0 / 0 |
| Go | 10,609 | 10,398–10,938 | 6290 | 30150 (34460) | 665.05 | 7.07 | 1.86 | 1 | 32.73 | 21.19 | 0 / 0 |
| Bun | 857 | 843–858 | 74100 | 77110 (84660) | 1176.76 | 1.00 | 2.46 | 1 | 57.69 | 31.22 | 0 / 0 |

## nbody-default

Route `POST:/nbody`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 21,737 | 21,017–22,045 | 2210 | 10380 (11540) | 413.18 | 8.91 | 0.79 | 10 | 5.58 | 5.16 | 0 / 0 |
| Neo (before) | 21,816 | 21,713–21,995 | 2220 | 10350 (11020) | 416.19 | 9.07 | 0.73 | 10 | 5.33 | 4.88 | 0 / 0 |
| Rust | 16,704 | 16,650–16,775 | 3690 | 8430 (8710) | 547.22 | 9.12 | 0.77 | 1 | 6.12 | 5.17 | 0 / 0 |
| Go | 10,063 | 9,969–10,130 | 6490 | 36820 (38550) | 741.21 | 7.44 | 1.50 | 1 | 25.27 | 17.13 | 0 / 0 |
| Bun | 1,060 | 1,054–1,060 | 59660 | 67810 (72190) | 951.45 | 1.00 | 1.71 | 1 | 55.67 | 28.86 | 0 / 0 |

## Each run with the load before it

req/s of each run, with the one-minute load average just before it started (the whole machine, including the previous run).

| Scenario | Round | Neo | Neo (before) | Rust | Go | Bun |
|---|---:|---:|---:|---:|---:|---:|
| hello-64 | 1 | 147,587 @ 12.44 | 137,800 @ 14.47 | 153,826 @ 5.43 | 138,708 @ 5.37 | 98,978 @ 8.78 |
| hello-64 | 2 | 147,515 @ 3.43 | 142,939 @ 2.90 | 152,629 @ 2.86 | 142,952 @ 4.17 | 94,896 @ 2.92 |
| hello-64 | 3 | 147,093 @ 3.45 | 146,840 @ 2.97 | 150,237 @ 2.96 | 139,924 @ 2.95 | 93,943 @ 2.93 |
| hello-256 | 1 | 150,081 @ 4.73 | 148,992 @ 5.20 | 151,648 @ 5.92 | 146,238 @ 4.93 | 100,496 @ 4.25 |
| hello-256 | 2 | 152,812 @ 2.98 | 146,271 @ 2.92 | 153,361 @ 2.87 | 146,470 @ 3.08 | 92,591 @ 2.89 |
| hello-256 | 3 | 149,281 @ 3.19 | 150,034 @ 3.88 | 147,514 @ 4.85 | 151,276 @ 4.90 | 93,932 @ 3.77 |
| pipeline-16 | 1 | 2,299,218 @ 4.60 | 2,252,525 @ 4.40 | 2,391,174 @ 5.22 | 363,646 @ 4.07 | 32,409 @ 3.36 |
| pipeline-16 | 2 | 2,297,102 @ 3.00 | 2,195,819 @ 2.96 | 2,346,977 @ 3.41 | 349,787 @ 2.99 | 32,411 @ 2.87 |
| pipeline-16 | 3 | 2,304,166 @ 3.62 | 2,125,606 @ 3.74 | 2,362,877 @ 2.97 | 355,251 @ 3.75 | 33,202 @ 3.61 |
| hello-one-worker | 1 | 152,289 @ 4.55 | 146,753 @ 3.60 | 141,414 @ 3.69 | 88,802 @ 3.93 | 94,547 @ 4.31 |
| hello-one-worker | 2 | 148,839 @ 2.89 | 147,396 @ 2.87 | 142,634 @ 2.92 | 88,097 @ 2.97 | 92,996 @ 2.93 |
| hello-one-worker | 3 | 148,479 @ 4.26 | 149,538 @ 4.38 | 141,845 @ 4.45 | 88,066 @ 3.32 | 92,804 @ 4.30 |
| smooth-1000-one-worker | 1 | 29,035 @ 2.86 | 28,832 @ 2.84 | 39,862 @ 2.97 | 17,752 @ 2.91 | 9,294 @ 2.98 |
| smooth-1000-one-worker | 2 | 28,899 @ 2.88 | 28,931 @ 2.92 | 39,491 @ 3.39 | 17,679 @ 2.94 | 9,229 @ 2.93 |
| smooth-1000-one-worker | 3 | 29,244 @ 3.53 | 29,053 @ 3.20 | 39,797 @ 2.96 | 17,666 @ 2.98 | 9,315 @ 3.00 |
| smooth-10000-one-worker | 1 | 3,237 @ 4.00 | 3,228 @ 2.87 | 4,892 @ 2.88 | 2,110 @ 2.90 | 853 @ 2.86 |
| smooth-10000-one-worker | 2 | 3,263 @ 2.82 | 3,255 @ 2.85 | 4,883 @ 2.79 | 2,095 @ 2.97 | 850 @ 2.89 |
| smooth-10000-one-worker | 3 | 3,313 @ 3.46 | 3,304 @ 3.21 | 4,886 @ 3.37 | 2,117 @ 3.28 | 856 @ 3.62 |
| smooth-10000-default | 1 | 25,882 @ 2.88 | 25,590 @ 3.67 | 34,665 @ 3.94 | 10,398 @ 4.80 | 843 @ 4.40 |
| smooth-10000-default | 2 | 25,308 @ 3.35 | 25,289 @ 2.89 | 35,002 @ 2.89 | 10,609 @ 2.90 | 857 @ 2.89 |
| smooth-10000-default | 3 | 25,471 @ 4.29 | 25,582 @ 3.24 | 35,209 @ 2.97 | 10,938 @ 3.97 | 858 @ 3.52 |
| nbody-default | 1 | 21,737 @ 3.01 | 21,713 @ 2.94 | 16,650 @ 3.63 | 9,969 @ 2.97 | 1,054 @ 2.97 |
| nbody-default | 2 | 21,017 @ 3.01 | 21,816 @ 4.05 | 16,775 @ 3.34 | 10,063 @ 4.04 | 1,060 @ 8.56 |
| nbody-default | 3 | 22,045 @ 6.48 | 21,995 @ 4.53 | 16,704 @ 5.01 | 10,130 @ 4.29 | 1,060 @ 2.94 |

## Dependency boundary and limits

Neo allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Neo source, with compiler primitives for direct kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `bench/http/results/2026-11-03-015825-native`.
