# HTTP benchmarks: Axon kernel runtime, multicore workers and batching

Measured 2026-10-24T20:16:17.543778+02:00. aarch64 Linux VM; 8 logical CPUs; 5.77 GiB RAM; Linux 6.8.0-64-generic.

wrk wrk debian/4.1.0-4build2 [epoll] Copyright (C) 2012 Will Glozer, 4 client threads, 3 measured runs of 3s after 1s warm-up. Client and server share this machine. Server order is shuffled with a recorded seed.

Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Axon runs one process per configured worker, with round-robin connection assignment, a dense connection vector, retained buffers and up to 64 responses per batch. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set AXON_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is Linux PSS. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks, not lifetime high-water marks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission.

Pipelined latency percentiles are omitted consistently across both platforms after the macOS wrk build emitted invalid/nonmonotonic values, including p99=0 µs despite millisecond average latency. Raw reported values and stdout are preserved. Pipeline throughput and CPU measurements use the request and CPU counters, not those percentiles.

Disk sizes below count the native executable, or the Bun executable plus this benchmark script. Shared OS libraries, compilers, SDKs, caches and deployment packaging are excluded. Startup is a warm-filesystem process-to-listening observation, not a cold-start benchmark.

Versions: Axon: Kernel syscall runtime, prefork HTTP workers + response batches; Clang: Ubuntu clang version 18.1.3 (1ubuntu1); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 linux/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle Linux PSS MiB | Startup ms |
|---|---:|---:|---:|---:|
| Axon | 0.05 | 0.57 | 0.21 | 6.4 |
| Rust | 1.02 | 2.44 | 1.56 | 6.5 |
| Go | 7.65 | 6.39 | 5.63 | 17.0 |
| Bun | 96.62 | 36.98 | 35.97 | 27.6 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 568,158 | 567,065–574,526 | 65 | 1510 | 5.64 | 3.21 | 8 | 1.30 | 0.92 | 0 / 0 |
| Rust | 285,289 | 269,743–287,645 | 186 | 567 | 7.43 | 2.08 | 1 | 5.61 | 4.55 | 0 / 0 |
| Go | 298,828 | 294,889–304,891 | 136 | 2000 | 14.71 | 4.40 | 1 | 15.29 | 14.41 | 0 / 0 |
| Bun | 95,567 | 94,107–97,752 | 593 | 2170 | 11.32 | 1.08 | 1 | 55.09 | 53.90 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 6,077,457 | 5,888,179–6,112,661 | n/a | n/a | 0.52 | 3.12 | 8 | 1.28 | 0.92 | 0 / 0 |
| Rust | 3,324,262 | 3,283,976–3,364,820 | n/a | n/a | 0.90 | 2.98 | 1 | 4.79 | 3.73 | 0 / 0 |
| Go | 441,679 | 383,141–447,805 | n/a | n/a | 11.20 | 4.73 | 1 | 18.26 | 17.39 | 0 / 0 |
| Bun | 27,653 | 27,472–27,882 | n/a | n/a | 37.30 | 1.03 | 1 | 55.19 | 54.00 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 218,465 | 215,866–223,980 | 279 | 667 | 4.56 | 1.00 | 1 | 0.78 | 0.78 | 0 / 0 |
| Rust | 217,477 | 209,641–224,619 | 273 | 446 | 4.61 | 1.00 | 1 | 3.35 | 2.29 | 0 / 0 |
| Go | 91,179 | 90,612–91,753 | 693 | 1560 | 10.99 | 1.00 | 1 | 12.46 | 11.58 | 0 / 0 |
| Bun | 104,538 | 102,708–106,418 | 559 | 1840 | 10.17 | 1.06 | 1 | 55.55 | 54.37 | 0 / 0 |

## Dependency boundary and limits

Axon allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Axon source, with compiler primitives for direct ARM64 kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `/axon/bench/http/results/2026-10-24-201617-native`.
