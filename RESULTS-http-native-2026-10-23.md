# HTTP benchmarks: Axon runtime written in Axon

Measured 2026-10-23T18:55:24.653666+02:00. Apple M1 Pro; 10 logical CPUs; 16.00 GiB RAM; macOS 27.0.

wrk wrk 4.2.0 [kqueue] Copyright (C) 2012 Will Glozer, 4 client threads, 3 measured runs of 5s after 2s warm-up. Client and server share this machine. Server order is shuffled with a recorded seed.

Each request body was validated against independent Python references before loading each server. Rust uses hyper/tokio with pipeline_flush enabled. Axon and Bun currently process handlers on one event loop; default Rust and Go may use multiple application workers. Single-worker rows set TOKIO_WORKER_THREADS=1 / GOMAXPROCS=1; these are worker budgets, not OS CPU affinity.

CPU/request covers all server threads, user + kernel time, using macOS proc_pid_rusage and the Mach timebase (calibrated against Python process_time). RSS and physical footprint are sampled every 100 ms during measured runs, after warm-up. Physical footprint is the macOS accounting metric, distinct from RSS and from disk size. Memory columns are sampled peaks, not lifetime high-water marks. Latencies come from closed-loop wrk saturation and may hide coordinated omission.

Pipelined latency percentiles are omitted: this wrk build emitted invalid/nonmonotonic percentiles, including p99=0 µs despite millisecond average latency. Raw stdout is preserved. Pipeline throughput and CPU measurements use the request and CPU counters, not those percentiles.

Disk sizes below count the native executable, or the Bun executable plus this benchmark script. Shared OS libraries, compilers, SDKs, caches and deployment packaging are excluded. Startup is a warm-filesystem process-to-listening observation, not a cold-start benchmark.

Versions: Axon: Python compiler + native Axon runtime; Clang: Apple clang version 21.0.0 (clang-2100.3.34.2); Rust: rustc 1.98.1 (48a229cea 2026-09-01); Go: go version go1.25.1 darwin/arm64; Bun: 1.3.13.

## Executable and idle footprint

| Server | Executable + script MiB | Idle RSS MiB | Idle physical MiB | Startup ms |
|---|---:|---:|---:|---:|
| Axon | 0.05 | 1.69 | 1.22 | 9.2 |
| Rust | 0.91 | 2.36 | 1.50 | 9.2 |
| Go | 7.73 | 9.38 | 3.41 | 20.9 |
| Bun | 60.15 | 25.28 | 9.67 | 37.2 |

## hello-64

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Peak RSS MiB | Peak physical MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 112,177 | 111,328–114,527 | 560 | 910 | 8.75 | 0.98 | 3.70 | 3.25 | 0 / 0 |
| Rust | 129,987 | 124,066–130,071 | 466 | 651 | 18.31 | 2.34 | 4.81 | 3.92 | 0 / 0 |
| Go | 114,684 | 113,319–115,716 | 504 | 1400 | 35.67 | 4.08 | 21.98 | 13.19 | 0 / 0 |
| Bun | 76,797 | 44,624–80,672 | 820 | 2690 | 13.13 | 0.88 | 34.69 | 14.38 | 0 / 0 |

## hello-256

Route `/`; 256 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Peak RSS MiB | Peak physical MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 120,148 | 117,990–120,896 | 2230 | 2810 | 8.26 | 0.99 | 9.38 | 8.94 | 0 / 0 |
| Rust | 126,832 | 113,931–128,475 | 1930 | 2870 | 18.23 | 2.24 | 8.83 | 7.95 | 0 / 0 |
| Go | 120,945 | 120,015–121,344 | 2030 | 3450 | 35.95 | 4.33 | 26.19 | 17.89 | 0 / 0 |
| Bun | 79,296 | 76,189–79,575 | 3280 | 3800 | 12.67 | 0.99 | 43.77 | 15.28 | 0 / 0 |

## pipeline-16

Route `/`; 64 connections; pipeline depth 16.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Peak RSS MiB | Peak physical MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 308,191 | 299,302–321,748 | n/a | n/a | 3.21 | 0.99 | 3.72 | 3.27 | 0 / 0 |
| Rust | 1,939,087 | 1,923,456–1,946,272 | n/a | n/a | 1.69 | 3.27 | 4.70 | 3.81 | 0 / 0 |
| Go | 272,973 | 266,954–301,786 | n/a | n/a | 15.41 | 4.31 | 28.84 | 16.38 | 0 / 0 |
| Bun | 20,638 | 20,002–21,417 | n/a | n/a | 47.55 | 0.98 | 43.73 | 14.94 | 0 / 0 |

## hello-one-worker

Route `/`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Peak RSS MiB | Peak physical MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 113,438 | 113,332–113,548 | 558 | 850 | 8.74 | 0.99 | 3.28 | 2.83 | 0 / 0 |
| Rust | 111,765 | 110,878–112,656 | 584 | 723 | 8.72 | 0.97 | 4.03 | 3.13 | 0 / 0 |
| Go | 72,561 | 71,769–73,111 | 870 | 1450 | 13.64 | 0.99 | 15.84 | 9.16 | 0 / 0 |
| Bun | 76,850 | 76,140–77,031 | 801 | 1660 | 12.90 | 0.99 | 41.72 | 13.95 | 0 / 0 |

## smooth-1000-one-worker

