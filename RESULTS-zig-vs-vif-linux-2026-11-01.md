# Vif vs Zig: compute, JSON and HTTP on a 2-vCPU x86-64 Linux box (2026-11-01)

A quick comparison against Zig 0.17.0 on the workloads the repository already uses for Rust, Go and
Bun. Vif ("Axon" in the sources) was built and run fresh on the same box; no number below is copied
from an older report. Zig sources and drivers: `bench/zig/`. Raw measurements, versions, binary
sizes and hashes: `bench/zig/results/2026-11-01-vultr-2c/`.

## Environment

- Temporary Vultr `voc-c-2c-4gb-50s-amd`, Amsterdam: 2 dedicated AMD EPYC-Genoa vCPUs (AVX-512),
  4 GB RAM, Ubuntu 24.04, Linux 6.8.0-146. Created for this run and destroyed afterwards; the Vultr
  listing no longer shows it. A monitoring agent ran on it at about 0.3% CPU.
- Vif: commit `9b9aa2d` (`git archive HEAD`; uncommitted TLS/X.509/RSA edits in the working tree are
  not included and none of these workloads uses them). `./axon build X.ax -o X --no-cache` (LLVM
  `-O3`), Ubuntu clang 18.1.3. Every Vif binary is a static ELF with no dynamic section and 0
  undefined symbols. HTTP ran with no `AXON_HTTP_URING` override, so it used the x86-64 Linux
  default, io_uring. I did not separately confirm the ring was opened, as the 10-31 driver did.
- Zig: 0.17.0 (2026-10-01), official `zig-x86_64-linux-0.17.0.tar.xz` from ziglang.org, SHA-256
  checked against the download index. `zig build -Doptimize=ReleaseFast -Dcpu=baseline`, plus a
  second build with the default `-mcpu=native` ("Zig native").
- karlseguin/http.zig: no release tags exist (only `last-mach`). Its README says master "is for Zig
  0.17.0", so it is pinned to master commit `1bb71ff` (2026-10-29) through `build.zig.zon` with a
  content hash.
- wrk 4.1.0 (Ubuntu package), Python 3.12.3, GNU time.

**Why `-Dcpu=baseline` is the main Zig column.** `axonc` passes no `-march`, so Vif emits generic
x86-64 (SSE2) code, as the earlier Rust builds did. Baseline Zig is the like-for-like ISA. "Zig native"
shows what Zig gets by default when built on the target (AVX-512 here). Vif cannot be built for native
CPU without compiler changes.

## Headline

Ratio = Zig time / Vif time for the command-line workloads (above 1.00× means Vif is faster). For
HTTP it is Vif req/s / Zig req/s and Zig CPU per request / Vif CPU per request. "Best Zig" is the
fastest baseline Zig variant for that row.

| Workload | Vif | Best Zig (baseline) | Ratio | Result |
|---|---:|---:|---:|---|
| mandel 1200×1200×300, 1 worker | 132.9 ms | 186.7 ms | 1.40× | Vif faster |
| mandel, 2 workers | 69.5 ms | 96.4 ms | 1.39× | Vif faster |
| stencil 1M×20, 1 worker | 34.2 ms | 35.2 ms | 1.03× | about equal |
| stencil 1M×20, 2 workers | 33.4 ms | 37.0 ms | 1.11× | Vif faster |
| **stencil 50M×20, 1 worker** | 5,982 ms | 1,685 ms | **0.28×** | **Zig 3.6× faster** |
| **stencil 50M×20, 2 workers** | 5,654 ms | 1,030 ms | **0.18×** | **Zig 5.5× faster** |
| nbody 1024×3, 1 worker | 10.8 ms | 16.5 ms | 1.52× | Vif faster |
| nbody 4096×10, 1 worker | 347.2 ms | 630.7 ms | 1.82× | Vif faster |
| nbody 4096×10, 2 workers | 180.4 ms | 326.9 ms | 1.81× | Vif faster |
| sieve 1e8, 1 worker | 500.7 ms | 487.0 ms | 0.97× | Zig 3% faster |
| sieve 1e8, 2 workers | 504.6 ms | 477.9 ms | 0.95× | Zig 6% faster |
| JSON small document ×1M | 198.0 ms | 316.8 ms (typed, arena) | 1.60× | Vif faster |
| JSON 1,000 orders ×1,000 | 181.2 ms | 212.7 ms (typed, arena) | 1.17× | Vif faster |
| HTTP hello, CPU per request | 9.87 µs | 12.33 µs (http.zig) | 1.25× | Vif cheaper |
| HTTP hello, req/s (client-bound) | 76,236 | 78,593 (http.zig) | 0.97× | http.zig 3% more req/s |
| HTTP 16-deep pipelining, req/s | 1,004,454 | 105,773 (std.http) | 9.5× | Vif faster; http.zig stalls |
| HTTP `/smooth/10000`, req/s | 3,114 | 2,564 (std.http) | 1.21× | Vif faster |
| HTTP `POST /nbody` 256×4, req/s | 1,447 | 869 (std.http) | 1.67× | Vif faster |
| HTTP `/page/50`, req/s | 70,600 | 63,209 (http.zig) | 1.12× | Vif faster |

