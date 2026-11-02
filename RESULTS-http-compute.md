# HTTP results: compute endpoint

Machine: Apple M1 Pro, 10 cores. Load generator: wrk 4.2.0 [kqueue] Copyright (C) 2012 Will Glozer, 4 threads, keep-alive, running on the same machine as the server (they share the cores). Each cell is the median of 3 runs of 5s (best run in parentheses); latencies are from the median run.

Every server answers `GET /smooth/N` with 32 passes of a 3-point i64 stencil over an N-element synthetic signal and a JSON body `{"n":N,"passes":32,"checksum":C}`; bodies were checked byte-for-byte against a Python reference before each run. Axon and Rust-std send three headers; hyper, Go and Bun also add `Date`. Axon's two rows are the same binary: `AXON_SERVE=threads` selects one blocking thread per connection; the default runs one kqueue event loop per core.

## /smooth/10000, 64 connections

| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |
|---|---|---|---|---|---|---|
| Axon (kqueue workers) | 31,403 (35,594) | 1530 µs | 12740 µs | 0 | 0 | 241.8 µs |
| Axon (thread per conn) | 29,550 (30,727) | 860 µs | 293820 µs | 0 | 0 | 256.1 µs |
| Rust (std threads) | 25,826 (29,977) | 1230 µs | 164040 µs | 0 | 0 | 260.9 µs |
| Rust (hyper + tokio) | 31,861 (32,900) | 1920 µs | 5940 µs | 0 | 0 | 250.0 µs |
| Go (net/http) | 9,401 (9,495) | 6990 µs | 45020 µs | 0 | 0 | 679.3 µs |
| Bun (Bun.serve) | 831 (845) | 74840 µs | 105600 µs | 0 | 0 | 1192.1 µs |

## /smooth/1000, 64 connections

| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |
|---|---|---|---|---|---|---|
| Axon (kqueue workers) | 139,639 (141,994) | 315 µs | 3480 µs | 0 | 0 | 38.6 µs |
| Axon (thread per conn) | 132,410 (134,029) | 357 µs | 2710 µs | 0 | 0 | 40.4 µs |
| Rust (std threads) | 108,560 (111,258) | 377 µs | 11160 µs | 0 | 0 | 39.3 µs |
| Rust (hyper + tokio) | 118,625 (121,822) | 415 µs | 31720 µs | 0 | 0 | 39.4 µs |
| Go (net/http) | 47,568 (48,681) | 1110 µs | 7790 µs | 0 | 0 | 115.5 µs |
| Bun (Bun.serve) | 8,606 (8,977) | 7210 µs | 12510 µs | 0 | 0 | 113.8 µs |

## /smooth/10000, 64 connections, server on 2 cores

Server limited to 2 worker threads (AXON_THREADS / TOKIO_WORKER_THREADS / GOMAXPROCS); thread-per-connection servers cannot be pinned and are omitted; Bun runs unchanged (single-threaded already).

| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |
|---|---|---|---|---|---|---|
| Axon (kqueue workers) | 9,740 (9,778) | 6340 µs | 12780 µs | 0 | 0 | 203.8 µs |
| Rust (hyper + tokio) | 8,734 (9,000) | 7340 µs | 18310 µs | 0 | 0 | 218.4 µs |
| Go (net/http) | 3,215 (3,395) | 17570 µs | 80140 µs | 0 | 0 | 549.8 µs |
| Bun (Bun.serve) | 708 (733) | 81400 µs | 247510 µs | 0 | 0 | 1279.0 µs |

## POST /nbody n=256 steps=4, 64 connections

| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |
|---|---|---|---|---|---|---|
| Axon (kqueue workers) | 11,916 (12,451) | 4210 µs | 56180 µs | 0 | 0 | 423.1 µs |
| Axon (thread per conn) | 14,919 (15,943) | 1760 µs | 441710 µs | 0 | 0 | 427.4 µs |
| Rust (hyper + tokio) | 13,841 (14,600) | 4390 µs | 12430 µs | 0 | 0 | 538.7 µs |
| Go (net/http) | 8,446 (8,666) | 7570 µs | 41430 µs | 0 | 0 | 742.7 µs |
| Bun (Bun.serve) | 1,013 (1,019) | 62120 µs | 81700 µs | 0 | 0 | 984.9 µs |

## Reading the numbers (refreshed with the size-class allocator)

- **`/smooth/10000`: Axon and hyper tie at about 31k requests per second; Go is 3.3x behind, Bun 38x.** Per-request CPU: Axon 242 µs, hyper 250, Rust-std 261, Go 679, Bun 1192. Pinned to 2 cores Axon leads slightly (9.7k vs 8.7k, 204 vs 218 µs). The stencil loop compiles to the same vectorised, check-free code in Axon and Rust here, so parity is the honest outcome for this endpoint.
- **`/smooth/1000`: Axon 140k, hyper 119k, Rust-std 109k, Go 48k, Bun 8.6k.** CPU per request is 39 µs for Axon and both Rust servers, 116 for Go and 114 for Bun.
- **`POST /nbody`: Axon uses the least CPU per request (423 µs against hyper's 539 and Go's 743) but hyper's throughput is higher in this run (13.8k against 11.9k).** The Axon binary in thread-per-connection mode reached 14.9k on the same endpoint. The cause is visible in the tail: with connections pinned to kqueue workers and no work stealing, a burst of heavy requests on one worker's connections queues behind each other (p99 56 ms against hyper's 12 ms). tokio steals tasks between workers; Axon's runtime does not yet. This is a runtime scheduling gap, not a codegen one, and it matters only when requests are both heavy and uneven.
- **What decided each row.** Allocation strategy first (the size-class allocator replaced the earlier exact-size cache), then code shape (Rust's server loop happens to be one LLVM can strip of bounds checks), then data layout and reduction order (n-body's struct-of-arrays records and order-free `sum`). The runtime's own request path is about 10 µs per request and identical across endpoints.

## What the Axon program does

[examples/http.ax](examples/http.ax) serves `GET /`, `GET /smooth/N`, `POST /nbody` and `GET /page/N`. Everything past framing is Axon: byte search with loop invariants, `parse_int`, `json_int`, `itoa`, fixed-point `ftoa`, `concat`, HTML escaping, and the n-body model over `type Body` records. The checker discharged 129 of 132 obligations; the remaining three are the argv precondition on the port and one `check` in `ftoa` on the integer part of a float.

## Caveats

wrk shares the machine with the server, which depresses every absolute number; the 2-core scenario removes that for the multi-core servers. Bodies were verified against a Python reference before every measurement (`/smooth` byte-for-byte, `/nbody` energy within 1e-9). The Rust std server has no POST route and is omitted from that row. Bun runs single-threaded on macOS (see RESULTS-http.md). Numbers move 10 to 20 percent between full runs of this suite.
