# Vif vs Zig, round 3: compute and JSON on 2 vCPUs, HTTP on 4 vCPUs (2026-11-02)

This is the third pass on the Zig comparison, after
[the first report](RESULTS-zig-vs-vif-linux-2026-11-01.md) and
[round 2](RESULTS-zig-vs-vif-linux-2026-11-01-r2.md). Round 2 left one loss: HTTP hello
requests per second, 0.99× against http.zig. That row was measured with `wrk -t1` on the other
vCPU of a 2-vCPU box. This round shows that the setup measured the load generator, not the
servers, and moves the HTTP rows to a 4-vCPU box where every server is the bottleneck. It also
re-runs the compute and JSON rows on the final tree, which adds loop alignment to the compiler.

**Result: Vif wins every compute, JSON and HTTP row of the headline table.** The compute and
JSON rows run on the 2-vCPU box as before; the HTTP rows run on the 4-vCPU box, where every
server is the bottleneck. Read these first:

- **2-vCPU hello.** The table's last, italic row is the old client-bound 2-vCPU hello, and Vif
  does not win it. In that setup http.zig default still completes more hello requests per second
  than Vif: 85,422 against 81,447 (0.95×) on today's box. That number is the load generator's
  ceiling, set by what each server costs the client per request (see "Hello"). It is reported,
  not counted as a server result.
- **Huge pages.** The 50M stencil and sieve margins depend on transparent huge pages being
  available.
- **Loop alignment.** It makes the sieve independent of code placement. It may cost the JSON
  document workload up to about 3%; the two measurements disagree (0% and 2.6%).

Raw data, versions, binary hashes and the scripts: `bench/zig/results/2026-11-02-vultr-r3/`
(`2c-box38/` and `4c-box39/`). Nothing is committed.

## Environment

Both boxes were temporary Vultr instances in Amsterdam, created for this run and destroyed
afterwards. Both report an AMD EPYC-Milan CPU; round 2's box was an EPYC-Genoa, so today's
absolute numbers are not comparable with round 2's.

| | Compute, JSON, 2-vCPU hello diagnosis | HTTP rows |
|---|---|---|
| Instance | `voc-c-2c-4gb-50s-amd`, id 38 | `voc-c-4c-8gb-75s-amd`, id 39 |
| CPU | AMD EPYC-Milan, 2 vCPUs = 1 core × 2 SMT threads (`thread_siblings_list` 0-1) | AMD EPYC-Milan, 4 vCPUs = 2 cores × 2 SMT threads (0-1, 2-3) |
| RAM | 4 GB | 8 GB |
| Pinning | 1 worker on CPU 0, 2 workers on CPUs 0–1 | server on CPU 0 (its SMT sibling, CPU 1, idle); wrk on CPUs 2–3 |

Software was the same on both boxes:

- Ubuntu 24.04.5, Linux 6.8.0-146-generic.
- Transparent huge pages at Ubuntu's defaults: `enabled=madvise`, `defrag=madvise`.
- Ubuntu clang 18.1.3, wrk 4.1.0 (Debian 4.1.0-4build2, epoll), Python 3.12.3, GNU time.
- Go 1.25.1 and Bun 1.4.4 on the 2-vCPU box, for the `bench/run.py` workloads and the suite.
- **Zig 0.17.0**: the official `zig-x86_64-linux-0.17.0.tar.xz`, SHA-256 checked. `bench/zig`
  requires at least 0.17.0. It was rebuilt on each box with an empty cache.
  - The main column is `-Doptimize=ReleaseFast -Dcpu=baseline`; "Zig native" is `-mcpu=native`.
  - http.zig is pinned to master `1bb71ff`.

Three builds of Vif were measured:

- **Vif after**: this checkout's working tree. That is commit `9b9aa2d`, the uncommitted
  language spike patch, the prover fix and the changes of rounds 2 and 3.
- **Vif before**: the same tree with every round-2/3 change reverted.
  - `runtime/core.ax`, `runtime/http_uring.ax`, `runtime/http_linux.ax` and the three platform
    files come from `HEAD`.
  - `axonc/llvm.py` and `axonc/cli.py` keep everyone else's edits but lose mine.
  - The overlays are produced by `scripts/mkvariants.py`.
- **Single-change variants** for the hello regression check, each reverting one change from Vif
  after:
  - `pollfirst`: receive with `IORING_RECVSEND_POLL_FIRST` again.
  - `accept1`: one accept per listener event.
  - `nocore`: no parked block and no huge-page advice.
  - `noalign`: no `-falign-loops=32`.
  - `nollvm`: no private-heap preset and no bounded-sum `add nsw`.

Every Vif binary was built with `./axon build X.ax -o X --no-cache` (LLVM `-O3`) and is a static
ELF. HTTP used the x86-64 default backend, io_uring, unless the row says epoll. The HTTP server
does not get the private-heap preset: its IR has `@ax_default_heap_mode = 0`.

