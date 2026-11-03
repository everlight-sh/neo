# HTTP benchmarks: Neo, Rust, Go and Bun

Measured 2026-11-03T01:24:51.409278+01:00. Apple M1 Pro; 10 logical CPUs; 16.00 GiB RAM; Darwin 27.2.0.

wrk wrk 4.2.0 [kqueue] Copyright (C) 2012 Will Glozer, 4 client threads. 3 round(s); in each, every scenario runs every server once in a freshly shuffled order (seed 20261023), with 1 measured run(s) of 5s after a 2s warm-up per start. Client and server share this machine.

Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Neo runs one process per worker. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set NEO_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. "Other cores" is the machine's busy CPU during each run minus the server, wrk and this script: load from the rest of the machine (median over runs). Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is macOS physical footprint. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission; p99 is the median of the runs' p99, with the worst run's p99 beside it.

Pipelined latency percentiles are omitted: the macOS wrk build emits invalid/nonmonotonic values for them. Pipeline throughput and CPU use the request and CPU counters.

Versions: Neo: kqueue worker processes, examples/http.neo; Neo (before): supplied binary neo-main; Clang: Apple clang version 21.0.0 (clang-2100.4.1.1); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 darwin/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle macOS physical footprint MiB | Startup ms |
|---|---:|---:|---:|---:|
| Neo | 0.08 | 3.00 | 2.74 | 12.0 |
| Neo (before) | 0.08 | 2.72 | 2.45 | 10.5 |
| Rust | 0.91 | 2.39 | 1.47 | 11.9 |
| Go | 7.73 | 9.54 | 3.39 | 29.0 |
| Bun | 60.15 | 25.41 | 9.70 | 30.8 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 148,051 | 139,448–148,377 | 413 | 568 (761) | 14.47 | 2.10 | 3.96 | 10 | 4.95 | 4.61 | 0 / 0 |
| Neo (before) | 144,498 | 138,012–144,998 | 423 | 557 (3540) | 18.26 | 2.60 | 3.77 | 10 | 4.78 | 4.59 | 0 / 0 |
| Rust | 152,632 | 152,517–154,683 | 374 | 568 (786) | 20.87 | 3.19 | 3.12 | 1 | 4.75 | 3.80 | 0 / 0 |
| Go | 138,317 | 130,885–139,923 | 315 | 1920 (2750) | 29.28 | 3.99 | 3.46 | 1 | 21.77 | 14.09 | 0 / 0 |
| Bun | 97,760 | 88,060–98,276 | 666 | 1460 (3020) | 10.43 | 0.99 | 4.64 | 1 | 44.45 | 16.49 | 0 / 0 |

## hello-256

Route `/`; 256 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 150,244 | 140,854–151,025 | 1650 | 2720 (2890) | 14.36 | 2.11 | 3.98 | 10 | 8.67 | 8.31 | 0 / 0 |
| Neo (before) | 150,412 | 149,043–153,083 | 1580 | 2900 (5300) | 26.16 | 3.94 | 2.79 | 10 | 8.50 | 8.30 | 0 / 0 |
| Rust | 153,110 | 150,579–154,352 | 1560 | 2220 (2490) | 23.26 | 3.54 | 2.88 | 1 | 32.67 | 31.73 | 0 / 0 |
| Go | 149,308 | 145,151–149,315 | 1230 | 5180 (5180) | 29.63 | 4.37 | 2.81 | 1 | 26.38 | 17.75 | 0 / 0 |
| Bun | 95,416 | 89,404–97,654 | 2760 | 3520 (4090) | 10.54 | 0.99 | 3.98 | 1 | 44.02 | 16.22 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 2,238,402 | 2,216,967–2,262,599 | n/a | n/a | 1.04 | 2.33 | 4.16 | 10 | 4.95 | 4.61 | 0 / 0 |
| Neo (before) | 2,226,005 | 2,141,104–2,227,586 | n/a | n/a | 1.29 | 2.83 | 3.35 | 10 | 4.69 | 4.47 | 0 / 0 |
| Rust | 2,316,097 | 2,276,785–2,324,227 | n/a | n/a | 1.75 | 4.02 | 2.58 | 1 | 5.03 | 4.08 | 0 / 0 |
| Go | 357,196 | 349,593–362,791 | n/a | n/a | 15.60 | 5.55 | 2.66 | 1 | 27.23 | 17.66 | 0 / 0 |
| Bun | 22,580 | 20,971–30,613 | n/a | n/a | 39.96 | 0.99 | 4.89 | 1 | 43.31 | 15.33 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 148,211 | 146,746–148,476 | 429 | 547 (671) | 6.61 | 0.98 | 3.81 | 1 | 3.20 | 2.64 | 0 / 0 |
| Neo (before) | 146,838 | 144,789–147,585 | 438 | 760 (805) | 6.81 | 0.99 | 4.68 | 1 | 3.20 | 2.64 | 0 / 0 |
| Rust | 138,383 | 74,673–139,407 | 450 | 610 (22020) | 7.44 | 0.87 | 3.77 | 1 | 4.19 | 3.22 | 0 / 0 |
| Go | 86,492 | 74,066–87,318 | 723 | 1330 (24500) | 11.62 | 0.96 | 3.78 | 1 | 15.55 | 8.84 | 0 / 0 |
| Bun | 92,972 | 47,250–95,478 | 685 | 1330 (14690) | 10.92 | 0.86 | 3.83 | 1 | 43.50 | 15.91 | 0 / 0 |

