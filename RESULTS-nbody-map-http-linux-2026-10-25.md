# HTTP benchmarks: Axon kernel runtime, multicore workers and batching

Measured 2026-10-25T09:16:18.146351+01:00. aarch64 Linux VM; 8 logical CPUs; 5.77 GiB RAM; Linux 6.8.0-64-generic.

wrk wrk debian/4.1.0-4build2 [epoll] Copyright (C) 2012 Will Glozer, 4 client threads, 3 measured runs of 3s after 1s warm-up. Client and server share this machine. Server order is shuffled with a recorded seed.

Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Axon runs one process per configured worker, with round-robin connection assignment, a dense connection vector, retained buffers and up to 64 responses per batch. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set AXON_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is Linux PSS. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks, not lifetime high-water marks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission.

Pipelined latency percentiles are omitted consistently across both platforms after the macOS wrk build emitted invalid/nonmonotonic values, including p99=0 µs despite millisecond average latency. Raw reported values and stdout are preserved. Pipeline throughput and CPU measurements use the request and CPU counters, not those percentiles.

Disk sizes below count the native executable, or the Bun executable plus this benchmark script. Shared OS libraries, compilers, SDKs, caches and deployment packaging are excluded. Startup is a warm-filesystem process-to-listening observation, not a cold-start benchmark.

Versions: Axon: Kernel syscall runtime, prefork HTTP workers + response batches; Clang: Ubuntu clang version 18.1.3 (1ubuntu1); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 linux/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle Linux PSS MiB | Startup ms |
|---|---:|---:|---:|---:|
| Axon | 0.05 | 0.57 | 0.21 | 6.1 |
| Rust | 1.02 | 2.43 | 1.43 | 6.5 |
| Go | 7.65 | 6.37 | 5.50 | 14.0 |
| Bun | 96.62 | 36.99 | 35.84 | 34.3 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 285,551 | 231,685–392,704 | 117 | 23520 | 8.52 | 2.58 | 8 | 1.30 | 0.92 | 0 / 0 |
| Rust | 262,111 | 247,876–273,826 | 197 | 6720 | 8.06 | 2.10 | 1 | 5.20 | 4.07 | 0 / 0 |
| Go | 226,942 | 202,320–280,318 | 188 | 3150 | 16.87 | 3.98 | 1 | 15.32 | 14.38 | 0 / 0 |
| Bun | 68,997 | 29,790–69,922 | 694 | 51300 | 16.40 | 0.92 | 1 | 55.65 | 54.43 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 4,895,148 | 4,162,066–4,994,621 | n/a | n/a | 0.59 | 2.76 | 8 | 1.31 | 0.93 | 0 / 0 |
| Rust | 2,856,719 | 2,666,544–2,929,316 | n/a | n/a | 0.96 | 2.71 | 1 | 5.28 | 4.15 | 0 / 0 |
| Go | 307,930 | 291,320–374,088 | n/a | n/a | 13.69 | 4.41 | 1 | 16.14 | 15.20 | 0 / 0 |
| Bun | 22,187 | 20,651–23,481 | n/a | n/a | 46.57 | 1.03 | 1 | 56.19 | 54.92 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 219,064 | 218,343–222,975 | 271 | 673 | 4.53 | 1.00 | 1 | 0.79 | 0.79 | 0 / 0 |
| Rust | 195,201 | 194,007–202,972 | 329 | 497 | 5.05 | 1.00 | 1 | 3.38 | 2.25 | 0 / 0 |
| Go | 71,543 | 70,864–80,703 | 880 | 7610 | 13.22 | 0.98 | 1 | 12.40 | 11.45 | 0 / 0 |
| Bun | 92,458 | 86,895–96,351 | 621 | 2200 | 11.62 | 1.07 | 1 | 55.02 | 53.88 | 0 / 0 |

## Dependency boundary and limits

Axon allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Axon source, with compiler primitives for direct ARM64 kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `/axon/bench/http/results/2026-10-25-091618-native`.