## Headline

Ratio = baseline Zig time / Vif time (above 1.00× means Vif is faster). For HTTP it is Vif req/s
divided by the best Zig server's req/s. "Best Zig" is the fastest `-Dcpu=baseline` Zig variant
for that row; the compute section also gives the native ratios, and Vif wins those too.

| Workload | Box | Vif before | **Vif after** | Best Zig | **Ratio** |
|---|---|---:|---:|---:|---:|
| mandel 1200×1200×300, 1 worker | 2 vCPU | 145.2 ms | **145.5 ms** | 203.4 ms | **1.40×** |
| mandel, 2 workers | 2 vCPU | 74.1 ms | **73.8 ms** | 102.6 ms | **1.39×** |
| stencil 1M×20, 1 worker | 2 vCPU | 36.1 ms | **30.7 ms** | 37.6 ms | **1.23×** |
| stencil 1M×20, 2 workers | 2 vCPU | 32.7 ms | **28.4 ms** | 38.3 ms | **1.35×** |
| stencil 50M×20, 1 worker | 2 vCPU | 6,167.5 ms | **1,420.7 ms** | 1,776.6 ms | **1.25×** |
| stencil 50M×20, 2 workers | 2 vCPU | 5,805.4 ms | **802.4 ms** | 1,105.5 ms | **1.38×** |
| nbody 1024×3, 1 worker | 2 vCPU | 11.7 ms | **11.8 ms** | 17.8 ms | **1.51×** |
| nbody 1024×3, 2 workers | 2 vCPU | 7.2 ms | **7.1 ms** | 11.5 ms | **1.62×** |
| nbody 4096×10, 1 worker | 2 vCPU | 377.9 ms | **377.1 ms** | 686.7 ms | **1.82×** |
| nbody 4096×10, 2 workers | 2 vCPU | 195.4 ms | **194.3 ms** | 353.3 ms | **1.82×** |
| sieve 1e8, 1 worker | 2 vCPU | 549.6 ms | **439.0 ms** | 511.9 ms | **1.17×** |
| sieve 1e8, 2 workers | 2 vCPU | 541.6 ms | **428.5 ms** | 494.4 ms | **1.15×** |
| JSON small document ×1M | 2 vCPU, CPU 0 | 188.1 ms | **188.1 ms** | 333.7 ms (typed, arena) | **1.77×** |
| JSON 1,000 orders ×1,000 | 2 vCPU, CPU 0 | 189.9 ms | **186.6 ms** | 218.3 ms (typed, arena) | **1.17×** |
| HTTP hello, req/s | 4 vCPU | 104,428 | **108,829** | 74,414 (http.zig default) | **1.46×** |
| HTTP hello, CPU per request | 4 vCPU | 9.54 µs | **9.19 µs** | 13.39 µs (http.zig default) | **1.46×** |
| HTTP 16-deep pipelining, req/s | 4 vCPU | 1,428,824 | **1,426,310** | 100,985 (std.http) | **14.1×** |
| HTTP `/smooth/10000`, req/s | 4 vCPU | 2,868 | **2,880** | 2,381 (std.http) | **1.21×** |
| HTTP `POST /nbody` 256×4, req/s | 4 vCPU | 1,330 | **1,329** | 796 (std.http) | **1.67×** |
| HTTP `POST /nbody`, p99 | 4 vCPU | 298.5 ms | **49.8 ms** | 113.2 ms (http.zig 1+1) | **2.3× lower** |
| HTTP `/page/50`, req/s | 4 vCPU | 67,113 | **68,508** | 53,952 (http.zig default) | **1.27×** |
| *2-vCPU hello, req/s (client-bound, not a server result)* | *2 vCPU* | *81,236* | *81,447* | *85,422 (http.zig default)* | *0.95×* |

Every Vif HTTP row runs on one worker thread (`AXON_THREADS=1`). Every server, of any thread
count, is confined to CPU 0 and used 1.00 CPU in every row, so all have the same CPU budget.
The HTTP rows are medians of 11 rounds; the compute rows of 7 and the JSON rows of 9.

## Hello: what the 2-vCPU setup measured

The 2-vCPU method ran the server pinned to CPU 0 with one worker and `wrk -t1 -c64` pinned to
CPU 1. Today's box was checked first (`2c-box38/meta-2c.txt`): CPU 0 and CPU 1 are the two SMT
threads of one physical core (`thread_siblings_list` 0-1, one `core_id`). Pinning therefore
cannot separate client from server: they share one core's execution units and caches.

Every server and every single-change variant was then measured in 13 interleaved rounds, with
order alternating (`2c-box38/hello-2c-variants.txt` and `.json`).