## smooth-1000-one-worker

Route `/smooth/1000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 28,650 | 27,155–28,835 | 2220 | 2450 (3440) | 34.99 | 0.99 | 3.48 | 1 | 3.20 | 2.64 | 0 / 0 |
| Neo (before) | 28,285 | 27,098–28,693 | 2240 | 4470 (4690) | 35.26 | 0.99 | 3.65 | 1 | 3.20 | 2.64 | 0 / 0 |
| Rust | 39,368 | 37,996–40,660 | 1650 | 1800 (6110) | 25.03 | 0.98 | 3.79 | 1 | 4.34 | 3.38 | 0 / 0 |
| Go | 17,440 | 16,855–17,594 | 3690 | 5770 (5880) | 57.64 | 1.00 | 3.12 | 1 | 16.06 | 9.33 | 0 / 0 |
| Bun | 9,189 | 8,706–9,257 | 6800 | 13360 (14180) | 110.38 | 1.00 | 3.82 | 1 | 47.22 | 19.17 | 0 / 0 |

## smooth-10000-one-worker

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 3,300 | 3,277–3,309 | 19260 | 19960 (20000) | 303.96 | 1.00 | 3.19 | 1 | 3.23 | 2.67 | 0 / 0 |
| Neo (before) | 3,265 | 3,250–3,290 | 19120 | 288420 (291710) | 306.40 | 1.00 | 3.29 | 1 | 3.23 | 2.67 | 0 / 0 |
| Rust | 4,832 | 4,734–4,874 | 13320 | 14390 (14590) | 207.52 | 1.00 | 3.34 | 1 | 4.66 | 3.69 | 0 / 0 |
| Go | 2,089 | 2,075–2,097 | 28540 | 96330 (100540) | 479.44 | 1.00 | 3.30 | 1 | 16.03 | 9.13 | 0 / 0 |
| Bun | 841 | 835–859 | 74630 | 80650 (95900) | 1185.69 | 1.00 | 3.85 | 1 | 61.53 | 23.78 | 0 / 0 |

## smooth-10000-default

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 24,761 | 24,628–24,843 | 1950 | 10000 (10300) | 351.18 | 8.67 | 1.11 | 10 | 6.64 | 6.20 | 0 / 0 |
| Neo (before) | 24,766 | 24,350–25,149 | 1970 | 10370 (11810) | 351.53 | 8.68 | 1.10 | 10 | 6.50 | 6.06 | 0 / 0 |
| Rust | 34,020 | 33,961–35,082 | 1810 | 3850 (11610) | 248.51 | 8.52 | 1.29 | 1 | 7.70 | 7.20 | 0 / 0 |
| Go | 10,730 | 10,268–10,854 | 6100 | 29310 (32780) | 654.06 | 6.93 | 2.10 | 1 | 33.73 | 24.75 | 0 / 0 |
| Bun | 847 | 842–849 | 74270 | 96960 (102660) | 1185.21 | 1.00 | 3.12 | 1 | 57.48 | 23.28 | 0 / 0 |

## nbody-default

Route `POST:/nbody`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs (worst run) | CPU µs/req | CPU cores used | Other cores | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Neo | 20,258 | 19,791–21,396 | 2300 | 16060 (36930) | 407.78 | 8.33 | 1.66 | 10 | 5.42 | 5.02 | 0 / 0 |
| Neo (before) | 21,481 | 21,445–21,654 | 2230 | 11420 (11650) | 408.75 | 8.78 | 1.07 | 10 | 5.33 | 4.88 | 0 / 0 |
| Rust | 16,563 | 16,035–16,568 | 3740 | 8810 (9400) | 539.42 | 8.82 | 0.95 | 1 | 6.06 | 5.11 | 0 / 0 |
| Go | 9,953 | 9,769–10,064 | 6560 | 37760 (44890) | 716.18 | 7.10 | 2.11 | 1 | 24.80 | 16.92 | 0 / 0 |
| Bun | 1,058 | 1,053–1,064 | 59920 | 64090 (67750) | 951.60 | 1.00 | 3.14 | 1 | 55.28 | 28.72 | 0 / 0 |

## Dependency boundary and limits

Neo allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Neo source, with compiler primitives for direct kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `bench/http/results/2026-11-03-012451-native`.