Vif's losses: the 50M stencil, by 3.6–5.5×, and the sieve, by 3–6%. On HTTP hello, http.zig
completed 3% more requests per second; that test is limited by the load generator, and http.zig
spent 25% more CPU per request. Tail latency in `POST /nbody` is also worse for Vif than for
http.zig with one pool thread (p99 273 ms vs 98 ms), although Vif completed 1.69× more requests.

## Method

All drivers are in `bench/zig/`. Zig and Vif outputs were compared before any timing. Every timed run
was also checked: integers exactly, nbody energy within 1e-9 relative, as in `bench/run.py`.

- **Compute** (`run_cli.py compute`, after `RESULTS-compute-db-x86-linux-2026-10-30.md`): median
  wall time of the complete process over 7 rounds after one warm-up round. Variant order alternates
  each round. One worker is pinned to CPU 0 and two workers to CPUs 0–1 (`taskset`, `AXON_THREADS`
  / `ZIG_THREADS`). The case sizes are those of the 10-30 report, plus the `bench/run.py` 50M stencil
  and the README's sieve. Peak RSS is GNU time `%M`.
- **JSON** (`run_cli.py json`, after `bench/json/run.py`): every process is pinned to CPU 0 with
  `AXON_THREADS=1`. Two warm-up rounds, then 9 measured rounds, order shuffled each round with a fixed
  seed. The workloads are `examples/library_bench.ax 0 1000000` and `bench/core/orders_json.ax 1000
  1000`, with the Zig modes mirroring `bench/rust/src/typed_json.rs`.
- **HTTP** (`run_http.py`, after the 2-vCPU runs of `RESULTS-http-uring-x86-linux-2026-10-31.md` and
  `bench/http/compare.py`): the server is pinned to CPU 0 with one worker. `wrk -t1 -c64 --latency
  --timeout 5s` runs pinned to CPU 1, as does the driver. Each run starts a fresh server, warms up
  for 2 s and measures for 10 s. Results are medians of 5 rounds, alternating server order. CPU per
  request is user + kernel time of every process in the server's session (`/proc`) divided by
  completed requests. "Server CPU busy" is that figure times req/s. Peak RSS is the largest
  `smaps_rollup` Rss sum over the session, sampled every 250 ms. Before measuring, each server was
  checked against the `compare.py` references (`/`, 404, `/smooth/1000`, `/smooth/10000`, 400s,
  `POST /nbody`). `/page/50` was also checked byte for byte against React's
  `bench/react/reference_50.html`. No run had socket errors or non-2xx responses.

A first complete compute and JSON pass agreed with the final one within 3%. Between the two passes,
the Zig stdout helper changed from a positional to a streaming writer. The positional writer wrote
at offset 0 of a redirected file, which did not affect the piped runs, and both suites were rerun.
The HTTP binaries were unaffected: their hashes are unchanged.

### The Zig ports

- `mandel.zig`, `stencil.zig`, `nbody.zig` and `sieve.zig` use the same algorithms, constants and
  arguments as `examples/*.ax` and the Rust ports. nbody uses an array of structs and ping-pong
  buffers, like the Rust and Go versions. Zig has no rayon equivalent, so `par.zig` provides one:
  `workers - 1` threads plus the caller claim chunks of about `n / (8 × workers)` from an atomic
  counter, ranges under 1,024 run sequentially, and threads are spawned per parallel region. Vif
  instead keeps a persistent worker pool.
- `json.zig` uses `std.json.parseFromSlice` into `std.json.Value` (dynamic, like
  `serde_json::Value`) or into structs (typed), freeing each parse with `deinit`. The `-arena`
  variants reuse one `ArenaAllocator` (`reset(.retain_capacity)`) with `parseFromSliceLeaky`, the
  usual Zig tuning for repeated parses.