- **Client CPU** is wrk's user + system time over the measured 10 s (`getrusage`), in CPUs.
- **Server CPU** is the server session's time over the same 10 s (`/proc`).
- **Busy** is each vCPU's non-idle share over the same 10 s (`/proc/stat`).

| Server (2 vCPU) | req/s | Range | p50 µs | p99 µs | Server CPU µs/req | Server CPUs | wrk CPUs | Busy CPU 0 / 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Vif after | 81,447 | 80,640–85,914 | 394 | 773 | 10.29 | 0.84 | 0.99 | 0.86 / 1.00 |
| Vif before | 81,236 | 78,284–92,482 | 394 | 779 | 10.04 | 0.82 | 0.99 | 0.84 / 1.00 |
| `pollfirst` | 81,770 | 79,141–89,748 | 394 | 776 | 10.06 | 0.81 | 0.99 | 0.84 / 1.00 |
| `accept1` | 81,906 | 79,087–89,771 | 392 | 786 | 10.19 | 0.83 | 0.99 | 0.86 / 1.00 |
| `nocore` | 81,573 | 80,697–87,424 | 395 | 773 | 10.25 | 0.83 | 0.99 | 0.86 / 1.00 |
| `noalign` | 81,312 | 78,572–91,783 | 394 | 780 | 10.39 | 0.84 | 0.99 | 0.86 / 1.00 |
| `nollvm` | 81,198 | 77,087–86,600 | 395 | 785 | 10.28 | 0.83 | 0.99 | 0.86 / 1.00 |
| Vif epoll | 82,392 | 81,047–90,015 | 388 | 815 | 10.65 | 0.87 | 0.99 | 0.90 / 1.00 |
| http.zig default | 85,422 | 84,286–96,624 | 606 | 1,450 | 11.64 | 0.99 | 0.99 | 1.00 / 0.99 |
| http.zig 1+1 | 71,826 | 70,224–77,584 | 812 | 2,730 | 13.83 | 0.99 | 0.94 | 1.00 / 0.95 |

What this shows:

- **wrk is the bottleneck.** In every Vif run wrk used 0.99 CPU and its vCPU was 100% busy, while
  the Vif server used 0.81–0.87 CPU. The request rate is therefore wrk's rate. That rate depends
  on how much client CPU each response costs, not on how fast the server is.
- **What decides the row.** wrk spent 0.99 CPU / 81,447 = 12.2 µs per request against Vif and
  11.6 µs against http.zig default. http.zig default keeps its own vCPU 100% busy (34 threads)
  and still has the higher rate. The Vif server uses less CPU per request (10.29 against 11.64
  µs).
- **What this run does not show.** One hypothesis was that slower servers make wrk cheaper
  through bigger epoll batches. Round 3's counters on the Genoa box (box 36, whose raw files were lost) contradict it: wrk
  made 0.030 `epoll_wait` calls per request against Vif (about 62 events per call), and
  0.039–0.040 against http.zig. Other client-side counters from round 3:
  - Both servers: 2.0 TCP segments per request (one segment per response) and no delayed ACKs.
  - Both servers: one `read`, one `write` and two `epoll_ctl` per request in wrk.
  - On the client's vCPU, 48–51k kernel cycles per request with Vif and 44–45k with http.zig.
    The waking of the server (io_uring task work against epoll's callback) and 0.10–0.12
    wake-up IPIs per request to the idle server vCPU account for part of that difference.
  - Keeping the server's vCPU out of idle with a spinner did not recover it.
  - I have no server change that lowers wrk's cost per request without slowing the server, so I
    did not chase this row further.
- **No regression from the round-2/3 changes.** Vif after, Vif before and every single-change
  revert lie within 81,198–81,906, against run ranges of ±5–10%. The round-3 final run measured 77,477
  (after) against 87,314 (before) over 5 rounds, which is consistent with this noise: before's own
  range here is 78,284–92,482. The server-bound 4-vCPU check below agrees. Nothing was reverted.

## HTTP method change and why

A server benchmark should be limited by the server. The 4-vCPU setup does that, with the same
CPU budget for every server:

- The server is pinned to CPU 0, one SMT thread of the first core. Its sibling, CPU 1, stays idle
  (0.02 busy), so the server has the core's execution units to itself.
- `wrk -t2 -c64` runs on CPUs 2–3, the other physical core. The connection count is unchanged.
- Every server, whatever its thread count, runs under `taskset -c 0`. That is one vCPU each.
- Everything else is as before: a fresh server per run, 2 s warm-up, 10 s measured,
  `--latency --timeout 5s`, alternating order, and the references validated before measuring.
  The only other change is 11 rounds instead of 5.
- The data confirms it, per row (`4c-box39/http-4c.txt`):
  - Every server used 1.00 CPU in every scenario.
  - wrk's median use was at most 1.40 of its 2 CPUs (hello with Vif; 1.41 in the variant runs
    below), and its vCPUs were 59–73% busy.
  - The server is therefore the limit in every run, and the client has spare capacity at the
    highest rate measured.

