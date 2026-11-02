# HTTP results

Machine: Apple M1 Pro, 10 cores. Load generator: wrk 4.2.0 [kqueue] Copyright (C) 2012 Will Glozer, 4 threads, keep-alive, running on the same machine as the server (they share the cores). Each cell is the median of 3 runs of 5s (best run in parentheses); latencies are from the median run.

Every server answers `GET /` with `200 Hello, World!` and anything else with 404. Axon and Rust-std send three headers; hyper, Go and Bun also add `Date`. Axon's two rows are the same binary: `AXON_SERVE=threads` selects one blocking thread per connection; the default runs one kqueue event loop per core.

## 64 connections

| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |
|---|---|---|---|---|---|---|
| Axon (kqueue workers) | 136,041 (140,541) | 422 µs | 920 µs | 0 | 0 | 16.3 µs |
| Axon (thread per conn) | 127,081 (127,498) | 464 µs | 870 µs | 0 | 0 | 16.9 µs |
| Rust (std threads) | 111,424 (120,076) | 463 µs | 2710 µs | 0 | 0 | 16.4 µs |
| Rust (hyper + tokio) | 132,508 (132,810) | 345 µs | 1140 µs | 0 | 0 | 19.1 µs |
| Go (net/http) | 125,359 (129,221) | 340 µs | 2060 µs | 0 | 0 | 33.4 µs |
| Bun (Bun.serve) | 88,190 (88,382) | 696 µs | 1380 µs | 0 | 0 | 11.2 µs |

## 256 connections

| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |
|---|---|---|---|---|---|---|
| Axon (kqueue workers) | 141,784 (142,722) | 1750 µs | 2140 µs | 0 | 0 | 16.6 µs |
| Axon (thread per conn) | 132,407 (133,702) | 1850 µs | 3830 µs | 0 | 0 | 16.7 µs |
| Rust (std threads) | 130,198 (139,620) | 1730 µs | 4540 µs | 0 | 0 | 17.7 µs |
| Rust (hyper + tokio) | 150,289 (150,820) | 1540 µs | 2270 µs | 0 | 0 | 22.8 µs |
| Go (net/http) | 142,095 (142,362) | 1080 µs | 4970 µs | 0 | 0 | 31.9 µs |
| Bun (Bun.serve) | 94,217 (95,672) | 2770 µs | 3480 µs | 0 | 0 | 10.5 µs |

## 64 connections, 16 pipelined

Each connection sends 16 requests per write (TechEmpower plaintext convention); measures the HTTP layer with the kernel mostly out of the way.

| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |
|---|---|---|---|---|---|---|
| Axon (kqueue workers) | 2,293,709 (2,314,671) | 227 µs | 496 µs | 0 | 0 | 1.0 µs |
| Axon (thread per conn) | 462,363 (467,802) | 1140 µs | 3440 µs | 0 | 0 | 11.7 µs |
| Rust (std threads) | 464,899 (466,393) | 1120 µs | 3010 µs | 0 | 0 | 11.6 µs |
| Rust (hyper + tokio) | 478,637 (478,831) | 1150 µs | 3640 µs | 0 | 0 | 9.7 µs |
| Go (net/http) | 325,863 (327,204) | 2170 µs | 11840 µs | 0 | 0 | 15.7 µs |
| Bun (Bun.serve) | 24,378 (25,335) | 22910 µs | 54000 µs | 0 | 0 | 40.2 µs |

## 64 connections, server on 2 cores

Server limited to 2 worker threads (AXON_THREADS / TOKIO_WORKER_THREADS / GOMAXPROCS) so the server, not the load generator, is the bottleneck; thread-per-connection servers cannot be pinned and are omitted. Bun runs unchanged because its handler is single-threaded already.

| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |
|---|---|---|---|---|---|---|
| Axon (kqueue workers) | 169,276 (169,416) | 347 µs | 520 µs | 0 | 0 | 10.4 µs |
| Rust (hyper + tokio) | 150,158 (156,150) | 390 µs | 763 µs | 0 | 0 | 11.8 µs |
| Go (net/http) | 134,003 (135,546) | 457 µs | 1240 µs | 0 | 0 | 14.6 µs |
| Bun (Bun.serve) | 90,087 (92,115) | 717 µs | 1360 µs | 0 | 0 | 11.1 µs |

## Reading the numbers

- **Plain keep-alive load (64 and 256 connections) is client-bound for the multi-core servers.** wrk and the server share ten cores, so Axon, hyper, Go and the thread-per-connection servers all land between 125k and 150k requests per second, within run-to-run noise of each other. Bun sits at 88 to 94k because `Bun.serve` runs its handler and HTTP core on one thread: on macOS `reusePort` does not spread connections across processes (in a four-process test all traffic went to one process), so Bun cannot use the other cores here.
- **Server on 2 cores is the fair efficiency test.** Axon serves 169k requests per second against hyper's 150k, Go's 134k and Bun's 90k: 1.13x hyper, 1.26x Go, 1.9x Bun. CPU per request: Axon 10.4 µs, Bun 11.1, hyper 11.8, Go 14.6. Bun's per-request CPU is competitive; its limit is the single thread, not the cost per request. Of Axon's 10 µs almost all is the kernel (read, write, kevent, TCP loopback); the runtime's parsing and the compiled handler are well under a microsecond.
- **Pipelined load rewards batching and punishes sequential writers.** Axon answers 16 pipelined requests with one read and one write: 2.29M requests per second at 1.0 µs of CPU each. hyper as configured reaches 479k; with its off-by-default `pipeline_flush(true)` it reaches 2.16M (median of three runs, measured separately), so that gap is configuration, not language. Go's net/http has no such option and flushes per response (326k). Bun collapses to 24k with 23 ms median latency: it handles pipelined requests one at a time through the JavaScript event loop and writes each response in about five separate syscalls (a 16-deep pipeline on one connection took 79 reads to collect). Browsers do not pipeline, so this hurts Bun only under this kind of load.
- **Fewer, busier workers are more efficient.** Axon's CPU per request drops from 16 µs with 10 workers to 10 µs with 2, because kevent returns batches instead of waking an idle thread per request. hyper (19 to 12 µs) and Go (33 to 15 µs) show the same effect.

## Bottom line

Axon's runtime is at parity with the best-configured Rust stack, 15 to 30 percent more efficient per core than Go's net/http, and about twice Bun's throughput on this machine because Bun is confined to one core on macOS. It is not "way better" than Rust, and on hello-world nothing can be: the request path is dominated by kernel networking that costs the same in every language. A large gap over Rust needs either a workload where the handler does real computation (see RESULTS.md, where proof-eliminated bounds checks give 1.9x) or kernel bypass, which is not a language property.

## Caveats

wrk and the server share one 10-core laptop, so absolute numbers are depressed and medians of three 5-second runs still moved by 10 to 20 percent between full harness runs. Hello-world plaintext measures the HTTP layer, not application code; Axon's HTTP layer is about 250 lines of C in the runtime and speaks only what this benchmark needs (HTTP/1.1 keep-alive, Content-Length bodies, pipelining), while hyper, net/http and Bun are complete implementations that also add a `Date` header. The Rust std server is the shape of the Rust Book's final project with keep-alive added; hyper is the fair Rust comparison. On Linux, Bun's `reusePort` would let several processes share the port and its multi-core numbers would look different. All six configurations pass the same edge-case script (`bench/http/protocol_test.py`: pipelining, byte-at-a-time delivery, POST body skipping, 300 idle connections).