Route `/smooth/1000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Peak RSS MiB | Peak physical MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 35,668 | 35,473–35,741 | 1770 | 2670 | 27.88 | 0.99 | 3.41 | 2.97 | 0 / 0 |
| Rust | 35,549 | 34,969–35,703 | 1810 | 2040 | 27.84 | 0.98 | 4.22 | 3.31 | 0 / 0 |
| Go | 16,744 | 16,576–16,766 | 3870 | 5970 | 59.62 | 0.99 | 15.92 | 9.34 | 0 / 0 |
| Bun | 8,089 | 4,448–8,924 | 7450 | 19180 | 119.09 | 0.85 | 46.91 | 18.52 | 0 / 0 |

## smooth-10000-one-worker

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Peak RSS MiB | Peak physical MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 4,896 | 4,854–4,905 | 12990 | 20550 | 203.75 | 0.99 | 5.44 | 5.00 | 0 / 0 |
| Rust | 4,767 | 4,508–4,786 | 13540 | 14420 | 210.04 | 0.98 | 4.59 | 3.70 | 0 / 0 |
| Go | 2,107 | 2,089–2,108 | 28820 | 90400 | 475.48 | 1.00 | 16.14 | 9.50 | 0 / 0 |
| Bun | 856 | 852–861 | 73450 | 99810 | 1168.43 | 1.00 | 65.55 | 24.95 | 0 / 0 |

## smooth-10000-default

Route `/smooth/10000`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Peak RSS MiB | Peak physical MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 4,825 | 4,822–4,835 | 13200 | 20790 | 206.45 | 0.99 | 4.48 | 4.05 | 0 / 0 |
| Rust | 31,663 | 30,625–32,145 | 1930 | 4920 | 252.90 | 7.94 | 7.97 | 7.36 | 0 / 0 |
| Go | 10,430 | 10,405–10,469 | 6240 | 30690 | 687.34 | 7.16 | 32.62 | 24.42 | 0 / 0 |
| Bun | 843 | 715–845 | 74590 | 100520 | 1198.46 | 0.96 | 61.44 | 31.34 | 0 / 0 |

## nbody-default

Route `POST:/nbody`; 64 connections; pipeline depth 1.

| Server | Median req/s | Run range req/s | p50 µs | p99 µs | CPU µs/req | CPU cores used | Peak RSS MiB | Peak physical MiB | Errors / non-2xx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Axon | 2,842 | 2,605–2,844 | 22390 | 38220 | 354.01 | 0.98 | 4.66 | 4.22 | 0 / 0 |
| Rust | 15,908 | 14,888–16,030 | 3890 | 8980 | 546.41 | 8.51 | 5.81 | 4.92 | 0 / 0 |
| Go | 9,800 | 9,447–9,859 | 6660 | 39120 | 740.94 | 7.17 | 27.16 | 18.14 | 0 / 0 |
| Bun | 1,048 | 1,047–1,050 | 60160 | 73850 | 955.50 | 1.00 | 55.19 | 28.64 | 0 / 0 |

## Dependency boundary and limits

Axon has no handwritten C runtime source. Its Axon runtime directly calls libSystem functions such as malloc/free, read/write, socket/poll and dispatch_apply_f; those OS/library dependencies still contain C implementations. Python and Clang/LLVM are build dependencies. The Axon HTTP stack is narrower than hyper, net/http and Bun, omits Date, and currently scans a fixed connection table and handles one response at a time per connection. The C runtime’s allocation cache and multiple HTTP workers were removed. These are implementation comparisons, not universal language rankings. Historical C-runtime results are preserved separately and are not a controlled before/after experiment.

Raw measurements, memory samples, commands, binary hashes and per-run logs: `bench/http/results/2026-10-23-185524-native`.

An initial Go hello-256 attempt had socket read/write errors. It is archived under `retries` in the JSON; the table uses the separately recorded rerun. No invalid attempt is silently discarded.

## Reading this run

- With one application worker, hello-world is essentially tied: Axon 113,438 req/s, Rust 111,765; CPU/request 8.74 versus 8.72 µs. Axon peak RSS is 3.28 MiB versus Rust 4.03, Go 15.84 and Bun 41.72 in that scenario.
- Single-worker compute shows similar parity between Axon and Rust: /smooth/1000 is about 35.6k req/s for both, and /smooth/10000 is about 4.9k versus 4.8k. The small Axon lead is not enough to claim a general advantage from three short laptop runs.
- Default-worker heavy-request throughput favors the multicore stacks: /smooth/10000 Rust 31.7k, Go 10.4k, Axon 4.8k, Bun 843 req/s. Current Axon and Bun use one handler event loop. For n-body, Rust reaches 15.9k, Go 9.8k, Axon 2.8k and Bun 1.0k req/s.
- Axon uses less server CPU per n-body request in this run (354 µs) than Rust (546), Go (741) and Bun (956), despite lower total throughput than multicore Rust and Go. CPU efficiency and total capacity are different measurements.
- Pipeline batching is a clear weakness of the rewrite: tuned hyper reaches 1.94M req/s, Axon 308k, Go 273k and Bun 20.6k. The new Axon loop processes/writes one response at a time and its prior C runtime batched pipelined responses. Restoring batching and multiple HTTP workers are concrete next improvements; these measurements do not isolate their individual effects.
- Axon has the smallest executable (about 51 KiB) and very low idle memory. Rust uses less memory than Axon on the large single-worker stencil case (peak physical 3.70 versus 5.00 MiB), so Axon does not win every memory comparison.
- Other desktop services were active, and the client shares this laptop with the server. Run ranges and raw samples are retained; these results do not establish production capacity, energy in joules or performance on Linux.