The layout follows from the CPU-use data above, not from the rates. The same layout was already
used for round 3's supplementary 4-vCPU hello on box 37.

`run_http.py` now takes `WRK_THREADS` (default 1) and records `client_cpu` and `server_cpu` for
every run. The defaults reproduce the 2-vCPU method, so earlier runs remain reproducible.

## HTTP (4 vCPU: server on CPU 0, wrk -t2 -c64 on CPUs 2–3; medians of 11 × 10 s)

| Scenario | Server | req/s | Run range | p50 µs | p99 µs | CPU µs/req (user + kernel) | Server CPUs | wrk CPUs | Peak RSS MiB | Threads |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `GET /` | **Vif after** | **108,829** | 105,053–114,061 | 573 | 816 | 0.18 + 9.01 = **9.19** | 1.00 | 1.40 | 0.8 | 1 |
| | Vif before | 104,428 | 99,577–116,165 | 599 | 759 | 0.16 + 9.38 = 9.54 | 1.00 | 1.37 | 0.8 | 1 |
| | Zig std.http | 58,427 | 58,038–61,972 | 1,080 | 1,850 | 0.95 + 16.16 = 17.10 | 1.00 | 1.11 | 18.0 | 65 |
| | Zig http.zig 1+1 | 55,240 | 53,088–56,916 | 1,020 | 3,950 | 1.37 + 16.81 = 18.18 | 1.00 | 0.93 | 3.7 | 3 |
| | Zig http.zig default | 74,414 | 74,071–76,796 | 846 | 3,000 | 0.69 + 12.71 = 13.39 | 1.00 | 1.14 | 12.3 | 34 |
| `GET /`, 16 pipelined | **Vif after** | **1,426,310** | 1,386,651–1,594,165 | n/a | n/a | 0.13 + 0.57 = **0.70** | 1.00 | 1.38 | 0.8 | 1 |
| | Vif before | 1,428,824 | 1,374,348–1,499,821 | n/a | n/a | 0.12 + 0.58 = 0.70 | 1.00 | 1.37 | 0.8 | 1 |
| | Zig std.http | 100,985 | 99,370–110,911 | n/a | n/a | 0.50 + 9.39 = 9.89 | 1.00 | 0.74 | 18.0 | 65 |
| | Zig http.zig (both) | stalls | | | | | | | | |
| `GET /smooth/10000` | **Vif after** | **2,880** | 2,830–2,918 | 21,780 | 27,640 | 337.4 + 9.2 = **346.7** | 1.00 | 0.05 | 1.4 | 1 |
| | Vif before | 2,868 | 2,794–2,893 | 22,020 | 34,160 | 339.0 + 9.5 = 348.5 | 1.00 | 0.05 | 1.0 | 1 |
| | Zig std.http | 2,381 | 2,324–2,407 | 26,590 | 36,670 | 399.5 + 20.0 = 419.5 | 1.00 | 0.08 | 33.7 | 66 |
| | Zig http.zig 1+1 | 2,351 | 2,326–2,383 | 26,870 | 31,280 | 396.6 + 28.8 = 425.3 | 1.00 | 0.09 | 13.2 | 3 |
| | Zig http.zig default | 2,316 | 2,253–2,344 | 27,090 | 101,800 | 406.9 + 25.5 = 432.4 | 1.00 | 0.07 | 23.8 | 34 |
| `POST /nbody` n=256 steps=4 | **Vif after** | **1,329** | 1,321–1,335 | 47,850 | **49,810** | 740.7 + 12.8 = **753.6** | 1.00 | 0.02 | 1.3 | 1 |
| | Vif before | 1,330 | 1,325–1,334 | 47,830 | 298,480 | 738.4 + 14.3 = 752.7 | 1.00 | 0.03 | 0.8 | 1 |
| | Zig std.http | 796 | 790–802 | 79,460 | 349,280 | 1,232.1 + 23.9 = 1,256.0 | 1.00 | 0.03 | 34.6 | 103 |
| | Zig http.zig 1+1 | 786 | 780–791 | 79,990 | 113,190 | 1,228.7 + 43.5 = 1,272.3 | 1.00 | 0.03 | 4.4 | 3 |
| | Zig http.zig default | 778 | 773–781 | 74,930 | 401,740 | 1,243.3 + 43.6 = 1,286.9 | 1.00 | 0.04 | 13.7 | 34 |
| `GET /page/50` | **Vif after** | **68,508** | 66,266–73,152 | 930 | 1,190 | 3.14 + 11.32 = **14.46** | 1.00 | 0.92 | 1.3 | 1 |
| | Vif before | 67,113 | 63,137–69,571 | 940 | 1,200 | 3.32 + 11.57 = 14.88 | 1.00 | 0.92 | 1.3 | 1 |
| | Zig std.http | 45,553 | 44,997–47,234 | 1,380 | 2,260 | 3.10 + 18.86 = 21.96 | 1.00 | 0.92 | 18.8 | 65 |
| | Zig http.zig 1+1 | 43,486 | 43,179–44,513 | 1,400 | 4,260 | 3.19 + 19.79 = 22.98 | 1.00 | 0.80 | 3.7 | 3 |
| | Zig http.zig default | 53,952 | 53,066–55,416 | 1,140 | 3,510 | 2.86 + 15.71 = 18.57 | 1.00 | 0.90 | 12.6 | 34 |

