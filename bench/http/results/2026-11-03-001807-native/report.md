# HTTP benchmarks: Axon kernel runtime, multicore workers and batching

Measured 2026-11-03T00:18:07.326703+01:00. Apple M1 Pro; 10 logical CPUs; 16.00 GiB RAM; Darwin 27.2.0.

wrk wrk 4.2.0 [kqueue] Copyright (C) 2012 Will Glozer, 4 client threads, 3 measured runs of 5s after 2s warm-up. Client and server share this machine. Server order is shuffled with a recorded seed.

Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Axon runs one process per configured worker, with round-robin connection assignment, a dense connection vector, retained buffers and up to 64 responses per batch. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set NEO_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is macOS physical footprint. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks, not lifetime high-water marks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission.

Pipelined latency percentiles are omitted consistently across both platforms after the macOS wrk build emitted invalid/nonmonotonic values, including p99=0 µs despite millisecond average latency. Raw reported values and stdout are preserved. Pipeline throughput and CPU measurements use the request and CPU counters, not those percentiles.

Disk sizes below count the native executable, or the Bun executable plus this benchmark script. Shared OS libraries, compilers, SDKs, caches and deployment packaging are excluded. Startup is a warm-filesystem process-to-listening observation, not a cold-start benchmark.

Versions: Axon: Kernel syscall runtime, prefork HTTP workers + response batches; Clang: Apple clang version 21.0.0 (clang-2100.4.1.1); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 darwin/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle macOS physical footprint MiB | Startup ms |
|---|---:|---:|---:|---:|
| Axon | 0.08 | 2.72 | 2.45 | 9.5 |
| Rust | 0.91 | 2.40 | 1.47 | 9.1 |
| Go | 7.73 | 9.70 | 3.54 | 35.1 |
| Bun | 60.15 | 25.41 | 9.73 | 96.6 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 136,405 | 127,160–140,589 | 364 | 4550 | 16.48 | 2.21 | 10 | 4.55 | 4.59 | 0 / 0 |
| Rust | 144,954 | 139,427–153,711 | 375 | 1370 | 19.83 | 2.89 | 1 | 4.69 | 3.70 | 0 / 0 |
| Go | 124,258 | 117,853–127,714 | 312 | 8820 | 25.79 | 3.17 | 1 | 21.12 | 14.97 | 0 / 0 |
| Bun | 76,082 | 75,081–84,971 | 740 | 4770 | 11.90 | 0.93 | 1 | 34.39 | 14.92 | 0 / 0 |

## hello-256

Route `/`; 256 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon (INVALID) | 152,845 | 150,015–158,088 | 1180 | 5790 | 19.83 | 3.04 | 10 | 8.31 | 8.36 | 21 / 0 |
| Rust | 150,661 | 149,964–154,882 | 1210 | 3790 | 18.47 | 2.80 | 1 | 21.94 | 20.52 | 0 / 0 |
| Go | 137,213 | 131,493–137,505 | 1100 | 7820 | 24.83 | 3.35 | 1 | 26.36 | 18.41 | 0 / 0 |
| Bun | 88,529 | 87,633–88,914 | 2810 | 6700 | 10.99 | 0.97 | 1 | 45.03 | 16.34 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 1,935,858 | 1,874,549–2,129,953 | n/a | n/a | 1.07 | 2.10 | 10 | 3.69 | 4.34 | 0 / 0 |
| Rust | 1,675,837 | 1,209,995–1,750,436 | n/a | n/a | 1.49 | 2.29 | 1 | 4.34 | 3.94 | 0 / 0 |
| Go | 266,971 | 255,316–282,726 | n/a | n/a | 14.97 | 4.00 | 1 | 24.09 | 15.77 | 0 / 0 |
| Bun | 15,435 | 15,242–18,606 | n/a | n/a | 53.62 | 0.88 | 1 | 33.91 | 14.86 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 102,309 | 89,540–109,694 | 513 | 18570 | 8.03 | 0.80 | 1 | 2.28 | 2.64 | 0 / 0 |
| Rust | 91,957 | 89,729–100,808 | 578 | 10590 | 8.77 | 0.82 | 1 | 3.59 | 3.11 | 0 / 0 |
| Go | 71,351 | 68,546–74,489 | 842 | 4480 | 13.06 | 0.93 | 1 | 14.97 | 9.67 | 0 / 0 |
| Bun | 85,631 | 78,226–85,667 | 724 | 4140 | 11.51 | 0.95 | 1 | 35.59 | 15.47 | 0 / 0 |

## smooth-1000-one-worker

Route `/smooth/1000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 25,185 | 23,534–26,384 | 2380 | 7400 | 37.83 | 0.95 | 1 | 3.19 | 2.63 | 0 / 0 |
| Rust | 37,238 | 34,702–38,014 | 1720 | 2470 | 26.77 | 0.98 | 1 | 3.52 | 3.28 | 0 / 0 |
| Go | 15,906 | 14,567–16,243 | 4070 | 6870 | 62.42 | 0.97 | 1 | 15.44 | 9.38 | 0 / 0 |
| Bun | 7,913 | 7,889–8,104 | 7540 | 18410 | 120.13 | 0.95 | 1 | 43.78 | 18.25 | 0 / 0 |

## smooth-10000-one-worker

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 3,170 | 2,966–3,189 | 19520 | 299090 | 314.70 | 0.98 | 1 | 3.23 | 2.67 | 0 / 0 |
| Rust | 4,519 | 4,439–4,579 | 13950 | 20140 | 216.38 | 0.97 | 1 | 3.95 | 3.63 | 0 / 0 |
| Go | 2,055 | 1,987–2,088 | 29630 | 92900 | 484.68 | 0.99 | 1 | 15.03 | 9.39 | 0 / 0 |
| Bun | 780 | 775–790 | 77970 | 121980 | 1248.97 | 0.97 | 1 | 57.92 | 35.45 | 0 / 0 |

## smooth-10000-default

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 20,752 | 20,318–21,698 | 2200 | 31040 | 340.24 | 7.10 | 10 | 6.45 | 6.06 | 0 / 0 |
| Rust | 30,187 | 30,076–30,505 | 2050 | 8480 | 239.34 | 7.22 | 1 | 8.11 | 6.44 | 0 / 0 |
| Go | 9,249 | 8,857–9,356 | 6670 | 35440 | 621.33 | 5.67 | 1 | 32.28 | 24.31 | 0 / 0 |
| Bun | 818 | 791–829 | 76480 | 106070 | 1221.53 | 0.99 | 1 | 62.17 | 35.70 | 0 / 0 |

## nbody-default

Route `POST:/nbody`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 18,785 | 16,482–20,088 | 2690 | 17110 | 398.97 | 7.33 | 10 | 5.38 | 5.00 | 0 / 0 |
| Rust | 13,915 | 11,647–14,144 | 4370 | 14250 | 526.86 | 6.95 | 1 | 9.97 | 9.05 | 0 / 0 |
| Go | 8,883 | 8,866–8,942 | 7060 | 42140 | 670.22 | 5.95 | 1 | 24.41 | 16.56 | 0 / 0 |
| Bun | 988 | 803–1,018 | 61440 | 150670 | 990.77 | 0.92 | 1 | 48.89 | 28.94 | 0 / 0 |

## Dependency boundary and limits

Axon allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Axon source, with compiler primitives for direct ARM64 kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `bench/http/results/2026-11-03-001807-native`.
