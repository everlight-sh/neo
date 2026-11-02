# Vif vs Zig, round 2: compute, JSON and HTTP on a 2-vCPU x86-64 Linux box (2026-11-01)

> Superseded by [round 3](RESULTS-zig-x86-linux-2026-11-02.md): final tree with loop
> alignment, and the HTTP rows re-measured on a 4-vCPU box where the servers, not wrk, are the
> bottleneck.

A second pass on [the morning's Zig comparison](RESULTS-zig-vs-vif-linux-2026-11-01.md). That report
had three Vif losses: the 50M stencil (Zig 3.6–5.5× faster), the sieve (Zig 3–6% faster) and the
HTTP hello request rate (http.zig 3% ahead, with the load generator as the bottleneck). It also
showed a 273 ms p99 for Vif's `POST /nbody`. This round changes the Vif runtime and compiler, not
the benchmarks. Then it reruns every row on a fresh box, with Zig rebuilt there and the previous
Vif ("Vif before") interleaved in every suite.

All but one row are now Vif wins. HTTP hello requests per second is still a narrow loss: http.zig
completed 1.4% more requests per second. The run ranges overlap, and the cause is set out below.

Raw measurements, versions, binary sizes and hashes: `bench/zig/results/2026-11-01-vultr-2c-r2/`.
Nothing is committed.

## Environment

- Temporary Vultr `voc-c-2c-4gb-50s-amd` (instance 34, Amsterdam): 2 dedicated AMD EPYC-Genoa
  vCPUs, 4 GB RAM, Ubuntu 24.04, Linux 6.8.0-146. It was created for this run and destroyed
  afterwards; the Vultr listing shows no instances. Transparent huge pages were left at Ubuntu's
  defaults, `enabled=madvise` and `defrag=madvise`.
- **Vif after**: this checkout's working tree at the end of the round. That is commit `9b9aa2d`
  plus the uncommitted language spike patch, the prover fix in `axonc/check.py` and
  `axonc/linear.py`, and this round's changes. **Vif before**: the same tree with this round's
  files restored. Both used `./axon build X.ax -o X --no-cache` (LLVM `-O3`) with Ubuntu clang
  18.1.3. Every Vif binary is a static ELF with 0 undefined symbols. HTTP used the x86-64
  default, io_uring.
- **Zig**: 0.17.0, the official `zig-x86_64-linux-0.17.0.tar.xz` (SHA-256 checked), rebuilt on
  this box with an empty cache. The main column is `-Doptimize=ReleaseFast -Dcpu=baseline`, and
  "Zig native" is the default `-mcpu=native`. http.zig is pinned to master `1bb71ff`.
- wrk 4.1.0, Python 3.12.3, GNU time; Go 1.25.1 and Bun 1.4.4 for the suites and the
  `bench/run.py` workloads.

## Headline

Ratio = Zig time / Vif time (above 1.00× means Vif is faster). For HTTP it is Vif req/s / Zig
req/s, and Zig CPU per request / Vif CPU per request. "Best Zig" is the fastest baseline Zig
variant for that row. The 11-01 columns are copied from the earlier report (same instance type,
different box). Every other column was measured in this run.

| Workload | 11-01 Vif | 11-01 best Zig | 11-01 ratio | Vif before | **Vif after** | Best Zig | **Ratio now** |
|---|---:|---:|---:|---:|---:|---:|---:|
| mandel 1200×1200×300, 1 worker | 132.9 ms | 186.7 ms | 1.40× | 132.5 ms | **132.1 ms** | 185.4 ms | **1.40×** |
| mandel, 2 workers | 69.5 ms | 96.4 ms | 1.39× | 68.2 ms | **68.7 ms** | 94.6 ms | **1.38×** |
| stencil 1M×20, 1 worker | 34.2 ms | 35.2 ms | 1.03× | 33.5 ms | **28.5 ms** | 34.9 ms | **1.22×** |
| stencil 1M×20, 2 workers | 33.4 ms | 37.0 ms | 1.11× | 33.1 ms | **25.9 ms** | 35.9 ms | **1.38×** |
| stencil 50M×20, 1 worker | 5,982 ms | 1,685 ms | 0.28× | 5,969 ms | **1,310 ms** | 1,674 ms | **1.28×** |
| stencil 50M×20, 2 workers | 5,654 ms | 1,030 ms | 0.18× | 5,594 ms | **747 ms** | 1,030 ms | **1.38×** |
| nbody 1024×3, 1 worker | 10.8 ms | 16.5 ms | 1.52× | 10.8 ms | **10.9 ms** | 16.4 ms | **1.51×** |
| nbody 1024×3, 2 workers | 6.8 ms | 11.7 ms | 1.73× | 6.9 ms | **6.8 ms** | 11.1 ms | **1.64×** |
| nbody 4096×10, 1 worker | 347.2 ms | 630.7 ms | 1.82× | 348.1 ms | **347.8 ms** | 629.4 ms | **1.81×** |
| nbody 4096×10, 2 workers | 180.4 ms | 326.9 ms | 1.81× | 179.1 ms | **182.2 ms** | 324.4 ms | **1.78×** |
| sieve 1e8, 1 worker | 500.7 ms | 487.0 ms | 0.97× | 497.3 ms | **414.3 ms** | 482.6 ms | **1.16×** |
| sieve 1e8, 2 workers | 504.6 ms | 477.9 ms | 0.95× | 497.5 ms | **400.5 ms** | 456.3 ms | **1.14×** |
| JSON small document ×1M | 198.0 ms | 316.8 ms (typed, arena) | 1.60× | 168.6 ms | **169.8 ms** | 308.9 ms (typed, arena) | **1.82×** |
| JSON 1,000 orders ×1,000 | 181.2 ms | 212.7 ms (typed, arena) | 1.17× | 173.8 ms | **173.0 ms** | 203.8 ms (typed, arena) | **1.18×** |
| HTTP hello, CPU per request | 9.87 µs | 12.33 µs (http.zig) | 1.25× | 9.88 µs | **9.88 µs** | 12.31 µs (http.zig) | **1.25×** |
| **HTTP hello, req/s (client-bound)** | 76,236 | 78,593 (http.zig) | 0.97× | 78,306 | **77,966** | 79,080 (http.zig) | **0.99×** |
| HTTP 16-deep pipelining, req/s | 1,004,454 | 105,773 (std.http) | 9.5× | 1,024,730 | **1,041,294** | 105,681 (std.http) | **9.9×** |
| HTTP `/smooth/10000`, req/s | 3,114 | 2,564 (std.http) | 1.21× | 3,099 | **3,124** | 2,583 (std.http) | **1.21×** |
| HTTP `POST /nbody` 256×4, req/s | 1,447 | 869 (std.http) | 1.67× | 1,447 | **1,448** | 870 (std.http) | **1.66×** |
| HTTP `POST /nbody`, p99 | 273.0 ms | 98.1 ms (http.zig 1+1) | | 257.8 ms | **46.3 ms** | 96.9 ms (http.zig 1+1) | |
| HTTP `/page/50`, req/s | 70,600 | 63,209 (http.zig) | 1.12× | 72,800 | **70,858** | 60,373 (http.zig) | **1.17×** |

**What is still lost, and the conditions for the new wins:**

- **HTTP hello req/s is a narrow loss: http.zig default completed 79,080 req/s, Vif 77,966
  (0.99×).** The ranges of the five runs overlap: Vif 75,995–78,791 and http.zig
  78,274–80,778. Vif before measured 78,306 here, and Vif still needs 1.25× less server CPU per
  request.
  - One `wrk -t1` thread on CPU 1 is the bottleneck, and the Vif server was only about 77% busy.
  - Measured on CPU 1, wrk made 4.03–4.07 system calls per request with every server. Its
    sampled kernel profile has the same paths with Vif and http.zig except the server's receive
    wakeup, which runs on the client's CPU: `io_poll_wake` + `__io_req_task_work_add` took 2.0%
    of CPU 1 samples with Vif's io_uring, and `ep_poll_callback` 1.2% with http.zig's epoll. That
    difference is about the size of the gap. Vif's epoll backend (`AXON_HTTP_URING=0`) would use
    the same callback as http.zig, but it was not measured in this round; io_uring is the x86-64
    default because it costs the server less CPU per request.
  - Making the Vif worker wait for 2 or 4 completions, with a 50 µs timeout, did not change the
    rate (medians 79.1k and 77.9k against 78.9k) and was dropped.
  - I found no server-side change that lowers wrk's per-request cost, so this row is not won.
- **The 50M stencil and sieve wins depend on transparent huge pages being available.**
  - In the measured rounds every large array got huge pages: about 1,200 faults instead of
    195,000 for the stencil.
  - A single stencil run made directly after the builds, with 2.8 GB of page cache to reclaim,
    got only partial coverage: 65,101 faults and 1.68 s, the same time as Zig (1.68 s)
    (`faults.log`).
  - With 4 KiB pages only, Vif and Zig were measured at 1.71 s and 1.66 s on the 1-worker
    50M stencil while developing (parked block and private heap, no huge pages). On a system
    with THP disabled, that row would be a tie.
- **Code placement moves the sieve by up to ±6%.** The same marking-loop machine code measured
  411–457 ms depending only on where LLVM placed it. Compiling the identical IR with
  `-falign-loops=32` gave 409–423 ms for every variant. In this run the loop starts on a 64-byte
  boundary (`sieve-mark-loop.txt`), the fast placement. With the slower placement the 1-worker
  sieve would still have been ahead of Zig, by about 5% instead of 16%.
- Small changes against Vif before are within noise: nbody 4096 with 2 workers (+1.7%) and
  `/page/50` (−2.7%). A separate 7-round A/B of `/page/50` gave medians of 73,292 (after) and
  72,471 req/s (before), with overlapping ranges.

## What changed and why

Seven source files changed: `runtime/core.ax`, the three platform files
(`runtime/platform_linux_x86_64.ax`, `runtime/platform_linux.ax`, `runtime/platform_macos.ax`),
`runtime/http_uring.ax`, `runtime/http_linux.ax` and `axonc/llvm.py`. The drivers
`bench/zig/run_cli.py`, `run_http.py` and `summarize.py` also changed, to add an optional
interleaved "Vif before" variant.

No benchmark program, workload, output or wrk setting changed. Checked arithmetic and bounds
proofs are as before. The one place that drops an overflow check does so from a bound the compiler
proves (change 4).

1. **A freed large block is parked instead of unmapped** (`runtime/core.ax`).
   - Before: freed mapped blocks stayed on per-class free lists while all retained blocks of a
     heap kind totalled at most 64 MiB. Anything beyond that was unmapped. Each 50M stencil pass
     (400 MB, in a 512 MiB class) therefore unmapped the old array and first-touched a new one:
     2.05M faults and 3.9 s of kernel time.
   - Now such a block is parked in one slot per heap kind (shared at runtime state 136, private at
     144). The next allocation of the same class takes it back with its pages still resident.
   - Bound: every new allocator mapping (slab refill or large block) first unmaps both parked
     blocks, and parking a block unmaps the one parked before it. Resident memory therefore never
     exceeds what was live just before the free.
   - Forked children forget the slots through the existing `rt_fork` reset of bytes 136–167.
   - The parking paths are `cold fn`. A first version kept them inline; `ax_free` then stopped
     being inlined into callers, and the JSON document workload slowed by 6% (`vif-library_bench`
     shrank by 12 KB). That pass is kept under `discarded-first-pass/` and is not reported here.
   - Measured alone (no huge pages; with 2 workers still on the shared heap): 50M stencil
     6.6 → 1.94 s with 1 worker and 5.9 → 1.20 s with 2; faults 2.05M → 195k, the same as Zig.
2. **Large private managed blocks ask for transparent huge pages** (`runtime/core.ax`, plus
   `rt_advise_huge` in the three platform files).
   - A private managed block of 4 MiB or more gets `madvise(MADV_HUGEPAGE)` over the 2 MiB-aligned
     regions that its requested bytes cover entirely. The partial region at the end keeps 4 KiB
     pages.
   - A managed array writes every element when it is created, so those regions would be resident
     anyway, and the measured peak RSS is unchanged (see Memory).
   - Raw `ax_alloc` buffers are never advised; the Darwin version is a no-op. Zig's page allocator
     does not request huge pages, so under the same `madvise` setting its arrays use 4 KiB pages.
   - Effect: stencil faults 195k → about 1.2k. The 1-worker 50M stencil went from 1.71 to 1.31 s.
     In an A/B of two builds that differed only in the advice, the sieve went from 497 to 425 ms.
     Its kernel time fell from 45 to 9 ms; the rest came from user time in the strided marking
     loop, consistent with fewer TLB misses, although code placement (below) can also move it.
3. **Programs whose parallel regions all run on threads use the private heap**
   (`axonc/llvm.py`).
   - Managed arrays used private pages with one worker. With several workers they used
     `MAP_SHARED` anonymous (shmem) pages, because fork-dispatched (allocating) regions write a
     parent-visible output buffer.
   - Now `main` presets heap mode 1 (private) for every worker count when no fork-dispatched
     region is reachable, no prebuilt library code is linked, and at least one shared-address
     thread region is reachable.
   - The 2-worker stencil profile had shown shmem fault work: `shmem_add_to_page_cache`,
     `shmem_inode_acct_blocks` and `fault_dirty_shared_page`. Private pages avoid it and can also
     use change 2.
   - Programs without parallel regions keep the runtime's worker-count policy. A first version
     also covered them and broke `tests/heap_headers.py`, which checks that policy, so it was
     narrowed.
   - Effect, with change 1 only: 2-worker 50M stencil 1.20 → 0.97 s (kernel time 0.72 → 0.36 s);
     2-worker sieve 0.50 → 0.48 s. With change 2, the 2-worker rows reach 0.75 s and 0.40 s.
4. **Bounded `i64` sums skip the per-element overflow check** (`axonc/llvm.py`).
   - Suppose the whole-program interval pass bounds a `sum` body to [b0, b1] and the iteration
     count by C. C is at most hi − lo, which the comprehension already checks for overflow. Then
     every partial, per-chunk and combined sum lies in [min(0, b0·C), max(0, b1·C)].
   - When that interval fits in `i64`, the accumulation is emitted as `add nsw`, and so are the
     vectorized sum's lane additions.
   - Here it applies to the sieve's final count (`if marks[k] then 1 else 0` over `0..n+1`). That
     loop lost its `jo` per byte and LLVM unrolls it 8×: 290 → 145 profile samples.
   - Measured with the loop alignment held fixed (`-falign-loops=32` or `64` on identical IR):
     −14 and −18 ms.
5. **Accept every pending connection per readiness event** (`runtime/http_uring.ax`,
   `runtime/http_linux.ax`).
   - The io_uring and epoll workers accepted one connection per listener event.
   - In `run_http.py` each measured wrk run opens 64 new connections while the server is still
     finishing the warm-up's requests. The k-th new connection therefore waited out k loop
     iterations, each serving the requests of the connections already accepted.
   - With 0.69 ms requests (`POST /nbody`), the first request of connections 21–63 took 106–740 ms,
     rising with the index. That was the p99.
   - Workers now accept while they hold the accept turn: with one worker, until the listener is
     drained. With several workers the round-robin turn still passes after each accept.
   - Effect: `POST /nbody` p99 258 → 46 ms and maximum latency 740 → 48 ms, with throughput
     unchanged. That p99 is now 2.1× lower than http.zig 1+1's.

Tried and dropped:

- **Storing bools as `i8` in memory.** LLVM's loop vectorizer rejects `i1` loads and stores, so
  the change made the fill and count loops vectorize. With the SSE2 baseline the 64-bit index
  comparisons are emulated, and the vector fill was slower than the scalar one: the sieve went
  from 492 to 506 ms with that change alone.
- **Advising whole blocks for huge pages.** This was the first version. It can enlarge resident
  memory by up to 2 MiB per block, so the advice is restricted to fully covered regions. I saw no
  speed difference attributable to the restriction; the remaining differences tracked code
  placement.
- **The adaptive io_uring wait** described above.

## Method

Same drivers and method as the earlier report (`bench/zig/`), with one addition: the optional
`BIN_BEFORE` variant, which runs Vif before inside the same interleaved rounds. All outputs were
compared across every variant (integers exactly, nbody energy within 1e-9 relative).

- **Compute** (`run_cli.py compute`): median of 7 rounds after a warm-up, variant order alternating
  each round. One worker is pinned to CPU 0 and two workers to CPUs 0–1 (`AXON_THREADS` /
  `ZIG_THREADS`). Peak RSS is GNU time `%M`.
- **JSON** (`run_cli.py json`): every process on CPU 0 with `AXON_THREADS=1`; 2 warm-ups, then 9
  rounds in shuffled order with a fixed seed.
- **HTTP** (`run_http.py`): server on CPU 0 with one worker; `wrk -t1 -c64 --latency --timeout 5s`
  on CPU 1. Each run starts a fresh server, warms up for 2 s and measures for 10 s; results are
  medians of 5 rounds with alternating order. CPU per request is the server session's user plus
  kernel time divided by completed requests (median user + median kernel). Peak RSS is sampled
  every 250 ms. Every server passed the `compare.py` references and the byte-for-byte `/page/50`
  check against React before measuring. No run had socket errors or non-2xx responses.
- The run order was: the complete verification suite on the final tree, the builds, the
  GNU-time fault log, then compute, JSON, header capture and HTTP, then the `bench/run.py`
  workloads.

## Compute (median ms; peak RSS MiB)

| Case | Workers | Vif after | Zig | Zig native | Zig / Vif | Zig native / Vif | Vif before | Before / after | Peak RSS after / before / Zig |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mandel-1200-1200-300 | 1 | 132.1 | 185.4 | 192.1 | 1.40× | 1.45× | 132.5 | 1.00× | ≤2 / ≤2 / ≤2 |
| stencil-1000000-20 | 1 | 28.5 | 34.9 | 35.2 | 1.22× | 1.23× | 33.5 | 1.17× | 15.3 / 15.2 / 15.9 |
| stencil-50000000-20 | 1 | 1,310.3 | 1,674.2 | 1,705.3 | 1.28× | 1.30× | 5,968.8 | 4.56× | 762.9 / 762.9 / 763.6 |
| nbody-1024-3 | 1 | 10.9 | 16.4 | 16.3 | 1.51× | 1.50× | 10.8 | 0.99× | ≤2 / ≤2 / ≤2 |
| nbody-4096-10 | 1 | 347.8 | 629.4 | 631.6 | 1.81× | 1.82× | 348.1 | 1.00× | ≤2 / ≤2 / ≤2 |
| sieve-100000000 | 1 | 414.3 | 482.6 | 478.6 | 1.16× | 1.16× | 497.3 | 1.20× | 95.4 / 95.4 / 96.0 |
| mandel-1200-1200-300 | 2 | 68.7 | 94.6 | 98.2 | 1.38× | 1.43× | 68.2 | 0.99× | ≤2 / ≤2 / ≤2 |
| stencil-1000000-20 | 2 | 25.9 | 35.9 | 31.9 | 1.38× | 1.23× | 33.1 | 1.28× | 15.2 / 15.2 / 16.2 |
| stencil-50000000-20 | 2 | 747.2 | 1,029.5 | 931.6 | 1.38× | 1.25× | 5,594.4 | 7.49× | 762.9 / 762.9 / 763.9 |
| nbody-1024-3 | 2 | 6.8 | 11.1 | 11.1 | 1.64× | 1.63× | 6.9 | 1.02× | ≤2 / ≤2 / ≤2 |
| nbody-4096-10 | 2 | 182.2 | 324.4 | 327.1 | 1.78× | 1.79× | 179.1 | 0.98× | ≤2 / ≤2 / ≤2 |
| sieve-100000000 | 2 | 400.5 | 456.3 | 460.0 | 1.14× | 1.15× | 497.5 | 1.24× | 95.4 / 95.2 / 96.3 |

Outputs: mandel 79165632, stencil 499998359740 (1M) and 25000046624222 (50M), sieve 5761455, and
nbody 1024×3 equal to −0.888664604141282 within 2e-15 in every variant. The 1-worker ranges are
tight; for example, the 50M stencil ran in 1,307.5–1,324.7 ms (Vif) against 1,660.0–1,700.6 ms
(Zig). The widest Vif range is the sieve's, 409.3–437.6 ms against Zig's 477.0–518.6 ms. All
ranges are in `compute.json`.

One GNU-time run each (`faults.log`):

| Run | Wall | User | Kernel | Minor faults |
|---|---:|---:|---:|---:|
| stencil 50M, 1 worker, Vif before | 6.23 s | 2.30 s | 3.92 s | 2,050,889 |
| stencil 50M, 1 worker, Vif after (partial huge pages, see above) | 1.68 s | 1.34 s | 0.33 s | 65,101 |
| stencil 50M, 1 worker, Zig | 1.68 s | 1.30 s | 0.37 s | 195,491 |
| stencil 50M, 2 workers, Vif before | 5.62 s | 2.20 s | 7.48 s | 2,050,892 |
| stencil 50M, 2 workers, Vif after | 0.81 s | 1.35 s | 0.10 s | 4,298 |
| stencil 50M, 2 workers, Zig | 1.02 s | 1.49 s | 0.41 s | 196,943 |
| sieve 1e8, 1 worker, Vif before / after / Zig | 0.54 / 0.42 / 0.51 s | 0.50 / 0.41 / 0.46 s | 0.04 / 0.00 / 0.04 s | 24,507 / 489 / 24,591 |

## JSON (one CPU; median ms over 9 runs)

| Workload | Vif after | Vif before | Zig Value | Zig typed | Zig Value arena | Zig typed arena | Zig Value native | Zig typed native |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| small document built and decoded ×1M | **169.8** | 168.6 | 626.1 | 320.7 | 585.3 | 308.9 | 636.2 | 322.0 |
| 1,000-order array decoded ×1,000 | **173.0** | 173.8 | 1,012.6 | 237.4 | 412.0 | 203.8 | 1,023.6 | 244.9 |

Checksums 513500000 and 34327000 match in every variant. Every process stays at or below the
2 MiB RSS floor. The Vif document time is lower than in the 11-01 report (198.0 ms) both before and
after this round's changes, so that difference comes from the spike patch or the machine, not
from these changes.

## HTTP (server: 1 worker on CPU 0; wrk -t1 -c64 on CPU 1; medians of 5 × 10 s)

| Scenario | Server | req/s | Run range | p50 µs | p99 µs | CPU µs/req (user + kernel) | Peak RSS MiB | Threads |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `GET /` | Vif after | 77,966 | 75,995–78,791 | 410 | 1,490 | 0.46 + 9.42 = **9.88** | 0.8 | 1 |
| | Vif before | 78,306 | 76,997–80,247 | 408 | 1,420 | 0.47 + 9.40 = 9.88 | 0.8 | 1 |
| | Zig std.http | 63,626 | 62,993–67,036 | 491 | 1,880 | 1.22 + 13.52 = 14.74 | 18.0 | 65 |
| | Zig http.zig 1+1 | 71,520 | 69,159–76,638 | 688 | 2,380 | 1.22 + 12.42 = 13.64 | 3.9 | 3 |
| | Zig http.zig default | **79,080** | 78,274–80,778 | 611 | 1,990 | 1.20 + 11.11 = 12.31 | 12.5 | 34 |
| `GET /`, 16 pipelined | Vif after | **1,041,294** | 1,020,628–1,048,563 | n/a | n/a | 0.13 + 0.58 = **0.71** | 0.8 | 1 |
| | Vif before | 1,024,730 | 1,015,417–1,032,230 | n/a | n/a | 0.12 + 0.58 = 0.70 | 0.8 | 1 |
| | Zig std.http | 105,681 | 104,372–111,017 | n/a | n/a | 0.66 + 8.76 = 9.42 | 18.0 | 65 |
| | Zig http.zig (both) | stalls | | | | | | |
| `GET /smooth/10000` | Vif after | **3,124** | 3,123–3,181 | 20,020 | 26,770 | 310.3 + 9.3 = **319.5** | 1.4 | 1 |
| | Vif before | 3,099 | 3,060–3,119 | 20,250 | 26,480 | 313.8 + 9.0 = 322.7 | 1.0 | 1 |
| | Zig std.http | 2,583 | 2,510–2,627 | 24,360 | 33,440 | 368.9 + 17.5 = 386.3 | 29.3 | 66 |
| | Zig http.zig 1+1 | 2,554 | 2,525–2,564 | 24,710 | 32,000 | 369.0 + 23.1 = 392.1 | 13.2 | 3 |
| | Zig http.zig default | 2,464 | 2,407–2,478 | 25,560 | 96,390 | 378.9 + 30.3 = 409.2 | 24.5 | 34 |
| `POST /nbody` n=256 steps=4 | Vif after | **1,448** | 1,443–1,456 | 43,970 | **46,290** | 679.3 + 12.4 = **691.7** | 1.3 | 1 |
| | Vif before | 1,447 | 1,423–1,451 | 43,910 | 257,800 | 679.5 + 12.4 = 691.9 | 0.8 | 1 |
| | Zig std.http | 870 | 869–877 | 72,700 | 280,440 | 1,129.5 + 20.7 = 1,150.2 | 29.8 | 75 |
| | Zig http.zig 1+1 | 852 | 845–863 | 73,910 | 96,850 | 1,131.2 + 41.4 = 1,172.6 | 4.5 | 3 |
| | Zig http.zig default | 849 | 845–852 | 66,430 | 414,340 | 1,153.2 + 26.0 = 1,179.2 | 13.9 | 34 |
| `GET /page/50` | Vif after | **70,858** | 68,871–76,794 | 837 | 2,020 | 2.92 + 10.74 = **13.66** | 1.3 | 1 |
| | Vif before | 72,800 | 69,843–78,510 | 823 | 2,010 | 2.98 + 10.42 = 13.40 | 1.3 | 1 |
| | Zig std.http | 54,064 | 53,538–59,889 | 1,100 | 2,640 | 3.22 + 14.82 = 18.04 | 18.8 | 65 |
| | Zig http.zig 1+1 | 46,437 | 45,082–51,057 | 1,270 | 3,490 | 3.87 + 17.15 = 21.02 | 3.9 | 3 |
| | Zig http.zig default | 60,373 | 58,147–79,472 | 1,000 | 3,120 | 3.07 + 13.21 = 16.28 | 12.7 | 34 |

Response headers, captured byte for byte from the measured binaries (`headers.txt`). Bodies are
identical. Neither the Vif nor the Zig header bytes changed in this round.

| Server | `GET /` header bytes |
|---|---|
| Vif | `HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 13\r\n\r\n` (65 bytes) |
| Zig std.http | `HTTP/1.1 200 OK\r\ncontent-length: 13\r\ncontent-type: text/plain\r\n\r\n` (65 bytes) |
| Zig http.zig | `HTTP/1.1 200 \r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Length: 13\r\n\r\n` (78 bytes) |

For `/page/50` and `/smooth/1000`, Vif sends 81 and 71 header bytes, std.http the same counts
with lower-case names, and http.zig 79 and 84 bytes. http.zig adds `; charset=UTF-8` and omits the
reason phrase. None of the servers sends `Date`.

## Memory

- **Compute**: peak RSS is the same before and after: 762.9 MiB for the 50M stencil and 95.4 MiB
  for the sieve. Huge pages cover only regions the arrays fully write, so the advice adds no
  resident memory.
- **A VifDB-like allocation pattern**
  (`bench/zig/results/2026-11-01-vultr-2c-r2/alloc_pattern.ax`). Each round, the program grows an
  append-only log with `concat`, rebuilds an offset index, builds small per-record strings, makes a
  compaction copy of the whole log every fourth round, and optionally creates an 80–160 MB
  temporary array that exercises blocks above the 64 MiB retention cap. Peak RSS is GNU time
  `%M`, before → after:

  | Arguments (docs, rounds, temporary elements) | 1 worker | 2 workers | Minor faults, 1 worker |
  |---|---:|---:|---:|
  | 20000 40 0 | 119,384 → 119,440 KiB | 119,328 → 119,328 KiB | 148,956 → 30,894 |
  | 20000 40 10000000 | 197,412 → 197,520 KiB | 197,420 → 197,524 KiB | 930,237 → 31,645 |
  | 2000 400 0 | 128,444 → 128,488 KiB | 128,280 → 128,328 KiB | 1,365,239 → 131,453 |
  | 50000 24 20000000 | 302,532 → 302,544 KiB | 302,452 → 302,628 KiB | 1,099,605 → 37,203 |

  The largest difference is +176 KiB (0.06%), within the 64 KiB slab-chunk granularity per heap
  kind. Wall time fell 3–5× (for example 3.50 → 0.87 s). This program contains fork-dispatched
  regions (`int_text`), so it keeps the shared heap with two workers. It exercises change 1
  (both heap kinds) and, with one worker, change 2.
- **HTTP server**: the idle RSS (0.3 MiB) is unchanged, and so is the peak for hello, pipelining
  and `/page/50` (0.8, 0.8 and 1.3 MiB). For the two slow endpoints the peak rose from 1.0 to
  1.4 MiB (`/smooth/10000`) and from 0.8 to 1.3 MiB (`POST /nbody`). The likely cause, not
  verified by instrumentation, is change 5: the measured run's 64 new connections are now
  accepted while the warm-up's 64 connections are still draining their last slow requests, so
  both sets of connection buffers are briefly live. Vif remains 3–20× below every Zig server
  there.

## Other Vif workloads

The `bench/run.py` compute workloads (its Rust/Go comparison), both CPUs, default worker count,
median of 7 runs (5 for nbody). They were run with `ab.py` because `bench/run.py` itself queries
macOS `sysctl` and rewrites `RESULTS.md`. Go 1.25.1 is for reference; Rust was not rebuilt.

| Workload | Vif after | Vif before | Go |
|---|---:|---:|---:|
| mandel 3000×3000×2000 | 2,419.8 ms | 2,418.3 ms | 3,629.0 ms |
| stencil 50M×20 | 772.8 ms | 5,607.4 ms | 1,286.5 ms |
| stencil 1M×2000 | 1,688.9 ms | 1,715.3 ms | 2,481.6 ms |
| nbody 16384×10 | 2,809.4 ms | 2,794.4 ms | 8,833.8 ms |

Apart from the 50M stencil, all differences are within the run ranges (`runpy.txt`). Binary sizes
grew by 168–400 bytes, except `orders_json`: 142,680 → 155,248 bytes. That comes from different
inlining decisions, which I did not investigate further; its time is unchanged.

## Verification

On this box, with the final tree, `./axon test` ran the following:

- The Python suite (`unittest discover`): 173 tests OK.
- 37 native cases: 36 passed.
- `tests/integration.py`: every script passed, including `heap_headers.py`, `observer_lifetimes.py`,
  the 59 listed scripts (language, network, crypto, TLS, HTTP, kernel-runtime, compute and stencil
  smokes), the Bun JSX tests and `jsx_ssr_smoke.py`. Log tail: `suite-axon-test-tail.log`.

The one failing native case, `bounded-large-buffer-reuse` (`tests/fixtures/allocator_cache.ax`),
fails identically on the "before" tree and on git HEAD; it is not caused by this round. It
reads runtime state 136 as a cached block pointer and 144 as its size: the single large-block
cache that the runtime replaced with per-class free lists. Its first check fails because an 8 MiB
block now goes to a free list.

This round reuses 136 and 144 for the parked-block slots, one pointer per heap kind, used only
beyond the 64 MiB cap. The fixture would need rewriting to test that, so it still fails.

## Not done

- No `-falign-loops` (or similar) in the clang command, which would remove the sieve's
  placement sensitivity. That flag belongs in `axonc/cli.py`, which was outside this round.
- `README.md`'s allocator paragraph ("large mappings have bounded caches and are unmapped when the
  cache is full") does not yet mention the parked block, huge pages or the private-heap preset.
- No THP-disabled (`enabled=never`) rerun; the expected effect on the two rows is estimated in
  the bullets above.
- Rust and Go were not rerun beyond the reference Go column above.
- No four-worker rows: the box has two vCPUs.