All servers passed the `compare.py` references and the byte-for-byte `/page/50` check against
React before measuring. No run had socket errors or non-2xx responses.

http.zig answers only the first request of a pipelined write, so the pipelining row is not run
against it, as in earlier rounds. The `POST /nbody` p99 confirms round 2's accept change on a
second machine: 298 ms before, 50 ms after.

**Thread counts and CPU budget.** Vif runs one thread on every row. std.http runs 65–103
threads, http.zig default 34 and http.zig 1+1 3. All of them are confined to CPU 0 and used 1.00
CPU on every row, so no server had more CPU than another. http.zig 1+1 is its configuration
closest to Vif's single worker; the default is its out-of-the-box configuration. Vif wins
against both on every row.

**Hello variants on the 4-vCPU box** (server-bound, 11 interleaved rounds,
`4c-box39/hello-4c-variants.txt`). This is the regression check where the server is the limit:

| Variant | req/s | Range | p50 µs | p99 µs | Server CPU µs/req | wrk CPUs |
|---|---:|---:|---:|---:|---:|---:|
| Vif after | 106,033 | 103,808–115,068 | 582 | 788 | 9.42 | 1.40 |
| Vif before | 105,624 | 100,311–120,065 | 588 | 743 | 9.46 | 1.38 |
| `pollfirst` | 105,840 | 101,413–118,475 | 592 | 762 | 9.34 | 1.38 |
| `accept1` | 107,506 | 80,245–113,767 | 561 | 840 | 9.29 | 1.41 |
| `nocore` | 104,648 | 98,357–111,327 | 579 | 870 | 9.52 | 1.39 |
| Vif epoll | 89,259 | 85,950–91,562 | 719 | 880 | 11.18 | 1.31 |
| http.zig default | 75,539 | 74,079–83,217 | 839 | 2,990 | 13.24 | 1.14 |

Server-bound, every io_uring variant lies within 104.6k–107.5k req/s and 9.29–9.52 µs per
request. None of the round-2/3 changes costs hello throughput or CPU. The receive change
(attempt first instead of `POLL_FIRST`) measured +3% req/s and −3% CPU per request on box 37
in round 3. Here it is within noise (106,033 against 105,840), and the comment in
`runtime/http_uring.ax` now says so. It is kept because it costs nothing measurable. The epoll
backend needs 19% more CPU per request than io_uring, which supports keeping io_uring as the
x86-64 default.

Response headers, captured byte for byte from the measured binaries (`4c-box39/headers.txt`),
are unchanged from round 2. Bodies are identical.

| Server | `GET /` header bytes |
|---|---|
| Vif | `HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 13\r\n\r\n` (65 bytes) |
| Zig std.http | `HTTP/1.1 200 OK\r\ncontent-length: 13\r\ncontent-type: text/plain\r\n\r\n` (65 bytes) |
| Zig http.zig | `HTTP/1.1 200 \r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Length: 13\r\n\r\n` (78 bytes) |

For `/page/50` and `/smooth/1000`, Vif sends 81 and 71 header bytes, std.http the same counts
with lower-case names, and http.zig 79 and 84 bytes.

## Compute (2 vCPU; median ms of 7 rounds; peak RSS MiB)