- `http_std.zig` is standard library only: `std.Io.net` listen and accept, `std.http.Server`
  framing, and one `Io.Group.concurrent` task per connection. With the default threaded `Io`, that
  is a thread per connection, so 65 threads at 64 connections. It sets `TCP_NODELAY`, as Vif and
  hyper do.
- `http_httpz.zig` uses http.zig's router, with epoll workers handing requests to a thread pool. It
  runs in two configurations: **1+1** (`workers.count = 1`, `thread_pool.count = 1`, the closest to
  one worker) and **default** (1 worker, 32 pool threads). http.zig links glibc dynamically.
- `app.zig` holds the route logic shared by both servers: the same routes, status codes and bodies
  as `examples/http.ax` and `http_hyper.rs`. Header bytes differ:
  - Vif sends `Content-Type` and `Content-Length`.
  - std.http sends lower-case `content-length` and `content-type`.
  - http.zig sends `HTTP/1.1 200 ` with no reason phrase and `Content-Type: text/plain;
    charset=UTF-8`.
  - None of them sends `Date`.
- Arithmetic is not equally checked. Vif keeps checked arithmetic and proves array bounds at compile
  time. Zig `ReleaseFast` removes both overflow and bounds checks.

## Compute (median ms; peak RSS MiB)

| Case | Workers | Vif | Zig | Zig native | Zig / Vif | Zig native / Vif | Peak RSS Vif / Zig |
|---|---:|---:|---:|---:|---:|---:|---:|
| mandel-1200-1200-300 | 1 | 132.9 | 186.7 | 192.6 | 1.40× | 1.45× | ≤2 / ≤2 |
| stencil-1000000-20 | 1 | 34.2 | 35.2 | 36.0 | 1.03× | 1.05× | 15.2 / 15.9 |
| stencil-50000000-20 | 1 | 5,982.1 | 1,684.6 | 1,713.7 | 0.28× | 0.29× | 762.9 / 763.6 |
| nbody-1024-3 | 1 | 10.8 | 16.5 | 16.5 | 1.52× | 1.52× | ≤2 / ≤2 |
| nbody-4096-10 | 1 | 347.2 | 630.7 | 633.1 | 1.82× | 1.82× | ≤2 / ≤2 |
| sieve-100000000 | 1 | 500.7 | 487.0 | 481.0 | 0.97× | 0.96× | 95.4 / 96.0 |
| mandel-1200-1200-300 | 2 | 69.5 | 96.4 | 98.2 | 1.39× | 1.41× | ≤2 / ≤2 |
| stencil-1000000-20 | 2 | 33.4 | 37.0 | 35.4 | 1.11× | 1.06× | 15.2 / 16.2 |
| stencil-50000000-20 | 2 | 5,654.1 | 1,030.3 | 945.5 | 0.18× | 0.17× | 762.9 / 763.9 |
| nbody-1024-3 | 2 | 6.8 | 11.7 | 11.0 | 1.73× | 1.63× | ≤2 / ≤2 |
| nbody-4096-10 | 2 | 180.4 | 326.9 | 327.1 | 1.81× | 1.81× | ≤2 / ≤2 |
| sieve-100000000 | 2 | 504.6 | 477.9 | 484.1 | 0.95× | 0.96× | 95.2 / 96.3 |

Outputs: mandel 79165632, stencil 499998359740 (1M) and 25000046624222 (50M), sieve 5761455. nbody
1024×3 gives −0.888664604141282 in every variant: Vif prints `-8.8866460414128208e-1`, Zig
`-0.88866460414128210`, and the variants differ by less than 2e-15 relative. Run ranges are in
`compute.json`. One-worker ranges are within ±6% of the median. Two-worker ranges are wider: up to
+15% for Zig's nbody-1024, and 5,182–5,915 ms for Vif's 50M stencil.

- **mandel:** Vif evaluates the escape loop 8 lanes at a time across iterations. LLVM leaves the
  data-dependent loop scalar in Zig, and AVX-512 does not change that. The 10-30 report measured Rust
  at a similar 1.45× behind Vif, on a different CPU.
- **nbody:** Vif lays the records out struct-of-arrays and may reorder the `sum`, so the inner loop
  vectorises. The Zig port, like the Rust and Go ones, keeps an array of structs and strict
  floating-point order. A Zig rewrite with `std.MultiArrayList` and `@Vector` or
  `@setFloatMode(.optimized)` could narrow this gap. I did not attempt it.
