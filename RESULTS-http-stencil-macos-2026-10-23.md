# HTTP benchmarks: Axon kernel runtime, multicore workers and batching

Measured 2026-10-23T21:37:38.383752+02:00. Apple M1 Pro; 10 logical CPUs; 16.00 GiB RAM; Darwin 27.0.0.

wrk wrk 4.2.0 [kqueue] Copyright (C) 2012 Will Glozer, 4 client threads, 3 measured runs of 5s after 2s warm-up. Client and server share this machine. Server order is shuffled with a recorded seed.

Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Axon runs one process per configured worker, with round-robin connection assignment, a dense connection vector, retained buffers and up to 64 responses per batch. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set AXON_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is macOS physical footprint. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks, not lifetime high-water marks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission.

Pipelined latency percentiles are omitted consistently across both platforms after the macOS wrk build emitted invalid/nonmonotonic values, including p99=0 µs despite millisecond average latency. Raw reported values and stdout are preserved. Pipeline throughput and CPU measurements use the request and CPU counters, not those percentiles.

Disk sizes below count the native executable, or the Bun executable plus this benchmark script. Shared OS libraries, compilers, SDKs, caches and deployment packaging are excluded. Startup is a warm-filesystem process-to-listening observation, not a cold-start benchmark.

Versions: Axon: Kernel syscall runtime, prefork HTTP workers + response batches; Clang: Apple clang version 21.0.0 (clang-2100.3.34.2); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 darwin/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle macOS physical footprint MiB | Startup ms |
|---|---:|---:|---:|---:|
| Axon | 0.06 | 2.66 | 2.47 | 9.7 |
| Rust | 0.91 | 2.36 | 1.50 | 9.9 |
| Go | 7.73 | 9.38 | 3.41 | 27.0 |
| Bun | 60.15 | 25.28 | 9.70 | 44.1 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 110,505 | 74,940–110,904 | 554 | 980 | 17.92 | 1.77 | 10 | 4.59 | 4.36 | 0 / 0 |
| Rust | 107,600 | 91,271–108,836 | 523 | 1510 | 19.67 | 2.01 | 1 | 4.84 | 4.03 | 0 / 0 |
| Go | 105,122 | 92,319–106,310 | 522 | 2960 | 32.83 | 3.31 | 1 | 19.86 | 13.28 | 0 / 0 |
| Bun | 72,679 | 71,070–75,537 | 835 | 1690 | 13.37 | 0.98 | 1 | 35.12 | 14.38 | 0 / 0 |

## hello-256

Route `/`; 256 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 108,045 | 103,356–111,278 | 2180 | 10300 | 27.62 | 2.96 | 10 | 8.22 | 8.20 | 0 / 0 |
| Rust | 114,493 | 102,377–115,193 | 2130 | 3500 | 20.79 | 2.29 | 1 | 13.81 | 13.97 | 0 / 0 |
| Go | 105,850 | 93,714–113,638 | 2060 | 11080 | 32.93 | 3.43 | 1 | 25.41 | 20.28 | 0 / 0 |
| Bun | 68,056 | 67,238–73,796 | 3590 | 8520 | 13.56 | 0.94 | 1 | 43.05 | 15.28 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 1,482,951 | 1,457,829–1,596,752 | n/a | n/a | 1.44 | 2.18 | 10 | 4.59 | 4.49 | 0 / 0 |
| Rust | 1,809,396 | 1,748,798–1,811,291 | n/a | n/a | 1.83 | 3.27 | 1 | 4.64 | 4.06 | 0 / 0 |
| Go | 256,286 | 246,309–271,232 | n/a | n/a | 16.64 | 4.28 | 1 | 23.59 | 16.25 | 0 / 0 |
| Bun | 14,838 | 13,928–14,971 | n/a | n/a | 65.50 | 0.95 | 1 | 43.47 | 15.39 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 107,142 | 104,623–109,567 | 603 | 1220 | 9.17 | 0.98 | 1 | 3.12 | 2.66 | 0 / 0 |
| Rust | 94,867 | 91,629–99,730 | 668 | 1400 | 9.95 | 0.95 | 1 | 3.34 | 3.19 | 0 / 0 |
| Go | 58,786 | 58,757–64,395 | 1030 | 3830 | 15.57 | 0.94 | 1 | 14.67 | 9.36 | 0 / 0 |
| Bun | 72,374 | 69,714–72,656 | 870 | 3570 | 13.48 | 0.96 | 1 | 44.05 | 15.41 | 0 / 0 |

## smooth-1000-one-worker