| Case | Workers | Vif after | Zig | Zig native | Zig / Vif | Zig native / Vif | Vif before | Before / after | Peak RSS after / before / Zig |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mandel-1200-1200-300 | 1 | 145.5 | 203.4 | 210.2 | 1.40× | 1.45× | 145.2 | 1.00× | 1.9 / 1.9 / 1.9 |
| stencil-1000000-20 | 1 | 30.7 | 37.6 | 38.8 | 1.23× | 1.26× | 36.1 | 1.18× | 15.3 / 15.2 / 15.9 |
| stencil-50000000-20 | 1 | 1,420.7 | 1,776.6 | 1,861.4 | 1.25× | 1.31× | 6,167.5 | 4.34× | 762.9 / 762.9 / 763.6 |
| nbody-1024-3 | 1 | 11.8 | 17.8 | 17.9 | 1.51× | 1.51× | 11.7 | 0.99× | 1.9 / 1.9 / 1.9 |
| nbody-4096-10 | 1 | 377.1 | 686.7 | 684.7 | 1.82× | 1.82× | 377.9 | 1.00× | 1.9 / 1.9 / 1.9 |
| sieve-100000000 | 1 | 439.0 | 511.9 | 502.3 | 1.17× | 1.14× | 549.6 | 1.25× | 95.4 / 95.4 / 96.0 |
| mandel-1200-1200-300 | 2 | 73.8 | 102.6 | 106.9 | 1.39× | 1.45× | 74.1 | 1.00× | 1.9 / 1.9 / 1.9 |
| stencil-1000000-20 | 2 | 28.4 | 38.3 | 36.5 | 1.35× | 1.29× | 32.7 | 1.15× | 15.2 / 15.2 / 16.2 |
| stencil-50000000-20 | 2 | 802.4 | 1,105.5 | 972.9 | 1.38× | 1.21× | 5,805.4 | 7.23× | 762.9 / 763.0 / 763.9 |
| nbody-1024-3 | 2 | 7.1 | 11.5 | 11.4 | 1.62× | 1.59× | 7.2 | 1.01× | 1.9 / 1.9 / 1.9 |
| nbody-4096-10 | 2 | 194.3 | 353.3 | 351.2 | 1.82× | 1.81× | 195.4 | 1.01× | 1.9 / 1.9 / 1.9 |
| sieve-100000000 | 2 | 428.5 | 494.4 | 493.9 | 1.15× | 1.15× | 541.6 | 1.26× | 95.4 / 95.2 / 96.3 |

Every output agreed across variants:

- mandel: 79165632.
- stencil: 499998359740 (1M) and 25000046624222 (50M).
- sieve: 5761455.
- nbody: within 1e-9 relative.

The run ranges of the two closest rows do not overlap:

| Sieve | Vif | Zig |
|---|---:|---:|
| 1 worker | 425.3–449.8 ms | 493.5–522.7 ms |
| 2 workers | 406.3–454.1 ms | 466.6–503.4 ms |

The other ranges are in `2c-box38/compute.json`; `summarize.py` prints them.

One GNU-time run each, made right after the builds (`2c-box38/faults.log`):

| Run | Wall | User | Kernel | Minor faults |
|---|---:|---:|---:|---:|
| stencil 50M, 1 worker, Vif before | 6.17 s | 2.21 s | 3.95 s | 2,050,886 |
| stencil 50M, 1 worker, Vif after (first run, see Caveats) | 2.07 s | 1.37 s | 0.69 s | 1,224 |
| stencil 50M, 1 worker, Zig | 1.76 s | 1.37 s | 0.38 s | 195,487 |
| stencil 50M, 2 workers, Vif before | 5.85 s | 1.86 s | 8.16 s | 2,050,889 |
| stencil 50M, 2 workers, Vif after | 0.83 s | 1.55 s | 0.05 s | 1,737 |
| stencil 50M, 2 workers, Zig | 1.12 s | 1.63 s | 0.45 s | 196,938 |
| sieve 1e8, 1 worker, Vif before / after / Zig | 0.52 / 0.45 / 0.49 s | 0.47 / 0.44 / 0.44 s | 0.04 / 0.00 / 0.04 s | 24,505 / 486 / 24,585 |

## JSON (one CPU; median ms over 9 runs)

| Workload | Vif after | Vif before | Zig Value | Zig typed | Zig Value arena | Zig typed arena | Zig Value native | Zig typed native |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| small document built and decoded ×1M | **188.1** | 188.1 | 676.6 | 355.9 | 636.0 | 333.7 | 695.4 | 342.1 |
| 1,000-order array decoded ×1,000 | **186.6** | 189.9 | 1,060.6 | 252.8 | 448.5 | 218.3 | 1,091.3 | 249.9 |

Checksums 513500000 and 34327000 match in every variant, and every process peaks at 1.9 MiB RSS.

## Loop alignment (`-falign-loops=32`)

Round 3 added `-falign-loops=32` to the x86-64 clang command in `axonc/cli.py`; LLVM's default
loop alignment is 16 bytes. The flag targets the sieve, whose 19-byte marking loop is slow when
it starts 48 bytes into a 64-byte line.

**Placement provocation** (`2c-box38/placement.txt`). The sieve's IR was compiled 16 times:

- with N = 0, 8, …, 56 bytes of NOPs at `main`'s entry (executed once), which shifts every loop
  in `main`;
- each with LLVM's default 16-byte loop alignment (a16) and with `-falign-loops=32` (a32).

The table gives medians of 7 interleaved runs, in ms.

