# HTTP results: server-side rendering

Machine: Apple M1 Pro, 10 cores. Load generator: wrk 4.2.0 [kqueue] Copyright (C) 2012 Will Glozer, 4 threads, keep-alive, running on the same machine as the server (they share the cores). Each cell is the median of 3 runs of 5s (best run in parentheses); latencies are from the median run.

Every server answers `GET /page/N` with the product-catalog page of bench/react/page.tsx (N rows, HTML-escaped notes, a computed total). Bun and Node render it with React 19's `renderToString`; Axon, Rust and Go hand-render the same HTML. Every server's `/page/50` was compared byte-for-byte with React's output before measuring. Axon and Rust-std send three headers; hyper, Go and Bun also add `Date`. Axon's two rows are the same binary: `AXON_SERVE=threads` selects one blocking thread per connection; the default runs one kqueue event loop per core.

## GET /page/50, 64 connections

| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |
|---|---|---|---|---|---|---|
| Axon (hand-rendered) | 141,118 (141,185) | 425 µs | 642 µs | 0 | 0 | 20.5 µs |
| Rust (hyper, hand-rendered) | 148,281 (148,597) | 382 µs | 677 µs | 0 | 0 | 25.0 µs |
| Go (net/http, hand-rendered) | 64,252 (64,768) | 910 µs | 4640 µs | 0 | 0 | 78.4 µs |
| Bun (React renderToString) | 2,221 (2,262) | 28240 µs | 32930 µs | 0 | 0 | 454.5 µs |
| Node (React renderToString) | 1,588 (1,600) | 34900 µs | 776270 µs | 0 | 0 | 658.3 µs |
| Node cluster (React, 10 workers) | 9,544 (9,571) | 5670 µs | 58220 µs | 0 | 0 | n/a |

## GET /page/50, 64 connections, server on 2 cores

Server limited to 2 workers (AXON_THREADS / TOKIO_WORKER_THREADS / GOMAXPROCS / NODE_CLUSTER); Bun and single-process Node run unchanged (one thread already).

| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |
|---|---|---|---|---|---|---|
| Axon (hand-rendered) | 140,865 (143,548) | 401 µs | 1200 µs | 0 | 0 | 13.7 µs |
| Rust (hyper, hand-rendered) | 114,345 (114,790) | 547 µs | 910 µs | 0 | 0 | 16.7 µs |
| Go (net/http, hand-rendered) | 56,985 (57,357) | 1120 µs | 2710 µs | 0 | 0 | 33.2 µs |
| Bun (React renderToString) | 2,178 (2,267) | 28130 µs | 54840 µs | 0 | 0 | 457.0 µs |
| Node (React renderToString) | 1,544 (1,601) | 34720 µs | 786650 µs | 0 | 0 | 654.7 µs |
| Node cluster (React, 10 workers) | 3,021 (3,090) | 18080 µs | 120130 µs | 0 | 0 | n/a |

## Reading the numbers

- **React SSR costs 50 to 80 times a native renderer for the same bytes.** Rendering the 5.4 KB catalog page takes React 19's `renderToString` about 455 µs of CPU per request on Bun and 658 µs on Node, against 20.5 µs for Axon and 25 µs for Rust. A single Bun or Node process serves about 2k pages per second; ten Node cluster workers reach 9.5k. That is the price of building a virtual element tree and walking it for every request, and it is why frameworks cache, stream, or precompute.
- **Axon beats Rust per core.** Pinned to 2 cores, Axon serves 141k requests per second at 13.7 µs each against Rust's 114k at 16.7 µs: 1.23x the throughput, 18 percent less CPU per request. Unconstrained, the load generator is the bottleneck and Rust's throughput is 5 percent higher even though Axon burns 18 percent less CPU. Go's `strings.Builder` version costs 2x Rust per request, mostly `fmt.Fprintf` and garbage collection.
- **How Axon got from 2x slower to 1.2x faster, without changing the program.** The first run had Axon at 39 µs per request because `concat(acc, row(i))` copied the accumulated page on every row and made about 250 small allocations. Four compiler and runtime changes followed, each measured on 2 cores: a per-thread size-class allocator with in-place `concat` onto owned buffers with spare capacity (39 to 16.0 µs); constant-length copies for literal pieces (15.6); compile-time evaluation of `escape("Ben & Jerry's …")`, legal because every Axon function is pure (14.7); and inlining `row` into the `concat` with the nested concat flattened, so the row's pieces append straight onto the page (13.5). Rust's renderer already does the first by hand with `String::with_capacity`; the other three are things Rust's compiler does not do for this program.
- **The escaper is proven, not checked.** Axon's `escape` writes into a buffer six times the input, keeps the write cursor under `6 * i` by loop invariant, and sizes the result by a bounded `sum`; every `set` and `put` is proven in range. It now also runs at compile time for literal inputs.
- **Node cluster** distributes over processes; its per-request CPU is not measured because the work happens in child processes.

## What the Axon program does

[examples/http.ax](examples/http.ax) handles `GET /page/N`: `parse_int` reads N, `page` folds `row(i)` into the response with `concat`, `row` formats the id, price and stock with `utoa`, picks names from eight-way `if` tables, and escapes the note. The whole handler's byte output equals React's for every N tested (3, 50, and the harness's check before each run). The checker discharged 129 of 132 obligations; the remaining three are the argv port precondition and one `check` in the float formatter used by `/nbody`.

## Caveats

wrk shares the ten cores with the server; the 2-core scenario removes that for the multi-threaded servers, and Bun and single-process Node are single-threaded regardless. React is doing more than the hand renderers: it builds a component tree and could render arbitrary components, while the native renderers are specialised to this page. That is the trade the benchmark measures, not a defect in React. Go's idiomatic `html/template` was not used because its escaping (`&#39;`, `&#34;`) differs from React's. All three native renderers could be tuned further; the point is what each compiler does with the straightforward program.