Route `/smooth/1000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 40,252 | 31,847–40,860 | 1570 | 2310 | 25.39 | 0.95 | 1 | 3.12 | 2.66 | 0 / 0 |
| Rust | 34,606 | 34,176–35,101 | 1860 | 2200 | 28.53 | 0.99 | 1 | 4.33 | 3.42 | 0 / 0 |
| Go | 16,125 | 15,709–16,285 | 4000 | 6310 | 61.97 | 0.99 | 1 | 15.94 | 9.38 | 0 / 0 |
| Bun | 8,323 | 8,005–8,636 | 7510 | 11210 | 118.68 | 0.99 | 1 | 45.80 | 18.39 | 0 / 0 |

## smooth-10000-one-worker

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 5,923 | 5,895–5,981 | 10490 | 84370 | 166.09 | 0.98 | 1 | 3.12 | 2.66 | 0 / 0 |
| Rust | 4,648 | 4,627–4,652 | 13780 | 19220 | 212.89 | 0.99 | 1 | 4.62 | 3.73 | 0 / 0 |
| Go | 2,070 | 2,065–2,071 | 29220 | 95890 | 482.56 | 1.00 | 1 | 16.06 | 9.48 | 0 / 0 |
| Bun | 814 | 740–815 | 76560 | 108420 | 1230.72 | 0.97 | 1 | 61.36 | 28.61 | 0 / 0 |

## smooth-10000-default

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 41,403 | 41,006–42,692 | 1160 | 10440 | 189.96 | 7.90 | 10 | 6.33 | 6.14 | 0 / 0 |
| Rust | 26,073 | 25,649–27,069 | 2260 | 9730 | 260.13 | 6.81 | 1 | 8.44 | 7.67 | 0 / 0 |
| Go | 9,682 | 9,365–9,753 | 6590 | 37610 | 685.31 | 6.57 | 1 | 33.05 | 23.98 | 0 / 0 |
| Bun | 829 | 816–839 | 75130 | 105730 | 1199.01 | 0.99 | 1 | 57.38 | 28.25 | 0 / 0 |

## nbody-default

Route `POST:/nbody`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | macOS physical footprint MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 19,678 | 19,620–19,691 | 2600 | 13400 | 402.34 | 7.89 | 10 | 5.02 | 4.81 | 0 / 0 |
| Rust | 14,478 | 13,472–16,056 | 4210 | 13140 | 541.11 | 7.92 | 1 | 5.38 | 4.66 | 0 / 0 |
| Go | 8,639 | 8,388–9,089 | 7650 | 41920 | 734.62 | 6.38 | 1 | 24.72 | 19.59 | 0 / 0 |
| Bun | 1,005 | 993–1,014 | 62220 | 80630 | 989.80 | 0.99 | 1 | 55.73 | 25.27 | 0 / 0 |

## Dependency boundary and limits

Axon allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Axon source, with compiler primitives for direct ARM64 kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `bench/http/results/2026-10-23-213738-native`.

## Reading this run

- This run tests bounded integer arithmetic in the compiler. Axon HTTP and runtime source files are unchanged from the preceding kernel-runtime report, and the Rust, Go and Bun source and executable hashes match that report. Each request still computes all 32 stencil passes; responses are not cached.
- The compiler infers a stencil dividend in [0, 4,000,008] and replaces remainder by 1,000,003 with two conditional subtractions using 32-bit arithmetic. This is a generic interval-based optimization, with conservative overflow/effect boundaries and signed fallback handling; AXON_RANGE=0 disables it.
- Axon’s median throughput beats the unchanged Rust server in all three stencil cases: 40,252 versus 34,606 requests/s for 1,000 elements with one worker (+16.3%); 5,923 versus 4,648 for 10,000 elements with one worker (+27.4%); and 41,403 versus 26,073 with default workers (+58.8%).
- The small single-worker stencil has overlapping sample ranges: one Axon sample was 31,847 requests/s, below Rust’s samples, while the other two were about 40 thousand. That variability is retained. The two large stencil cases have no overlap: Axon’s slowest sample exceeds Rust’s fastest.
- The large default-worker stencil used 189.96 versus Rust’s 260.13 CPU microseconds/request and 6.14 versus 7.67 MiB sampled peak physical footprint. The large single-worker case used 166.09 versus 212.89 CPU microseconds/request and 2.66 versus 3.73 MiB physical footprint.
- All 32 final comparisons and 96 measured runs are valid, with ten Axon worker processes in default mode and one in single-worker mode. CPU and memory count every worker.
- One original Axon hello-256 warm-up had 230 socket read and 80 write errors. Its three measured runs had zero errors, but the whole attempt was marked invalid. It is preserved under invalid_attempts and its original log files. One separate rerun with identical settings had zero warm-up or measured errors; the table uses that rerun, whose logs are under retry-hello-256-axon. No stencil case was retried.
- Other workloads are retained in the tables. In particular Rust led pipeline throughput in this run (1.81 versus Axon’s 1.48 million requests/s); these results do not imply Axon leads every workload.
- The Mac executable still imports no libc functions. Apple’s libSystem/dyld loader requirement remains; the separate Linux executable is fully static and passed HTTP inside an otherwise empty root filesystem. No runtime dependency or runtime source was added.
- All 28 unit tests, six compute examples with one and four workers, argument/refinement checks, HTTP protocol/concurrency/batching/backpressure checks with one and four workers, and 2,080 optimized/unoptimized signed/overflow/tail cases passed. Logs and the build report are included beside measurements.json.
- The test VM was stopped for this native M1 Pro run. Client and server share the Mac; these short saturation measurements are implementation comparisons and do not measure electrical energy or establish universal language rankings. Linux VM throughput is a separate environment.