| NOP bytes | a16 loop offset in 64 B | a16, 1 worker | a16, 2 workers | a32 loop offset | a32, 1 worker | a32, 2 workers |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 441.3 | 429.5 | 0 | 442.8 | 435.8 |
| 8 | 0 | 443.1 | 430.9 | 0 | 443.4 | 426.7 |
| 16 | 16 | 445.0 | 438.7 | 32 | 439.6 | 440.3 |
| 24 | 16 | 440.1 | 431.9 | 32 | 440.5 | 432.0 |
| 32 | 32 | 440.9 | 428.2 | 32 | 441.8 | 432.3 |
| 40 | 32 | 445.3 | 430.3 | 32 | 448.5 | 421.6 |
| 48 | **48** | **484.8** | **468.1** | 0 | 445.5 | 429.5 |
| 56 | **48** | **473.4** | **460.5** | 0 | 444.4 | 424.2 |
| Zig (baseline) | | 507.4 | 489.5 | | 507.4 | 489.5 |

- **With the flag**, every provoked placement measured 439.6–448.5 ms with 1 worker and
  421.6–440.3 ms with 2. That is at least 1.13× and 1.11× ahead of Zig.
- **Without the flag**, the two placements at offset 48 lose 7–10%. They still beat Zig, but
  only by 1.05×.
- The same pattern was measured on box 37 (EPYC-Milan) in round 3.

**Cost elsewhere** (`2c-box38/align-ab.txt`; "align16" is the final tree without the flag,
interleaved medians in ms):

| Workload | align32 (final) | align16 | Vif before (align16) |
|---|---:|---:|---:|
| JSON document ×1M, 15 runs | 187.5 | 182.8 | 183.6 |
| JSON orders ×1,000, 15 runs | 186.5 | 184.9 | 189.4 |
| sieve, 1 worker, 11 runs | 457.2 | 450.5 | |
| sieve, 2 workers, 11 runs | 438.7 | 437.2 | |
| stencil 50M, 1 worker, 7 runs | 1,426.1 | 1,430.7 | |

- **JSON document.** This dedicated A/B measured 2.6% slower with the flag, with overlapping
  ranges (185.3–204.4 against 179.2–197.0). The 9-round JSON suite above measured no
  difference: 188.1 ms after and before.
- **Sieve.** In its default placement the sieve is already at a fast offset, so the flag gains
  nothing there and is within noise.
- **HTTP.** The `noalign` variant's hello lies within the other variants' spread (81,312
  against 81,447 req/s on 2 vCPUs).
- **Verdict.** I kept the flag. It removes a 7–10% placement cliff from every hot loop, at a
  cost of 0–3% on the JSON document workload, which remains a 1.77× win.

## Other Vif workloads

The `bench/run.py` compute workloads (its Rust/Go comparison) used both CPUs and the default
worker count. Each is the median of 7 runs (5 for nbody), run with `ab.py` (`2c-box38/runpy.txt`).
Go 1.25.1 is for reference; Rust was not rebuilt.

| Workload | Vif after | Vif before | Go |
|---|---:|---:|---:|
| mandel 3000×3000×2000 | 2,628.6 ms | 2,627.1 ms | 3,923.4 ms |
| stencil 50M×20 | 798.6 ms | 5,758.6 ms | 1,326.5 ms |
| stencil 1M×2000 | 1,604.6 ms | 1,678.2 ms | 2,787.5 ms |
| nbody 16384×10 | 3,035.9 ms | 3,050.2 ms | 9,605.7 ms |

Apart from the 50M stencil, the differences are within the run ranges. The 1M stencil, for
example, ran 1,500.9–1,946.2 ms after and 1,381.2–1,730.9 ms before. No regression. (The first
attempt in `2c-box38/job.log` could not find the Go binaries; `scripts/runpy2.sh` is the rerun
reported here.)

## Memory

**A VifDB-like allocation pattern** (`scripts/alloc_pattern.ax`, the same program as round 2).
Peak RSS is GNU time `%M` (`2c-box38/rss-alloc-pattern.log`), before → after:

| Arguments (docs, rounds, temporary elements) | 1 worker | 2 workers | Minor faults, 1 worker | Wall, 1 worker |
|---|---:|---:|---:|---:|
| 20000 40 0 | 119,388 → 119,444 KiB | 119,384 → 119,264 KiB | 148,957 → 29,360 | 0.38 → 0.14 s |
| 20000 40 10000000 | 197,464 → 197,532 KiB | 197,520 → 197,556 KiB | 930,236 → 51,574 | 2.76 → 0.93 s |
| 2000 400 0 | 128,460 → 128,412 KiB | 128,276 → 128,460 KiB | 1,365,238 → 149,849 | 3.51 → 0.91 s |
| 50000 24 20000000 | 302,536 → 302,584 KiB | 302,408 → 302,580 KiB | 1,099,606 → 48,955 | 3.09 → 1.08 s |

- The largest difference is +184 KiB (0.14%), within the 64 KiB slab-chunk granularity per heap
  kind; two cells went down.