- **stencil 50M is a clear Vif loss, and GNU time shows the cause.**

  | Stencil 50M, 1 worker | Vif | Zig |
  |---|---:|---:|
  | User time | 2.25 s | 1.30 s |
  | Kernel time | 3.83 s | 0.35 s |
  | Minor page faults | 2,050,889 | 195,489 |

  Vif's minor faults are 21 × 97.7k, so every pass first-touches a fresh 400 MB output array. Each
  `stencil(a)` returns a new `Arr i64 n`, and at this size the old buffer is not reused (the
  README describes the large-mapping cache as bounded). The Zig and Rust ports ping-pong two
  preallocated buffers. With two
  workers Vif's kernel time doubles to 7.58 s and wall time hardly moves. At 1M elements (8 MB)
  reuse works and Vif matches Zig (4,002 vs 4,082 faults).
- **sieve:** Zig is 3–6% faster. Both run the same sequential marking loop over one byte per flag.
- **Zig native vs baseline:** within ±6% with no consistent direction (native mandel is 3% slower),
  except the 2-worker 50M stencil (945 vs 1,030 ms, −8%).
- **Peak RSS:** "≤2" marks the floor of the method. GNU time wraps `taskset`, whose own RSS (about
  2 MiB) carries across `exec`. Both languages use the same memory wherever it exceeds that floor.

## JSON (one CPU; median ms over 9 runs)

| Workload | Vif | Zig Value | Zig typed | Zig Value arena | Zig typed arena | Zig Value native | Zig typed native |
|---|---:|---:|---:|---:|---:|---:|---:|
| small document built and decoded ×1M | **198.0** | 640.6 | 333.1 | 582.9 | 316.8 | 651.0 | 319.2 |
| vs Vif | 1.00× | 3.24× | 1.68× | 2.94× | 1.60× | 3.29× | 1.61× |
| 1,000-order array decoded ×1,000 | **181.2** | 1,015.0 | 245.9 | 411.8 | 212.7 | 1,028.5 | 238.4 |
| vs Vif | 1.00× | 5.60× | 1.36× | 2.27× | 1.17× | 5.68× | 1.32× |

Checksums 513500000 and 34327000 match in every variant.

- Vif's dynamic API, which validates fully and indexes source slices, beats both Zig's dynamic
  `std.json.Value` and its typed struct decoding.
- Arena reuse narrows the typed gap to 1.17× on the order array.
- Every process stays at or below the ≈2 MiB RSS floor.
- The Vif order-array time is far below the 783.9 ms of the 10-30 report, which ran on an 8-vCPU
  EPYC-Rome box at an earlier compiler state. Its checksums match Zig, so it does the same work. I
  did not investigate the difference.

## HTTP (server: 1 worker on CPU 0; wrk -t1 -c64 on CPU 1; medians of 5 × 10 s)

| Scenario | Server | req/s | p50 µs | p99 µs | CPU µs/req (user + kernel) | Server CPU busy | Peak RSS MiB | Threads |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `GET /` | Vif | 76,236 | 413 | 1,150 | 0.51 + 9.36 = **9.87** | 75% | 0.8 | 1 |
| | Zig std.http | 61,890 | 495 | 2,200 | 1.24 + 13.66 = 14.90 | 93% | 18.0 | 65 |
| | Zig http.zig 1+1 | 71,354 | 692 | 2,410 | 1.22 + 12.36 = 13.58 | 97% | 3.9 | 3 |
| | Zig http.zig default | **78,593** | 594 | 1,950 | 1.17 + 11.16 = 12.33 | 97% | 12.5 | 34 |
| `GET /`, 16 pipelined | Vif | **1,004,454** | n/a | n/a | 0.13 + 0.58 = **0.71** | 71% | 0.8 | 1 |
| | Zig std.http | 105,773 | n/a | n/a | 0.66 + 8.74 = 9.40 | 100% | 18.0 | 65 |
| | Zig http.zig (both) | stalls | | | | | | |
| `GET /smooth/10000` | Vif | **3,114** | 20,190 | 27,210 | 311.7 + 9.3 = **321.0** | 100% | 1.0 | 1 |
| | Zig std.http | 2,564 | 24,520 | 35,400 | 372.1 + 19.3 = 391.4 | 100% | 29.6 | 71 |
| | Zig http.zig 1+1 | 2,550 | 24,780 | 32,160 | 369.8 + 24.6 = 394.4 | 100% | 13.0 | 3 |
| | Zig http.zig default | 2,479 | 25,750 | 94,020 | 377.2 + 29.0 = 406.2 | 100% | 23.6 | 34 |
| `POST /nbody` n=256 steps=4 | Vif | **1,447** | 43,870 | 273,020 | 678.8 + 13.8 = **692.6** | 100% | 0.8 | 1 |
| | Zig std.http | 869 | 72,920 | 344,300 | 1,130.5 + 23.0 = 1,153.5 | 100% | 28.2 | 91 |
| | Zig http.zig 1+1 | 854 | 73,890 | **98,050** | 1,132.5 + 40.0 = 1,172.5 | 100% | 4.5 | 3 |
| | Zig http.zig default | 847 | 66,540 | 396,070 | 1,151.1 + 30.7 = 1,181.8 | 100% | 13.8 | 34 |
| `GET /page/50` | Vif | **70,600** | 880 | 1,890 | 3.03 + 10.67 = **13.70** | 97% | 1.3 | 1 |
| | Zig std.http | 50,294 | 1,170 | 2,710 | 3.36 + 16.17 = 19.53 | 97% | 18.8 | 65 |
| | Zig http.zig 1+1 | 46,861 | 1,260 | 3,440 | 3.87 + 17.22 = 21.09 | 98% | 3.9 | 3 |
| | Zig http.zig default | 63,209 | 940 | 2,870 | 3.12 + 12.25 = 15.37 | 98% | 12.7 | 34 |

