# HTTP benchmarks: Axon kernel runtime, multicore workers and batching

Measured 2026-10-23T20:08:14.334700+02:00. aarch64 Linux VM; 8 logical CPUs; 5.77 GiB RAM; Linux 6.8.0-64-generic.

wrk wrk debian/4.1.0-4build2 [epoll] Copyright (C) 2012 Will Glozer, 4 client threads, 3 measured runs of 5s after 2s warm-up. Client and server share this machine. Server order is shuffled with a recorded seed.

Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Axon runs one process per configured worker, with round-robin connection assignment, a dense connection vector, retained buffers and up to 64 responses per batch. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set AXON_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is Linux PSS. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks, not lifetime high-water marks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission.

Pipelined latency percentiles are omitted consistently across both platforms after the macOS wrk build emitted invalid/nonmonotonic values, including p99=0 µs despite millisecond average latency. Raw reported values and stdout are preserved. Pipeline throughput and CPU measurements use the request and CPU counters, not those percentiles.

Disk sizes below count the native executable, or the Bun executable plus this benchmark script. Shared OS libraries, compilers, SDKs, caches and deployment packaging are excluded. Startup is a warm-filesystem process-to-listening observation, not a cold-start benchmark.

Versions: Axon: Kernel syscall runtime, prefork HTTP workers + response batches; Clang: Ubuntu clang version 18.1.3 (1ubuntu1); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 linux/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle Linux PSS MiB | Startup ms |
|---|---:|---:|---:|---:|
| Axon | 0.04 | 0.48 | 0.17 | 6.1 |
| Rust | 1.02 | 2.43 | 1.56 | 6.3 |
| Go | 7.65 | 6.38 | 5.62 | 12.5 |
| Bun | 96.62 | 36.98 | 35.97 | 19.4 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 522,833 | 503,159–617,628 | 71 | 2110 | 5.97 | 3.27 | 8 | 1.17 | 0.87 | 0 / 0 |
| Rust | 249,410 | 241,939–283,880 | 210 | 2060 | 7.86 | 2.03 | 1 | 5.34 | 4.28 | 0 / 0 |
| Go | 255,198 | 216,936–288,556 | 168 | 2110 | 16.32 | 4.13 | 1 | 15.78 | 14.91 | 0 / 0 |
| Bun | 100,129 | 97,981–100,194 | 576 | 1810 | 10.63 | 1.06 | 1 | 54.33 | 53.15 | 0 / 0 |

## hello-256

Route `/`; 256 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 693,045 | 689,238–732,819 | 169 | 2860 | 5.40 | 3.80 | 8 | 2.67 | 2.37 | 0 / 0 |
| Rust | 540,359 | 534,150–554,000 | 367 | 1790 | 6.23 | 3.38 | 1 | 11.46 | 10.40 | 0 / 0 |
| Go | 320,800 | 320,297–321,459 | 499 | 5250 | 14.31 | 4.58 | 1 | 20.47 | 19.59 | 0 / 0 |
| Bun | 83,278 | 81,288–89,564 | 2740 | 5490 | 12.28 | 1.03 | 1 | 54.57 | 53.39 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 6,033,100 | 5,989,037–6,399,210 | n/a | n/a | 0.54 | 3.30 | 8 | 1.17 | 0.87 | 0 / 0 |
| Rust | 3,052,357 | 3,007,314–3,093,286 | n/a | n/a | 0.89 | 2.72 | 1 | 5.13 | 4.07 | 0 / 0 |
| Go | 465,195 | 463,709–466,816 | n/a | n/a | 10.43 | 4.84 | 1 | 17.57 | 16.68 | 0 / 0 |
| Bun | 26,495 | 26,325–27,493 | n/a | n/a | 38.38 | 1.03 | 1 | 54.81 | 53.63 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 257,106 | 211,998–267,449 | 249 | 564 | 4.07 | 1.00 | 1 | 0.77 | 0.77 | 0 / 0 |
| Rust | 201,425 | 201,012–203,383 | 324 | 446 | 4.95 | 1.00 | 1 | 3.38 | 2.32 | 0 / 0 |
| Go | 91,501 | 88,589–93,099 | 695 | 1560 | 11.00 | 1.00 | 1 | 12.14 | 11.27 | 0 / 0 |
| Bun | 101,618 | 100,000–105,093 | 568 | 1750 | 10.38 | 1.06 | 1 | 54.39 | 53.20 | 0 / 0 |

## smooth-1000-one-worker

