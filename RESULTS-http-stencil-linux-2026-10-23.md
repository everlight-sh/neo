# HTTP benchmarks: Axon kernel runtime, multicore workers and batching

Measured 2026-10-23T21:27:31.114316+02:00. aarch64 Linux VM; 8 logical CPUs; 5.77 GiB RAM; Linux 6.8.0-64-generic.

wrk wrk debian/4.1.0-4build2 [epoll] Copyright (C) 2012 Will Glozer, 4 client threads, 3 measured runs of 5s after 2s warm-up. Client and server share this machine. Server order is shuffled with a recorded seed.

Every route was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Axon runs one process per configured worker, with round-robin connection assignment, a dense connection vector, retained buffers and up to 64 responses per batch. Default Rust and Go may use multiple workers; Bun runs one handler event loop. Single-worker rows set AXON_THREADS=1 / TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request includes all threads in the parent and every descendant worker process, user + kernel time. macOS uses proc_pid_rusage with Mach-timebase conversion; Linux uses /proc/PID/stat. Both samplers are calibrated against Python process_time. Memory is sampled every 100 ms after warm-up and summed across all live workers. The footprint column is Linux PSS. Aggregate RSS can count shared pages more than once; Linux PSS apportions shared pages. These are sampled peaks, not lifetime high-water marks. Latencies are closed-loop wrk saturation measurements and may hide coordinated omission.

Pipelined latency percentiles are omitted consistently across both platforms after the macOS wrk build emitted invalid/nonmonotonic values, including p99=0 µs despite millisecond average latency. Raw reported values and stdout are preserved. Pipeline throughput and CPU measurements use the request and CPU counters, not those percentiles.

Disk sizes below count the native executable, or the Bun executable plus this benchmark script. Shared OS libraries, compilers, SDKs, caches and deployment packaging are excluded. Startup is a warm-filesystem process-to-listening observation, not a cold-start benchmark.

Versions: Axon: Kernel syscall runtime, prefork HTTP workers + response batches; Clang: Ubuntu clang version 18.1.3 (1ubuntu1); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 linux/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle aggregate RSS MiB | Idle Linux PSS MiB | Startup ms |
|---|---:|---:|---:|---:|
| Axon | 0.04 | 0.48 | 0.17 | 6.0 |
| Rust | 1.02 | 2.43 | 1.56 | 6.2 |
| Go | 7.65 | 6.38 | 5.63 | 12.1 |
| Bun | 96.62 | 36.99 | 35.97 | 16.8 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 635,125 | 613,052–655,358 | 63 | 1460 | 5.49 | 3.48 | 8 | 1.17 | 0.87 | 0 / 0 |
| Rust | 292,183 | 288,054–293,426 | 183 | 528 | 7.00 | 2.04 | 1 | 5.32 | 4.27 | 0 / 0 |
| Go | 308,557 | 307,564–311,882 | 129 | 2150 | 14.15 | 4.37 | 1 | 15.27 | 14.38 | 0 / 0 |
| Bun | 98,021 | 92,307–102,446 | 596 | 1770 | 10.82 | 1.06 | 1 | 55.69 | 54.50 | 0 / 0 |

## hello-256

Route `/`; 256 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 732,672 | 720,919–733,299 | 161 | 2610 | 5.26 | 3.83 | 8 | 2.67 | 2.37 | 0 / 0 |
| Rust | 583,097 | 575,631–588,053 | 360 | 1620 | 6.12 | 3.56 | 1 | 10.43 | 9.37 | 0 / 0 |
| Go | 313,565 | 312,384–318,354 | 516 | 5250 | 14.58 | 4.58 | 1 | 21.81 | 20.93 | 0 / 0 |
| Bun | 87,554 | 84,546–88,598 | 2800 | 4420 | 12.04 | 1.05 | 1 | 55.49 | 54.30 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 6,445,201 | 6,277,373–6,480,021 | n/a | n/a | 0.52 | 3.30 | 8 | 1.17 | 0.87 | 0 / 0 |
| Rust | 3,386,350 | 3,329,631–3,446,238 | n/a | n/a | 0.89 | 3.02 | 1 | 4.98 | 3.93 | 0 / 0 |
| Go | 459,756 | 442,974–460,900 | n/a | n/a | 10.58 | 4.80 | 1 | 19.46 | 18.58 | 0 / 0 |
| Bun | 26,441 | 26,334–26,468 | n/a | n/a | 38.98 | 1.03 | 1 | 53.83 | 52.64 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 257,061 | 254,316–275,400 | 219 | 606 | 3.81 | 1.00 | 1 | 0.77 | 0.77 | 0 / 0 |
| Rust | 207,469 | 202,680–211,916 | 305 | 458 | 4.83 | 1.00 | 1 | 3.40 | 2.34 | 0 / 0 |
| Go | 91,289 | 89,848–91,331 | 706 | 1520 | 11.03 | 1.00 | 1 | 12.47 | 11.60 | 0 / 0 |
| Bun | 102,382 | 90,214–103,204 | 575 | 1830 | 10.74 | 1.06 | 1 | 55.06 | 53.87 | 0 / 0 |

## smooth-1000-one-worker

