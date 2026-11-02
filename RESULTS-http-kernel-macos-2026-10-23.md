# HTTP benchmarks: Axon kernel runtime, multicore workers and batching

Measured 2026-10-23T19:52:16.392337+02:00. Apple M1 Pro; 10 logical CPUs; 16.00 GiB RAM; Darwin 27.0.0.

wrk wrk 4.2.0 [kqueue] Copyright (C) 2012 Will Glozer, 4 client threads, 3 measured runs of 5s after 2s warm-up. Client and server share this machine. Server order is shuffled with a recorded seed.

Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Axon runs one process per configured worker, with round-robin connection assignment, a dense connection vector, retained buffers and up to 64 responses per batch. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set AXON_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is macOS physical footprint. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks, not lifetime high-water marks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission.

Pipelined latency percentiles are omitted consistently across both platforms after the macOS wrk build emitted invalid/nonmonotonic values, including p99=0 µs despite millisecond average latency. Raw reported values and stdout are preserved. Pipeline throughput and CPU measurements use the request and CPU counters, not those percentiles.

Disk sizes below count the native executable, or the Bun executable plus this benchmark script. Shared OS libraries, compilers, SDKs, caches and deployment packaging are excluded. Startup is a warm-filesystem process-to-listening observation, not a cold-start benchmark.

Versions: Axon: Kernel syscall runtime, prefork HTTP workers + response batches; Clang: Apple clang version 21.0.0 (clang-2100.3.34.2); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 darwin/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle macOS physical footprint MiB | Startup ms |
|---|---:|---:|---:|---:|
| Axon | 0.06 | 2.67 | 2.49 | 8.8 |
| Rust | 0.91 | 2.36 | 1.50 | 9.0 |
| Go | 7.73 | 9.38 | 3.40 | 19.7 |
| Bun | 60.15 | 25.28 | 9.68 | 26.5 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 120,079 | 119,984–120,173 | 511 | 693 | 17.28 | 2.07 | 10 | 4.66 | 4.42 | 0 / 0 |
| Rust | 126,693 | 126,335–128,373 | 475 | 704 | 17.60 | 2.23 | 1 | 4.66 | 3.77 | 0 / 0 |
| Go | 115,912 | 113,977–115,980 | 515 | 1200 | 37.76 | 4.35 | 1 | 21.61 | 14.61 | 0 / 0 |
| Bun | 75,467 | 69,238–76,835 | 807 | 1640 | 13.08 | 0.96 | 1 | 42.09 | 14.28 | 0 / 0 |

## hello-256

Route `/`; 256 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 120,058 | 120,024–120,154 | 2070 | 2520 | 30.02 | 3.60 | 10 | 8.47 | 8.27 | 0 / 0 |
| Rust | 128,966 | 126,563–130,907 | 1920 | 2460 | 18.08 | 2.32 | 1 | 11.67 | 10.78 | 0 / 0 |
| Go | 117,772 | 113,746–120,234 | 2080 | 3600 | 35.65 | 4.17 | 1 | 25.70 | 17.77 | 0 / 0 |
| Bun | 79,762 | 79,619–80,423 | 3230 | 3720 | 12.42 | 0.99 | 1 | 42.88 | 15.02 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 1,816,549 | 1,807,914–1,816,883 | n/a | n/a | 1.31 | 2.37 | 10 | 4.66 | 4.42 | 0 / 0 |
| Rust | 1,920,996 | 1,914,989–1,924,697 | n/a | n/a | 1.67 | 3.19 | 1 | 4.97 | 4.08 | 0 / 0 |
| Go | 306,324 | 303,817–309,967 | n/a | n/a | 16.25 | 4.97 | 1 | 24.97 | 14.20 | 0 / 0 |
| Bun | 19,078 | 18,423–19,694 | n/a | n/a | 51.36 | 0.98 | 1 | 42.72 | 14.42 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 119,730 | 119,643–120,655 | 534 | 1020 | 8.21 | 0.98 | 1 | 3.14 | 2.67 | 0 / 0 |
| Rust | 109,971 | 109,743–110,393 | 595 | 742 | 8.86 | 0.97 | 1 | 4.09 | 3.19 | 0 / 0 |
| Go | 70,811 | 70,289–71,640 | 900 | 1510 | 13.87 | 0.98 | 1 | 15.48 | 8.97 | 0 / 0 |
| Bun | 76,422 | 69,909–76,480 | 804 | 1600 | 13.13 | 0.97 | 1 | 42.03 | 14.28 | 0 / 0 |

## smooth-1000-one-worker

