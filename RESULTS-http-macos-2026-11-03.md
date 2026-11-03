# HTTP: kqueue workers, macOS ARM64 (2026-11-03)

The goal was for Neo's multi-worker HTTP server on macOS to beat Rust (hyper/tokio) in throughput and in CPU per
request, without a worse tail latency, and to keep the single-worker wins. This round replaces the macOS
worker loop (`poll`) with one kqueue per worker process and changes how a burst of connections is accepted.
Linux code is unchanged.

**Outcome.** On the three I/O-bound multi-worker rows, Neo now uses 1.58–1.77× less CPU per request than Rust.
Before, it used 1.28× less, 1.21× *more* and 1.39× less. Throughput on those rows is still 1–3% below Rust's
(medians; Neo was ahead in 1 of the 9 row-rounds), so the throughput target is **not** met. The gap is in
per-request latency, not server CPU (see "What remains"). The one-worker heavy-route p99 dropped from 289 ms
to 20.1 ms. Rust's is 13.8 ms; that gap is per-request compute, because neoc's stencil code generation
regressed after 2026-10-23, outside this change. A one-line neoc change from the arm64 compute work, measured
here but not on main, closes most of that compute gap (see "The stencil with NEON vectorization"). The
single-worker hello row stays ahead of Rust. No run in this comparison had a socket error; the first
re-measurement of the old loop had 21 at hello-256.

## Setup

Apple M1 Pro (8 performance + 2 efficiency cores), 16 GiB, Darwin 27.2.0. wrk 4.2.0 (kqueue build) with
4 client threads; client and servers share the machine. Harness: `bench/http/compare.py` with
`--rounds 3 --repeats 1 --duration 5s --warmup 2s --max-load 3 --quiet-timeout 100`. In each round,
every scenario runs every server once, restarted, in a freshly shuffled order (seed 20261023), so servers
interleave in time. Before each server is loaded, its routes are validated against independent Python
references. CPU per request is the user + kernel time of every server process and thread, divided by
completed requests.

- **Neo**: this branch, `examples/http.neo` built by the harness.
- **Neo (before)**: main at 6e18e65 (the `poll` loop), built the same way and run in the same rounds.
- **Rust**: hyper/tokio with `pipeline_flush`, default worker threads (10), built from `bench/rust`.
- **Go**: net/http, go1.25.1. **Bun**: 1.3.13.

**Load.** Other sessions were compiling and testing on this machine. Before each run the harness waits up
to 100 s for the one-minute load average to drop to 3, then records the load and the busiest processes and
starts the run anyway. 52 of the 120 runs started at a load of 3 or less; the median was 3.30 and the
highest 14.47 (the very first run). The busiest process before a run was a local user process using about
one core (93 runs), `mediaanalysisd` (21), `corespotlightd` (5) or `suggestd` (1). "Other cores" in the
generated report is the median number of cores the rest of the machine kept busy during each run (host
CPU ticks minus the server, wrk and the harness): 2–4 during the I/O rows, about 1 during the multi-worker
compute rows and about 2 during the one-worker rows. That noise affects every server, and the interleaving
spreads it across them. Every run and the load before it is listed under "Each run and the load before it".

Raw data: `bench/http/results/2026-11-03-015825-native/` (this run; JSON, per-run wrk output and server logs,
binary hashes). Earlier runs: `bench/http/results/2026-11-03-012451-native/` (the same comparison, gated on
idle cores instead of load) and `bench/http/results/2026-11-03-001807-native/` (the first re-measurement of
main, with the harness as it was).

## Results

Medians over the three rounds; p99 shows the worst round in parentheses. The pipelined p50/p99 values from
this wrk build are not valid and are omitted.

### Multi-worker rows