Idle RSS after startup: Vif 0.3 MiB, std.http 1.0, http.zig 1+1 3.5, http.zig default 11.6 MiB.

- **Hello is limited by the load generator.** One `wrk` thread on one CPU saturates at about
  80k req/s, and Vif's server CPU was only 75% busy. Its run range, 73,862–97,877 req/s, shows the
  noise. CPU per request is the server measure there: Vif needs 1.25–1.51× less than the Zig
  servers. Kernel time is 95% of Vif's per-request cost and about 91% of the Zig servers'.
- **Pipelining.** Vif writes a batch of responses at once. `std.http.Server.Request.respond`
  flushes after every response, so std.http makes one write per request.
- **http.zig does not answer pipelined requests.** At `1bb71ff`, 16 pipelined GETs written in one
  `send` get one response; the other 15 wait until the client sends more bytes. The same happens
  with 2 requests, in both configurations. wrk's pipeline script therefore stalls on it for its 5 s
  timeout (about 32 req/s in a 2 s probe), so it was not measured there.
- **Compute endpoints.** These are CPU-bound, and the gaps follow the compute section: the stencil
  is 1.2× and nbody 1.7× (256 bodies, sequential per request). `/page/50` builds about 5 KB of
  HTML per request.
- **Latency.** Vif's p50 and p99 are lower everywhere except the `POST /nbody` p99. There, http.zig
  with one pool thread has a far tighter tail (98 ms vs Vif's 273 ms), though at 59% of Vif's
  throughput. I did not investigate the cause.
- **Memory.** std.http's peak RSS grows with its thread count (65–91 threads, one per connection).
  http.zig's default configuration starts 34 threads and idles at 11.6 MiB.

## Binary size (bytes)

| Program | Vif (static) | Zig as built | Zig stripped |
|---|---:|---:|---:|
| HTTP server | 78,344 | std.http 4,467,128; http.zig 4,769,936 | 608,504; 648,632 (dynamic, glibc) |
| mandel / stencil / nbody / sieve | 19,456 / 19,832 / 24,224 / 19,680 | 4,070,544 / 4,122,840 / 4,161,736 / 4,102,456 | 507,016 / 513,512 / 529,672 / 511,080 |
| JSON (Vif: library_bench, orders_json) | 129,440 / 140,024 | 4,476,888 (one binary, all modes) | 594,392 |

Zig `ReleaseFast` keeps DWARF by default, and its stripped binaries still carry the threaded `Io`
runtime and the stack-trace panic handler. `ReleaseSmall` or `-fstrip` would shrink them; that was
not measured. Every Zig binary except http.zig's is static.

## Not done

- Rust, Go and Bun were not rerun on this box. Their numbers in the older reports come from
  different machines (8-vCPU EPYC-Rome, ARM64), so set them beside these ratios for orientation only.
- No hand-vectorised or struct-of-arrays Zig variants of mandel or nbody. Those would be Zig tuning
  beyond a straight port of the Rust and Go programs.
- No `std.Io.Uring` (evented) backend for the std.http server. Zig 0.17.0 ships it, but this run
  used the default threaded `Io`.
- No four-worker rows: the box has two vCPUs.
