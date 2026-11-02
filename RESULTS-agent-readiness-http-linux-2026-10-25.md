# HTTP benchmarks: Axon kernel runtime, multicore workers and batching

Measured 2026-10-25T10:44:06.013210+01:00. aarch64 Linux VM; 8 logical CPUs; 5.77 GiB RAM; Linux 6.8.0-64-generic.

wrk wrk debian/4.1.0-4build2 [epoll] Copyright (C) 2012 Will Glozer, 4 client threads, 3 measured runs of 3s after 2s warm-up. Client and server share this machine. Server order is shuffled with a recorded seed.

Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Axon runs one process per configured worker, with round-robin connection assignment, a dense connection vector, retained buffers and up to 64 responses per batch. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set AXON_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is Linux PSS. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks, not lifetime high-water marks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission.

Pipelined latency percentiles are omitted consistently across both platforms after the macOS wrk build emitted invalid/nonmonotonic values, including p99=0 µs despite millisecond average latency. Raw reported values and stdout are preserved. Pipeline throughput and CPU measurements use the request and CPU counters, not those percentiles.

Disk sizes below count the native executable, or the Bun executable plus this benchmark script. Shared OS libraries, compilers, SDKs, caches and deployment packaging are excluded. Startup is a warm-filesystem process-to-listening observation, not a cold-start benchmark.

Versions: Axon: Kernel syscall runtime, prefork HTTP workers + response batches; Clang: Ubuntu clang version 18.1.3 (1ubuntu1); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 linux/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle Linux PSS MiB | Startup ms |
|---|---:|---:|---:|---:|
| Axon | 0.05 | 0.60 | 0.22 | 6.3 |
| Rust | 1.02 | 2.44 | 1.39 | 6.1 |
| Go | 7.65 | 6.39 | 5.51 | 18.4 |
| Bun | 96.62 | 36.99 | 35.81 | 27.7 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 570,432 | 564,467–587,919 | 66 | 1860 | 5.56 | 3.18 | 8 | 1.33 | 0.92 | 0 / 0 |
| Rust | 261,397 | 231,608–271,601 | 199 | 3460 | 8.36 | 2.13 | 1 | 5.06 | 3.90 | 0 / 0 |
| Go | 284,734 | 256,491–285,840 | 144 | 1970 | 15.53 | 4.27 | 1 | 15.61 | 14.66 | 0 / 0 |
| Bun | 97,967 | 97,036–103,990 | 594 | 1800 | 10.66 | 1.06 | 1 | 54.42 | 53.13 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 5,841,856 | 4,861,961–5,950,375 | n/a | n/a | 0.54 | 2.99 | 8 | 1.33 | 0.92 | 0 / 0 |
| Rust | 3,043,917 | 2,558,216–3,102,268 | n/a | n/a | 0.97 | 2.80 | 1 | 4.93 | 3.77 | 0 / 0 |
| Go | 337,063 | 326,450–392,952 | n/a | n/a | 12.45 | 4.36 | 1 | 19.64 | 18.69 | 0 / 0 |
| Bun | 23,615 | 23,561–23,796 | n/a | n/a | 43.49 | 1.03 | 1 | 54.20 | 52.90 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 211,361 | 207,210–219,270 | 287 | 673 | 4.68 | 0.99 | 1 | 0.79 | 0.79 | 0 / 0 |
| Rust | 190,524 | 187,817–191,271 | 340 | 476 | 5.27 | 1.00 | 1 | 3.40 | 2.25 | 0 / 0 |
| Go | 85,644 | 80,800–86,183 | 747 | 1630 | 11.86 | 1.00 | 1 | 12.46 | 11.52 | 0 / 0 |
| Bun | 87,716 | 83,416–92,136 | 663 | 2060 | 12.09 | 1.06 | 1 | 55.01 | 53.73 | 0 / 0 |

## Dependency boundary and limits

Axon allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Axon source, with compiler primitives for direct ARM64 kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `/axon/bench/http/results/2026-10-25-104406-native`.