| Scenario | Server | req/s (range) | p50 | p99 (worst) | CPU µs/req |
|---|---|---:|---:|---:|---:|
| hello-64 | **Neo** | 147,515 (147,093–147,587) | 414 µs | 548 µs (574) | 14.51 |
| | Neo (before) | 142,939 (137,800–146,840) | 426 µs | 568 µs (6,690) | 17.98 |
| | Rust | **152,629** (150,237–153,826) | 376 µs | 570 µs (582) | 22.93 |
| | Go | 139,924 | 321 µs | 1,350 µs | 30.68 |
| | Bun | 94,896 | 678 µs | 1,320 µs | 10.37 |
| hello-256 | **Neo** | 150,081 (149,281–152,812) | 1,650 µs | 2,150 µs (2,910) | 14.76 |
| | Neo (before) | 148,992 (146,271–150,034) | 1,610 µs | 2,190 µs (2,270) | 30.38 |
| | Rust | **151,648** (147,514–153,361) | 1,580 µs | 2,160 µs (2,290) | 25.20 |
| | Go | 146,470 | 1,230 µs | 4,580 µs | 30.16 |
| | Bun | 93,932 | 2,800 µs | 3,190 µs | 10.41 |
| pipeline-16 | **Neo** | 2,299,218 (2,297,102–2,304,166) | | | **1.03** |
| | Neo (before) | 2,195,819 (2,125,606–2,252,525) | | | 1.32 |
| | Rust | **2,362,877** (2,346,977–2,391,174) | | | 1.83 |
| | Go | 355,251 | | | 16.42 |
| | Bun | 32,411 | | | 30.31 |
| smooth-10000-default | **Neo** | 25,471 (25,308–25,882) | 1,900 µs | 7,770 µs (8,420) | 354.05 |
| | Neo (before) | 25,582 (25,289–25,590) | 1,920 µs | 8,350 µs (8,870) | 355.59 |
| | Rust | **35,002** (34,665–35,209) | 1,750 µs | **3,660 µs** (3,870) | **250.70** |
| | Go | 10,609 | 6,290 µs | 30.1 ms | 665.05 |
| | Bun | 857 | 74.1 ms | 77.1 ms | 1176.76 |
| nbody-default | **Neo** | **21,737** (21,017–22,045) | 2,210 µs | 10.4 ms (11.5) | **413.18** |
| | Neo (before) | 21,816 (21,713–21,995) | 2,220 µs | 10.3 ms (11.0) | 416.19 |
| | Rust | 16,704 (16,650–16,775) | 3,690 µs | **8,430 µs** (8,710) | 547.22 |
| | Go | 10,063 | 6,490 µs | 36.8 ms | 741.21 |
| | Bun | 1,060 | 59.7 ms | 67.8 ms | 951.45 |

Bun runs one thread. On the hello rows it uses the least CPU per request of all five servers, while serving
about 0.63× Neo's requests.

### Single-worker rows

| Scenario | Server | req/s (range) | p50 | p99 (worst) | CPU µs/req |
|---|---|---:|---:|---:|---:|
| hello-one-worker | **Neo** | **148,839** (148,479–152,289) | 430 µs | **545 µs** (548) | **6.54** |
| | Neo (before) | 147,396 (146,753–149,538) | 438 µs | 760 µs (762) | 6.74 |
| | Rust | 141,845 (141,414–142,634) | 438 µs | 610 µs (611) | 6.96 |
| | Go | 88,097 | 712 µs | 1,220 µs | 11.23 |
| | Bun | 92,996 | 687 µs | 1,330 µs | 10.69 |
| smooth-1000-one-worker | **Neo** | 29,035 (28,899–29,244) | 2,210 µs | 2,360 µs (2,390) | 34.10 |
| | Neo (before) | 28,931 (28,832–29,053) | 2,190 µs | 4,260 µs (4,260) | 34.25 |
| | Rust | **39,797** (39,491–39,862) | 1,630 µs | **1,770 µs** (1,800) | **24.77** |
| | Go | 17,679 | 3,640 µs | 5,590 µs | 56.47 |
| | Bun | 9,294 | 6,750 µs | 13.2 ms | 108.05 |
| smooth-10000-one-worker | **Neo** | 3,263 (3,237–3,313) | 19.5 ms | 20.1 ms (20.4) | 306.17 |
| | Neo (before) | 3,255 (3,228–3,304) | 19.2 ms | 289.4 ms (293.0) | 306.13 |
| | Rust | **4,886** (4,883–4,892) | 13.2 ms | **13.8 ms** (13.8) | **204.80** |
| | Go | 2,110 | 28.1 ms | 98.8 ms | 475.73 |
| | Bun | 853 | 73.9 ms | 100.5 ms | 1176.67 |