- A first attempt in `job.log` used a copy of the program with an operator-precedence mistake
  (round 2's draft) and timed out. Only the corrected rerun is reported.

**HTTP server.** Every Vif row's peak RSS is in the HTTP table, 0.8–1.4 MiB, the same as in round
2. As in round 2, the two slow endpoints peak 0.4–0.5 MiB higher after than before. The likely
cause is round 2's accept change: new connections are accepted while the warm-up's connections
are still draining. Every Zig server peaks at 3.7–34.6 MiB.

## Caveats

- **Huge pages.** The 50M stencil and sieve wins depend on transparent huge pages being
  available to the private heap's large blocks (`MADV_HUGEPAGE`, under Ubuntu's
  `enabled=madvise`).
  - In the measured rounds the arrays got them: about 1,200 faults for the 50M stencil against
    Zig's 195,000 (`2c-box38/faults.log`).
  - The single GNU-time run made right after the builds also got huge pages (1,224 faults), but
    spent 0.69 s in the kernel. With `defrag=madvise` the kernel compacts memory synchronously
    for advised regions, and memory was full of build page cache. That run took 2.07 s against
    Zig's 1.76 s; the measured rounds settled at 1,421 ms against 1,777 ms.
  - Round 2 measured the 1-worker 50M stencil with 4 KiB pages only at 1.71 s against Zig's
    1.66 s, a tie. That figure was taken while developing, with the parked block and private
    heap in place.
  - On a system with THP disabled, or under memory fragmentation, those two rows may be a tie or
    a loss. No THP-disabled rerun was made.
- **Sieve placement.** Without loop alignment, the sieve is 7–10% slower when its marking loop
  starts 48 bytes into a 64-byte line. `-falign-loops=32` (round 3) removes that;
  see the placement table above. Today's default build happens to sit at a fast placement either
  way.
- **JSON document workload with loop alignment.** The dedicated A/B measured 2.6% slower (187.5
  against 182.8 ms); the main JSON run measured no difference. It remains a 1.77× win.
- **CPU model.** Both boxes are EPYC-Milan, round 2's was EPYC-Genoa. Absolute times are not
  comparable across rounds; the ratios are the closer comparison, but they can shift with the
  CPU too.
- **2-vCPU hello.** Reported above as a client-bound number (0.95×), not as a server
  comparison.

## Changes since round 2

No benchmark program, workload, output, wrk connection count or response byte changed.

- `runtime/http_uring.ax`: receives are attempted when submitted instead of with
  `IORING_RECVSEND_POLL_FIRST` (round 3). Today only the comment changed, to report both
  measurements.
- `axonc/cli.py`: `-falign-loops=32` for x86-64 targets (round 3).
- `tests/fixtures/allocator_cache.ax`: rewritten for the parked-block design (round 3). It covers
  both heap kinds and checks:
  - the parking slot after a free, and reuse of the same class;
  - replacement of the parked block;
  - eviction by a mapping of another class and by a slab refill;
  - free-list reuse under the 64 MiB cap;
  - independence of the two kinds, and the fork reset.
- `README.md`: the allocator paragraph now describes the class lists, the parked block, the
  huge-page advice and the private heap of thread-only programs (round 3).
- `bench/zig/run_http.py`:
  - the optional `Vif epoll` variant (`VIF_EPOLL=1`, round 3);
  - `WRK_THREADS`, and the per-run `client_cpu` and `server_cpu` (today).

Round 2's changes stay in place unchanged:

- `runtime/core.ax` and the three platform files: the parked large block, huge-page advice.
- `runtime/http_uring.ax` and `runtime/http_linux.ax`: accept every pending connection.
- `axonc/llvm.py`: the private-heap preset and bounded-sum `add nsw`.

## Verification

The full suite ran on the 2-vCPU box on the final tree (`2c-box38/suite.txt` and
`suite-axon-test-tail.log`):

- `./axon test` exited 0.
- The Python suite (`unittest discover`): 173 tests OK.
- Native cases: 37, 0 failed. That includes `bounded-large-buffer-reuse`, the rewritten
  `tests/fixtures/allocator_cache.ax`, which failed before round 3.
- `tests/integration.py`: every script passed, including the Bun tests (31 tests).

Before measuring, every compute and JSON output and every HTTP response was checked against the
references. The only source change made after this suite run is the comment in
`runtime/http_uring.ax`; `./axon check examples/http.ax` passes for the macOS, x86-64 Linux and
AArch64 Linux targets.

## Boxes

Instances 38 (2 vCPU) and 39 (4 vCPU) were created for this round and destroyed after their
results were copied back. Each was destroyed with `instance_destroy`, which returned
`"destroyed": true`. Afterwards, the Vultr connection's read-only `list_instances` returned 0
instances.
`instance_compare_provider` now answers "instance not found" for both ids, because destroying
removes the Instances row. Box 36, round 3's final-run box, was deleted by hand during that run,
and its raw files were lost; this round replaces its results.