Route `/smooth/1000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 36,547 | 36,207–37,592 | 1700 | 3300 | 26.71 | 0.98 | 1 | 3.14 | 2.67 | 0 / 0 |
| Rust | 34,230 | 30,699–35,540 | 1850 | 2370 | 28.57 | 0.96 | 1 | 4.36 | 3.45 | 0 / 0 |
| Go | 16,303 | 16,266–16,628 | 3950 | 6310 | 60.33 | 0.99 | 1 | 15.92 | 9.33 | 0 / 0 |
| Bun | 8,630 | 8,493–8,721 | 7270 | 14040 | 114.89 | 0.99 | 1 | 45.91 | 18.55 | 0 / 0 |

## smooth-10000-one-worker

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 4,909 | 4,882–4,978 | 12740 | 128580 | 201.89 | 0.99 | 1 | 3.14 | 2.67 | 0 / 0 |
| Rust | 4,798 | 4,779–4,805 | 13500 | 14250 | 207.38 | 0.99 | 1 | 4.59 | 3.70 | 0 / 0 |
| Go | 2,132 | 2,112–2,140 | 28400 | 86880 | 469.67 | 1.00 | 1 | 15.88 | 9.23 | 0 / 0 |
| Bun | 857 | 854–860 | 73380 | 103410 | 1167.75 | 1.00 | 1 | 60.61 | 21.09 | 0 / 0 |

## smooth-10000-default

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 34,369 | 33,957–34,673 | 1390 | 9930 | 232.03 | 7.95 | 10 | 6.20 | 6.02 | 0 / 0 |
| Rust | 30,145 | 25,562–32,285 | 2070 | 7050 | 246.83 | 7.22 | 1 | 8.34 | 7.48 | 0 / 0 |
| Go | 10,544 | 10,470–10,606 | 6180 | 30070 | 669.19 | 7.04 | 1 | 35.28 | 24.05 | 0 / 0 |
| Bun | 850 | 848–853 | 73980 | 99760 | 1177.31 | 1.00 | 1 | 64.45 | 25.08 | 0 / 0 |

## nbody-default

Route `POST:/nbody`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 20,132 | 17,480–20,610 | 2450 | 13590 | 404.73 | 7.84 | 10 | 4.94 | 5.03 | 0 / 0 |
| Rust | 14,472 | 11,303–15,984 | 4180 | 12120 | 529.10 | 7.34 | 1 | 5.45 | 4.59 | 0 / 0 |
| Go | 10,107 | 10,096–10,119 | 6050 | 36720 | 708.94 | 7.15 | 1 | 27.33 | 18.22 | 0 / 0 |
| Bun | 1,058 | 1,049–1,063 | 59650 | 71790 | 948.28 | 1.00 | 1 | 57.05 | 27.66 | 0 / 0 |

## Dependency boundary and limits

Axon allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Axon source, with compiler primitives for direct ARM64 kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `bench/http/results/2026-10-23-195216-native`.

## Reading this run

- All 32 comparisons and 96 measured runs completed with zero socket errors or non-2xx responses. Every Axon sample contains ten processes in default mode and one in single-worker mode; CPU and memory include them all.
- Pipelining reached 1.82 million requests/s versus Rust’s 1.92 million, using 1.31 versus 1.67 CPU microseconds/request. That is about 5.9 times the intermediate Axon runtime’s 308 thousand requests/s; the historical comparison is a separate run, not a controlled A/B experiment.
- The large stencil workload reached 34.4 thousand requests/s (Rust 30.1 thousand, Go 10.5 thousand, Bun 850). N-body reached 20.1 thousand (Rust 14.5 thousand, Go 10.1 thousand, Bun 1.1 thousand). Both Axon results are about seven times the intermediate single-worker runtime.
- These improvements do not cover every case: with 256 ordinary hello connections, Axon used 30.0 CPU microseconds/request versus Rust’s 18.1 and had lower throughput. Worker coordination has a cost.
- The single-worker large stencil result was 4,909 versus Rust’s 4,798 requests/s, a small gap that should not be generalized to whole languages. Sampled physical footprint was 2.67 versus 3.70 MiB.
- The 68,000-byte Mac Axon executable has zero undefined function imports, but Apple still requires libSystem/dyld to load it. The separate static Linux executable passed the full HTTP suite inside an otherwise empty filesystem.
- Three short samples on a shared laptop describe these implementations and workloads. They do not measure production capacity or electrical energy.
- Kernel-runtime and all six compute-example regression logs are included beside measurements.json, with one- and four-worker checks. The final Mac HTTP executable also passed the protocol smoke suite with one and four workers.