### Neo against Rust

| Scenario | Throughput Neo / Rust | CPU per request Rust / Neo | p99 Neo / Rust | Before: throughput | Before: CPU |
|---|---:|---:|---:|---:|---:|
| hello-64 | 0.97× | 1.58× | 0.96× | 0.94× | 1.28× |
| hello-256 | 0.99× | 1.71× | 1.00× | 0.98× | 0.83× |
| pipeline-16 | 0.97× | 1.77× | n/a | 0.93× | 1.39× |
| smooth-10000-default | 0.73× | 0.71× | 2.12× | 0.73× | 0.71× |
| nbody-default | 1.30× | 1.32× | 1.23× | 1.31× | 1.31× |
| hello-one-worker | 1.05× | 1.06× | 0.89× | 1.04× | 1.03× |
| smooth-1000-one-worker | 0.73× | 0.73× | 1.33× | 0.73× | 0.72× |
| smooth-10000-one-worker | 0.67× | 0.67× | 1.46× | 0.67× | 0.67× |

Above 1.00× is better for Neo in the first two columns; below 1.00× is better in the p99 column.

The earlier run (`2026-11-03-012451-native`, gated on idle cores rather than load) gave the same picture:
throughput 0.97×, 0.98×, 0.97×, 0.73× and 1.22× of Rust on the five multi-worker rows, with 1.44×, 1.62× and
1.68× less CPU per request on the I/O rows. In that run Neo's nbody-default p99 was 16.1 ms, against 11.4 ms
before. A separate 5-round interleaved A/B straight afterwards did not reproduce it (kqueue 9.8 ms, main
10.0 ms, Rust 8.5 ms; `bench/http/results/2026-11-03-macos-ab/nbody/`), and neither did this run (10.4 ms
against 10.3 ms).

### Against the targets

| Target | Result |
|---|---|
| Throughput above Rust on every multi-worker row | **Not met.** hello-64 0.97×, hello-256 0.99×, pipeline-16 0.97×, smooth-10000-default 0.73×; met on nbody-default (1.30×). Before: 0.94×, 0.98×, 0.93×, 0.73×, 1.31×. |
| CPU per request below Rust on every multi-worker row | Met on hello-64 (1.58× less), hello-256 (1.71×), pipeline-16 (1.77×) and nbody-default (1.32×). **Not met** on smooth-10000-default (Neo uses 1.41× more). |
| Heavy-route p99 at or below Rust | **Not met.** One worker: 20.1 ms vs 13.8 ms (before: 289.4 ms). Multi-worker: 7.77 ms vs 3.66 ms (before: 8.35 ms). |
| Keep the single-worker wins | Met: hello-one-worker 1.05× throughput, 1.06× less CPU, p99 545 µs against 610 µs. |

### Each run and the load before it

req/s of each run, with the one-minute load average just before it started (the whole machine, including
the previous run). From `bench/http/results/2026-11-03-015825-native/report.md`.