Route `/smooth/1000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 42,004 | 41,525–42,599 | 1500 | 2890 | 23.78 | 1.00 | 1 | 0.77 | 0.77 | 0 / 0 |
| Rust | 34,202 | 33,869–34,341 | 1890 | 2250 | 29.29 | 1.00 | 1 | 3.50 | 2.45 | 0 / 0 |
| Go | 15,393 | 15,387–15,523 | 4130 | 8300 | 64.87 | 1.00 | 1 | 12.59 | 11.72 | 0 / 0 |
| Bun | 9,435 | 9,402–9,477 | 6550 | 12620 | 109.33 | 1.03 | 1 | 58.71 | 57.52 | 0 / 0 |

## smooth-10000-one-worker

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 5,920 | 5,913–5,926 | 10580 | 86410 | 169.07 | 1.00 | 1 | 0.77 | 0.77 | 0 / 0 |
| Rust | 4,333 | 4,288–4,355 | 14910 | 15870 | 231.33 | 1.00 | 1 | 3.73 | 2.67 | 0 / 0 |
| Go | 2,057 | 2,056–2,063 | 29300 | 96080 | 486.39 | 1.00 | 1 | 12.40 | 11.52 | 0 / 0 |
| Bun | 1,085 | 1,075–1,085 | 57650 | 113670 | 942.66 | 1.02 | 1 | 70.68 | 69.50 | 0 / 0 |

## smooth-10000-default

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 42,843 | 42,624–42,883 | 1380 | 4260 | 175.55 | 7.50 | 8 | 2.27 | 1.96 | 0 / 0 |
| Rust | 32,044 | 30,115–32,127 | 1950 | 4500 | 244.11 | 7.67 | 1 | 5.79 | 4.73 | 0 / 0 |
| Go | 9,046 | 9,029–9,097 | 8070 | 33020 | 638.62 | 5.78 | 1 | 22.11 | 21.23 | 0 / 0 |
| Bun | 1,077 | 1,072–1,085 | 58000 | 114510 | 948.29 | 1.02 | 1 | 70.59 | 69.41 | 0 / 0 |

## nbody-default

Route `POST:/nbody`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Processes | Aggregate RSS MiB | Linux PSS MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 18,389 | 16,345–18,927 | 3050 | 9990 | 425.18 | 7.59 | 8 | 1.39 | 1.09 | 0 / 0 |
| Rust | 11,952 | 10,093–16,589 | 4640 | 134710 | 602.93 | 7.59 | 1 | 5.19 | 4.13 | 0 / 0 |
| Go | 9,046 | 8,664–9,073 | 7540 | 39740 | 667.93 | 5.95 | 1 | 16.37 | 15.49 | 0 / 0 |
| Bun | 987 | 918–1,015 | 62060 | 122640 | 1051.03 | 1.02 | 1 | 63.47 | 62.28 | 0 / 0 |

## Dependency boundary and limits

Axon allocation/free lists, memory operations, formatting, process scheduling and HTTP handling are Axon source, with compiler primitives for direct ARM64 kernel syscalls. Its Linux executable is static, has no ELF interpreter, shared libraries or undefined symbols. The Mac executable imports no functions but must load libSystem because Apple requires it for native ARM64 executable startup; Mac is therefore not dependency-free. Python and Clang/LLVM remain build dependencies, and both targets require the OS kernel. The HTTP protocol subset is narrower than hyper, net/http and Bun and omits Date. These are implementation comparisons, not universal language rankings. Linux VM results and Mac results are separate environments.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `/axon/bench/http/results/2026-10-23-212731-native`.

## Reading this run

- This run tests the compiler’s bounded remainder optimization. Axon HTTP and runtime sources, plus the Rust, Go and Bun benchmark sources, are unchanged from the preceding kernel-runtime comparison; their matching hashes are recorded in the validation data. There is no response caching or reduced iteration count.
- The compiler infers that the stencil dividend is in [0, 4,000,008]. It replaces signed i64 remainder by 1,000,003 with two conditional subtractions in 32-bit arithmetic, then extends the result to i64. The pass is generic, handles signed inputs conservatively and can be disabled with AXON_RANGE=0.
- All 32 comparisons and 96 measured runs completed with zero socket errors or non-2xx responses. Every Axon sample counts eight processes in default mode and one in single-worker mode, including all worker CPU and memory.
- All three stencil cases beat the unchanged Rust server: 42,004 versus 34,202 requests/s for 1,000 elements with one worker (+22.8%); 5,920 versus 4,333 for 10,000 elements with one worker (+36.6%); and 42,843 versus 32,044 for 10,000 elements with default workers (+33.7%). In every case Axon’s slowest sample exceeds Rust’s fastest.
- For the large default-worker stencil, Axon used 175.55 versus Rust’s 244.11 CPU microseconds/request and 1.96 versus 4.73 MiB sampled peak PSS. The previous Axon kernel-runtime run measured 28,574 requests/s here; the historical comparison is a separate run, not a controlled A/B experiment.
- Pipelining remains fast: 6.45 million requests/s for Axon versus Rust’s 3.39 million, with 0.52 versus 0.89 CPU microseconds/request. The remaining workload results, including n-body, are retained in full above.
- The 38,712-byte (37.8 KiB) Axon ELF is still static, with zero undefined symbols or shared libraries. The exact benchmark executable passed the HTTP suite from an otherwise empty filesystem. No runtime source or dependency was added.
- The full regression suite passed: 28 unit tests; HTTP protocol, concurrency, backpressure and batching checks; allocator and shared-memory worker checks; all six compute examples with one and four workers; argument/refinement checks; and 2,080 native signed/overflow/tail cases against an independent wrapping-i64 reference with optimization on and off. Logs and the build report are included beside measurements.json.
- This is ARM64 Ubuntu in an eight-vCPU Colima VZ VM with 6 GiB configured RAM on the M1 Pro host. Client and server share the VM. The container’s /axon mount is this repository; host artifacts are under bench/http/results/2026-10-23-212731-native.
- These are three short saturation samples of the existing server implementations. The Axon HTTP subset is narrower than the comparison frameworks; the results do not establish universal language rankings or electrical energy use. Native Mac is a separate environment.