Route `/smooth/1000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 31,892 | 31,681–31,995 | 1970 | 3930 | 31.41 | 1.00 | 1 | 0.77 | 0.77 | 0 / 0 |
| Rust | 34,027 | 33,933–34,247 | 1910 | 2160 | 29.33 | 1.00 | 1 | 3.50 | 2.45 | 0 / 0 |
| Go | 14,982 | 13,848–15,267 | 4270 | 8830 | 68.29 | 1.00 | 1 | 12.59 | 11.77 | 0 / 0 |
| Bun | 9,344 | 9,186–9,366 | 6600 | 12820 | 111.11 | 1.03 | 1 | 59.09 | 57.90 | 0 / 0 |

## smooth-10000-one-worker

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 4,077 | 4,040–4,079 | 15390 | 183490 | 246.11 | 1.00 | 1 | 0.77 | 0.77 | 0 / 0 |
| Rust | 4,332 | 4,328–4,337 | 14950 | 16090 | 230.97 | 1.00 | 1 | 3.65 | 2.62 | 0 / 0 |
| Go | 2,058 | 2,057–2,062 | 30400 | 92240 | 486.83 | 1.00 | 1 | 12.46 | 11.59 | 0 / 0 |
| Bun | 1,067 | 1,061–1,086 | 58690 | 113570 | 955.73 | 1.02 | 1 | 68.08 | 66.90 | 0 / 0 |

## smooth-10000-default

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 28,574 | 27,539–29,164 | 2020 | 6120 | 266.09 | 7.56 | 8 | 2.30 | 1.97 | 0 / 0 |
| Rust | 31,859 | 31,348–31,884 | 1970 | 4540 | 241.64 | 7.65 | 1 | 6.32 | 5.27 | 0 / 0 |
| Go | 9,025 | 8,949–9,077 | 8090 | 32940 | 637.94 | 5.75 | 1 | 21.38 | 20.51 | 0 / 0 |
| Bun | 1,060 | 1,049–1,072 | 59020 | 115630 | 963.43 | 1.02 | 1 | 67.11 | 65.94 | 0 / 0 |

## nbody-default

Route `POST:/nbody`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 19,906 | 19,486–20,484 | 2880 | 7950 | 387.16 | 7.68 | 8 | 1.42 | 1.12 | 0 / 0 |
| Rust | 15,076 | 11,789–16,286 | 4030 | 12830 | 537.95 | 7.72 | 1 | 5.20 | 4.14 | 0 / 0 |
| Go | 8,910 | 8,797–8,911 | 7740 | 37510 | 660.83 | 5.85 | 1 | 18.20 | 17.32 | 0 / 0 |
| Bun | 1,021 | 1,016–1,026 | 61070 | 120280 | 1001.03 | 1.02 | 1 | 65.20 | 64.02 | 0 / 0 |

## Dependency boundary and limits

Axon allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Axon source, with compiler primitives for direct ARM64 kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `/axon/bench/http/results/2026-10-23-200814-native`.

## Reading this run

- All 32 comparisons and 96 measured runs completed with zero socket errors or non-2xx responses. Every Axon sample contains eight processes in default mode and one in single-worker mode. CPU and memory include every worker.
- This is ARM64 Ubuntu in a Colima VZ VM with eight virtual CPUs and 6 GiB configured RAM on the Apple M1 Pro host. The load generator shares the VM. These numbers must not be compared directly with native Mac absolute throughput.
- Axon handled 523 thousand requests/s with 64 ordinary hello connections and 693 thousand with 256, versus Rust’s 249 thousand and 540 thousand. The single-worker hello result was 257 thousand versus Rust’s 201 thousand.
- At pipeline depth 16, Axon reached 6.03 million requests/s versus Rust’s 3.05 million, Go’s 465 thousand and Bun’s 26.5 thousand. CPU cost was 0.54 versus Rust’s 0.89 microseconds/request. Sampled peak PSS was 0.87 versus 4.07 MiB.
- Rust led both single-worker stencil cases: 34,027 versus Axon’s 31,892 requests/s at 1,000 elements, and 4,332 versus 4,077 at 10,000. On the large default-worker stencil, Rust also led, 31,859 versus 28,574. Axon used 1.97 versus 5.27 MiB peak PSS there, but 266 versus 242 CPU microseconds/request.
- N-body reached 19,906 requests/s for Axon versus Rust’s 15,076, Go’s 8,910 and Bun’s 1,021. Axon used 387 versus Rust’s 538 CPU microseconds/request and 1.12 versus 4.14 MiB peak PSS.
- The Axon executable is 38,584 bytes (37.7 KiB), with no undefined symbols, dynamic section or ELF interpreter. Rust’s executable is 1.02 MiB, Go’s 7.65 MiB and Bun plus its script 96.62 MiB; shared libraries are excluded from disk sizes.
- RSS and PSS both come from smaps_rollup. An earlier partial run under results/2026-10-23-200701-native was stopped because /proc/PID/stat RSS accounting lagged for small processes; its raw results and reason are preserved. It is not included in these tables.
- The container’s /axon directory is the mounted repository. The matching host artifact directory is bench/http/results/2026-10-23-200814-native.
- These short saturation runs measure the current server implementations, not universal language rankings or electrical energy. The Axon HTTP protocol subset is narrower than the comparison frameworks.
- The full Linux regression suite passed: 17 unit tests, HTTP protocol/concurrency/backpressure checks, kernel allocation and shared-memory worker tests, all six compute examples with one and four workers, and argument/refinement checks. The exact benchmark executable also passed HTTP inside an otherwise empty root filesystem. Logs are included beside measurements.json.