| Scenario | Round | Neo | Neo (before) | Rust | Go | Bun |
|---|---:|---:|---:|---:|---:|---:|
| hello-64 | 1 | 147,587 @ 12.44 | 137,800 @ 14.47 | 153,826 @ 5.43 | 138,708 @ 5.37 | 98,978 @ 8.78 |
| hello-64 | 2 | 147,515 @ 3.43 | 142,939 @ 2.90 | 152,629 @ 2.86 | 142,952 @ 4.17 | 94,896 @ 2.92 |
| hello-64 | 3 | 147,093 @ 3.45 | 146,840 @ 2.97 | 150,237 @ 2.96 | 139,924 @ 2.95 | 93,943 @ 2.93 |
| hello-256 | 1 | 150,081 @ 4.73 | 148,992 @ 5.20 | 151,648 @ 5.92 | 146,238 @ 4.93 | 100,496 @ 4.25 |
| hello-256 | 2 | 152,812 @ 2.98 | 146,271 @ 2.92 | 153,361 @ 2.87 | 146,470 @ 3.08 | 92,591 @ 2.89 |
| hello-256 | 3 | 149,281 @ 3.19 | 150,034 @ 3.88 | 147,514 @ 4.85 | 151,276 @ 4.90 | 93,932 @ 3.77 |
| pipeline-16 | 1 | 2,299,218 @ 4.60 | 2,252,525 @ 4.40 | 2,391,174 @ 5.22 | 363,646 @ 4.07 | 32,409 @ 3.36 |
| pipeline-16 | 2 | 2,297,102 @ 3.00 | 2,195,819 @ 2.96 | 2,346,977 @ 3.41 | 349,787 @ 2.99 | 32,411 @ 2.87 |
| pipeline-16 | 3 | 2,304,166 @ 3.62 | 2,125,606 @ 3.74 | 2,362,877 @ 2.97 | 355,251 @ 3.75 | 33,202 @ 3.61 |
| hello-one-worker | 1 | 152,289 @ 4.55 | 146,753 @ 3.60 | 141,414 @ 3.69 | 88,802 @ 3.93 | 94,547 @ 4.31 |
| hello-one-worker | 2 | 148,839 @ 2.89 | 147,396 @ 2.87 | 142,634 @ 2.92 | 88,097 @ 2.97 | 92,996 @ 2.93 |
| hello-one-worker | 3 | 148,479 @ 4.26 | 149,538 @ 4.38 | 141,845 @ 4.45 | 88,066 @ 3.32 | 92,804 @ 4.30 |
| smooth-1000-one-worker | 1 | 29,035 @ 2.86 | 28,832 @ 2.84 | 39,862 @ 2.97 | 17,752 @ 2.91 | 9,294 @ 2.98 |
| smooth-1000-one-worker | 2 | 28,899 @ 2.88 | 28,931 @ 2.92 | 39,491 @ 3.39 | 17,679 @ 2.94 | 9,229 @ 2.93 |
| smooth-1000-one-worker | 3 | 29,244 @ 3.53 | 29,053 @ 3.20 | 39,797 @ 2.96 | 17,666 @ 2.98 | 9,315 @ 3.00 |
| smooth-10000-one-worker | 1 | 3,237 @ 4.00 | 3,228 @ 2.87 | 4,892 @ 2.88 | 2,110 @ 2.90 | 853 @ 2.86 |
| smooth-10000-one-worker | 2 | 3,263 @ 2.82 | 3,255 @ 2.85 | 4,883 @ 2.79 | 2,095 @ 2.97 | 850 @ 2.89 |
| smooth-10000-one-worker | 3 | 3,313 @ 3.46 | 3,304 @ 3.21 | 4,886 @ 3.37 | 2,117 @ 3.28 | 856 @ 3.62 |
| smooth-10000-default | 1 | 25,882 @ 2.88 | 25,590 @ 3.67 | 34,665 @ 3.94 | 10,398 @ 4.80 | 843 @ 4.40 |
| smooth-10000-default | 2 | 25,308 @ 3.35 | 25,289 @ 2.89 | 35,002 @ 2.89 | 10,609 @ 2.90 | 857 @ 2.89 |
| smooth-10000-default | 3 | 25,471 @ 4.29 | 25,582 @ 3.24 | 35,209 @ 2.97 | 10,938 @ 3.97 | 858 @ 3.52 |
| nbody-default | 1 | 21,737 @ 3.01 | 21,713 @ 2.94 | 16,650 @ 3.63 | 9,969 @ 2.97 | 1,054 @ 2.97 |
| nbody-default | 2 | 21,017 @ 3.01 | 21,816 @ 4.05 | 16,775 @ 3.34 | 10,063 @ 4.04 | 1,060 @ 8.56 |
| nbody-default | 3 | 22,045 @ 6.48 | 21,995 @ 4.53 | 16,704 @ 5.01 | 10,130 @ 4.29 | 1,060 @ 2.94 |

The load average says little about a single run. Neo's hello-64 runs were 147,587 req/s at a load of 12.44
and 147,093 at 3.45. Rust's hello-256 run at 5.92 was faster than its run at 4.85, which is the one round
of the nine I/O row-rounds where Neo was ahead (hello-256, round 3).

## What changed

`runtime/platform_macos.neo`; `NEO_HTTP_POLL=1` still selects the old loop.

- **One kqueue per worker process.** Filters persist across waits. New connections' registrations are
  queued and submitted with the next wait, so there is one `kevent` call per loop. The read filter stays
  enabled, and the write filter is enabled only for backpressure or for buffered complete requests beyond
  one batch, the same interest rule as the Linux epoll backend. Connection slots are reused from a free list
  and never move, so a filter's `udata` (slot + 3) is valid for the connection's whole life. Every event in
  a batch is handled before any new connection is adopted.
- **No per-loop `getppid`.** Workers watch the parent with `EVFILT_PROC`/`NOTE_EXIT`, so a wait needs no
  timeout.
- **Burst accept.** Connections are still assigned round-robin (connection *c* belongs to worker
  *c* mod *workers*); one accepted by another worker is passed to its owner as `SCM_RIGHTS` over the
  existing notification socketpair. The worker holding the accept turn takes what its listener reports.
  When more than one connection is waiting, it raises a burst flag and wakes every worker, and all of them
  accept until the queue is empty. The old loop accepted one connection per turn and then woke the next
  worker. macOS caps the listen queue at `kern.ipc.somaxconn` (128) and resets connections beyond it, which
  is where the old hello-256 errors came from.
- Accepted sockets inherit `O_NONBLOCK` and `TCP_NODELAY` from the listener on Darwin (verified), so each
  connection costs one `fcntl(FD_CLOEXEC)` and no `setsockopt`.

## Why the old loop lost

- **`poll` is O(connections) on XNU.** The kernel builds and tears down a temporary kqueue for every call.
  The old loop also rebuilt its descriptor array and called `getppid` on every iteration. Multi-worker CPU
  per request at hello-256 fell from 30.38 to 14.76 µs.
- **Heavy-route tail.** The old loop served ready connections in slot order and polled again right after
  answering the last one, before that client had sent its next request. The highest slots were therefore
  skipped every other round. A per-connection probe (64 connections, one worker, `/smooth/10000`) shows slots
  62–63 answered half as often as the others, each waiting two rounds (40 ms). Under wrk the p99 reached
  about 15 rounds (289 ms); the probe shows the mechanism, not that magnitude. kqueue reports readiness in
  arrival order: in the same probe every connection was served every round, with a maximum latency of 29 ms.

## What remains, and why

- **The compute rows are code generation, not HTTP.** Neo's HTTP path runs fewer instructions per request
  than hyper's (38.4k against 55.2k on `/`; table in the next section). The stencil behind `/smooth`
  regressed in neoc after 2026-10-23: the boundary test is now inside the interior loop, with 32-bit
  arithmetic plus sign extension. That is about 18.5 instructions per element instead of 10.5. A Neo binary
  from 2026-10-23 ran 3.38M instructions per `/smooth/10000` request against Rust's 3.41M, measured the same
  way earlier that day (`bench/http/results/2026-11-03-macos-ab/instructions.txt`), and the one-worker p50
  (one round of 64 requests) tracks CPU per request. This was reported to the compiler work and is not
  changed here; the next section measures a candidate fix.
- **Throughput on the I/O rows.** With wrk's closed loop, req/s ≈ connections / latency. At hello-64, Neo's
  p50 is 414 µs and Rust's 376 µs, although Neo spends 8.4 µs less CPU per request. This is not contention:
  in round 2 (loads below 3.5) 7.0 of the 10 cores were busy during Neo's run and 8.8 during Rust's, and the
  p50s were 413 and 376 µs. Rust spends more CPU (3.4 server cores against Neo's 2.1) and answers sooner.
  Each Neo worker is a process blocked in `kevent` that must be woken for its next request. Things tried
  that did not help:
  - spinning on a non-blocking `kevent` before blocking (hello-64: 140.7k req/s at 21.1 µs, against 144.8k at
    14.7 µs without);
  - 4, 6 or 8 workers instead of 10 (small, noisy differences, and the compute rows need every core).
- **Multi-worker tails under contention.** A connection stays with its worker process. When the machine
  preempts that process, its connections wait, whereas tokio's threads take each other's work. This shows in
  the smooth-10000-default p99 (7.77 ms against 3.66 ms; 8.35 ms before).

## The stencil with NEON vectorization

The arm64 compute work has a one-line neoc change that lets Darwin use NEON for i64 array loops, as
Linux ARM64 already does (`neoc/vectorize.py::array_width`, on the arm64 compute branch; it
depends on that branch's vector code generation and is not on main). Built from that branch with this
branch's `runtime/platform_macos.neo` and `runtime/http.neo`, `examples/http.neo` passes the HTTP smoke
test (4 workers), including the checksum routes. These numbers are not part of the comparison above.

Instructions retired per request, one worker, sequential keep-alive client (`/usr/bin/time -l`; requests
per measurement in parentheses). The count includes kernel work, and `/` varies by about 10% between
measurements: the earlier table gave 41,750 for this branch.

| Route | Neo (this branch) | Neo + NEON change | Rust |
|---|---:|---:|---:|
| `/` (20,000) | 38,403 (17.1k cycles) | 38,748 (16.8k) | 55,247 (27.1k) |
| `/smooth/1000` (4,000) | 634,365 (110.0k cycles) | 410,858 (91.6k) | 392,345 (87.4k) |
| `/smooth/10000` (400) | 5,917,721 (945k cycles) | 3,677,756 (754k) | 3,385,757 (688k) |
| `POST /nbody` (400) | 4,677,280 (1.115M cycles) | 4,677,219 (1.116M) | 5,630,278 (1.474M) |

Interleaved, three rounds, same harness code and load gate (`scripts/ab.py`). 26 of the 27 runs started at
a load of 3.34 or less; the patched build's first multi-worker run started at 5.12. Medians:

| Scenario | Server | req/s | p50 | p99 | CPU µs/req |
|---|---|---:|---:|---:|---:|
| smooth-10000-one-worker | Neo | 3,269 | 19.5 ms | 20.2 ms | 305.97 |
| | Neo + NEON change | 4,304 | 14.9 ms | 15.4 ms | 234.59 |
| | Rust | **4,869** | **13.2 ms** | **14.2 ms** | **205.62** |
| smooth-1000-one-worker | Neo | 29,206 | 2,190 µs | 2,350 µs | 33.99 |
| | Neo + NEON change | 35,486 | 1,800 µs | 1,940 µs | 27.71 |
| | Rust | **40,052** | **1,620 µs** | **1,750 µs** | **24.57** |
| smooth-10000-default | Neo | 25,925 | 1,910 µs | 7,540 µs | 355.57 |
| | Neo + NEON change | 32,815 | **1,470 µs** | 6,830 µs | 275.33 |
| | Rust | **35,257** | 1,770 µs | **3,620 µs** | **252.79** |

With the change, Neo reaches 0.88×, 0.89× and 0.93× of Rust's throughput on these rows (from 0.67×, 0.73×
and 0.74×) and uses 1.14×, 1.13× and 1.09× Rust's CPU per request (from 1.49×, 1.38× and 1.41×). It still
runs 5–9% more instructions and 5–10% more cycles per request than Rust, so it does not beat Rust here. In
the multi-worker row its p50 is below Rust's, but its p99 barely moves (7.5 to 6.8 ms, against Rust's
3.6 ms), which fits the per-process tail described above better than compute. `POST /nbody` and
`/` are unchanged by it. Raw data: `bench/http/results/2026-11-03-macos-ab/neon/`.

## Accept bursts and the listen queue

The new smoke test opens 512 connections at once and sends a request on each. When no worker gets a CPU
during the burst, the kernel resets whatever overflows the 128-entry queue, for every server. A Python
listener that does not accept keeps exactly 128; a single-threaded Python accept loop answers 214. 512
non-blocking connects, servers interleaved (`bench/http/results/2026-11-03-macos-ab/bursts.txt`):

| Condition | Neo (10 workers) | Neo (4 workers) | Rust |
|---|---|---|---|
| Machine load 7–9, 12 bursts each | 11 complete; 1 lost 283 | 12 complete | 11 complete; 1 lost 13 (same round) |
| Load around 20 from other sessions, 8 bursts each | 5 complete; 3 lost 15, 29, 98 | not run | 6 complete; 2 lost 3, 256 |
| Servers at background QoS (efficiency cores only), 9 bursts each | 294 answered on average | not run | 264 answered on average |

The smoke test therefore retries connections that were reset and fails on anything else, such as a
connection closed without a full response. On this branch it passed 12 of 12 times at 1, 4 and 10 workers
(load averages 8–10, no retries needed). Without the retry, it failed 2 of 15 runs at load averages of 10–24.

**Tried and not kept:** every worker keeps the listener armed (nginx's default with `accept_mutex off`).
Under starvation it answered a little more of each burst (316 against 294 on average over the same 9
interleaved bursts; noisy). But on connection churn (`wrk -c16 -H 'Connection: close'`, `churn.txt`) it
cost 107 µs of server CPU per connection against 77 for the turn, at 17k against 22k connections/s (Rust:
49 µs, 19k). It is not on this branch.

## Notes for follow-up (outside this change)

- Neo does not send `Connection: close` when it closes after a request that asked for it. A client that pools
  connections, such as wrk, then writes its next request into the closing socket: wrk logged one read error
  per connection in the churn run, and hyper sends the header. This is in `runtime/http.neo`, shared with
  Linux.
- neoc stencil code generation: see above. With the October code, Neo ran as many instructions per
  `/smooth/10000` request as Rust.

## Linux

The runtime change is limited to `runtime/platform_macos.neo`; `runtime/http.neo` changed only in a comment.
`tests/http_smoke.py` gained the 512-connection burst, which also runs on Linux. The full suite (`./neo test`)
and the `.github/workflows/verify.yml` steps ran from this branch's source on a temporary Vultr
`voc-c-2c-4gb-50s-amd` box (x86-64, Ubuntu 24.04, clang 18.1.3, Go 1.22.2, Bun 1.3.13), as root. All passed:

- `./neo test`: 37 native cases, 0 failed. The HTTP smoke test ran io_uring (4 and 1 workers) and epoll
  (4 workers); every 512-connection burst was answered without a retry.
- Empty-root runtime audit (`tests/freestanding_linux_smoke.py`): HTTP PASS from a root containing only the
  executable.
- Reproducible release: two `./neo release` archives identical (sha256 `dbca2bf2…`, 101 files).
- Empty-root language, crypto and TLS (`tests/language_freestanding.py`): PASS; static ELF, no imports.

The box was destroyed, and the provider's instance list no longer shows it.
