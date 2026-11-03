# Compute margins on x86-64 Linux, with and without huge pages (2026-11-03)

Neo's x86-64 compute rows against Zig 0.17.0 and Rust, measured with transparent huge pages (THP)
set to `madvise` and to `never`. The goal was at least 1.2× on every row against the best of Rust and
Zig, in both THP settings, with separate ranges, and every other row the same or better.

**Result: the target is met on 23 of the 28 rows. It is missed on the 2 sieve rows without huge pages
(1 and 2 workers) and on 3 of the 4 four-worker stencil rows: both rows without huge pages (1.12× and
1.16×), and 1M with huge pages, which reaches 1.22× but whose ranges overlap.**

- **Stencil: met on all 8 rows** (1M and 50M × 1 and 2 workers × 2 THP settings). Neo is now 1.24–1.89× faster than the best competitor in both THP
  settings, with separate ranges. Before this change Neo ranged from 0.95× (a loss: THP never,
  2 workers, 50M) to 1.22×.
- **Mandelbrot and n-body: unchanged.** They were already 1.38–1.82× ahead in both settings.
- **Sieve with huge pages: met.** Neo is 1.20–1.29× ahead, with separate ranges in both runs of the
  final binary.
- **Sieve without huge pages: missed.** Neo is 1.09–1.12× ahead; the ranges are separate in three of
  the four measurements (two runs × two worker counts). Neo's sieve got 1.10–1.19× faster, but the remaining time is the marking loop's memory
  traffic over 100 MB. Only blocking the sieve (a segmented sieve) would remove that, and that changes
  the algorithm the program states.
- **HTTP `/smooth/N` (stencil plus `cat`): 47% fewer instructions per request.** Responses are
  byte-identical, and the constant `GET /` control is unchanged.
- **CI passed** on an x86-64 box for the exact committed tree: `./neo test` and every
  `.github/workflows/verify.yml` step.
- **4-worker stencil on a voc-c-4c box: met on 1 of 4 rows.** Against Rust, the original 1.05× row,
  1M is now 1.22× with huge pages (ranges overlap) and 1.12× without. 50M is 1.71× ahead of
  Zig native with huge pages and 1.16× without. Without huge pages, every program spends 405–426 ms of
  system time faulting in the same two 400 MB arrays. Neo uses 1.23× less user time than Zig native, but the
  shared fault cost dilutes the wall-time margin. Neo after is 1.11–1.38× faster than `main` on all four
  rows, and the 50M row without huge pages turns from a loss (0.96×) into a win.

## Final table (voc-c-2c, 1 and 2 workers)

Medians in ms of complete-process wall time, with ranges in brackets. "vs best" is the best
competitor's median divided by Neo after's, i.e. the fastest of Zig, Zig native and Rust. "Separate"
means Neo after's slowest run beat that competitor's fastest run.

| THP | Row | W | Neo after | Neo before | Zig | Zig native | Rust | vs best | Separate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| madvise | stencil 1M × 20 | 1 | **19.3** (18.6–20.6) | 29.9 (29.6–33.0) | 36.4 (35.5–36.8) | 37.3 (36.9–42.4) | 49.0 (48.6–49.7) | **1.89×** Zig | yes |
| madvise | stencil 50M × 20 | 1 | **918.8** (904.5–959.7) | 1,419.5 | 1,732.8 (1,693.4–1,757.9) | 1,793.0 | 2,349.9 | **1.89×** Zig | yes |
| madvise | sieve 1e8 (run A) | 1 | **383.2** (363.6–392.1) | 433.2 | 475.8 | 464.5 (453.1–485.1) | 481.0 | **1.21×** Zig native | yes |
| madvise | sieve 1e8 (run B) | 1 | **375.8** (365.7–397.1) | 443.3 | 503.0 | 486.6 (468.0–509.9) | 510.2 | **1.29×** Zig native | yes |
| madvise | mandel 1200² × 300 | 1 | **147.1** (143.5–148.5) | 147.0 | 202.9 (201.2–205.7) | 209.6 | 203.5 | **1.38×** Zig | yes |
| madvise | nbody 1024 × 3 | 1 | **11.6** (11.5–11.7) | 11.6 | 17.7 | 17.6 (17.6–17.8) | 18.3 | **1.52×** Zig native | yes |
| madvise | nbody 4096 × 10 | 1 | **376.5** (375.7–378.5) | 376.1 | 684.5 | 684.2 (682.4–688.0) | 686.2 | **1.82×** Zig native | yes |
| madvise | stencil 1M × 20 | 2 | **19.2** (18.8–23.7) | 24.9 | 32.4 | 32.5 | 28.6 (28.1–31.1) | **1.49×** Rust | yes |
| madvise | stencil 50M × 20 | 2 | **539.3** (519.2–596.6) | 816.9 | 1,070.8 | 978.2 (933.6–1,092.7) | 1,241.5 | **1.81×** Zig native | yes |
| madvise | sieve 1e8 (run A) | 2 | **404.5** (367.3–457.9) | 480.8 | 502.2 | 487.2 (467.6–541.0) | 490.1 | **1.20×** Zig native | yes |
| madvise | sieve 1e8 (run B) | 2 | **369.6** (357.4–391.5) | 424.0 | 473.6 | 470.8 | 466.3 (454.6–507.9) | **1.26×** Rust | yes |
| madvise | mandel 1200² × 300 | 2 | **74.9** (73.2–79.6) | 74.6 | 103.1 (102.6–105.4) | 106.9 | 103.7 | **1.38×** Zig | yes |
| madvise | nbody 1024 × 3 | 2 | **7.1** (7.0–7.3) | 7.1 | 11.4 | 11.4 | 10.7 (10.6–17.4) | **1.52×** Rust | yes |
| madvise | nbody 4096 × 10 | 2 | **194.5** (193.6–207.4) | 194.5 | 352.0 | 350.0 | 349.8 (347.0–356.2) | **1.80×** Rust | yes |
| never | stencil 1M × 20 | 1 | **22.5** (22.3–22.9) | 34.6 | 35.6 (35.5–37.9) | 37.2 | 49.0 | **1.58×** Zig | yes |
| never | stencil 50M × 20 | 1 | **1,174.4** (1,157.6–1,259.3) | 1,764.7 | 1,758.8 (1,726.7–1,827.9) | 1,825.9 | 2,373.1 | **1.50×** Zig | yes |
| never | sieve 1e8 (run A) | 1 | **439.8** (430.4–456.1) | 500.2 | 504.4 | 492.4 (473.5–519.5) | 504.3 | 1.12× Zig native | yes |
| never | sieve 1e8 (run B) | 1 | **445.9** (433.2–479.8) | 505.9 | 496.8 | 495.8 (476.1–506.9) | 516.3 | 1.11× Zig native | no |
| never | mandel 1200² × 300 | 1 | **145.2** (143.6–151.7) | 145.8 | 202.5 (201.9–205.2) | 210.1 | 203.5 | **1.39×** Zig | yes |
| never | nbody 1024 × 3 | 1 | **11.9** (11.6–12.3) | 12.0 | 18.0 | 17.8 (17.7–21.0) | 19.7 | **1.49×** Zig native | yes |
| never | nbody 4096 × 10 | 1 | **377.5** (376.2–379.5) | 376.8 | 685.3 | 684.3 (682.0–688.4) | 686.9 | **1.81×** Zig native | yes |
| never | stencil 1M × 20 | 2 | **24.3** (20.1–27.9) | 29.3 | 34.4 | 32.4 | 30.1 (28.0–33.6) | **1.24×** Rust | yes |
| never | stencil 50M × 20 | 2 | **797.9** (742.3–823.9) | 1,051.7 | 1,088.0 | 996.9 (941.0–1,006.7) | 1,248.8 | **1.25×** Zig native | yes |
| never | sieve 1e8 (run A) | 2 | **457.8** (443.5–486.4) | 506.4 | 509.4 (492.5–546.4) | 519.2 | 513.3 | 1.11× Zig | yes |
| never | sieve 1e8 (run B) | 2 | **433.3** (412.7–443.7) | 476.4 | 474.4 | 479.1 | 473.4 (452.3–491.7) | 1.09× Rust | yes |
| never | mandel 1200² × 300 | 2 | **74.6** (73.7–78.1) | 74.5 | 103.1 (102.6–107.0) | 106.8 | 103.7 | **1.38×** Zig | yes |
| never | nbody 1024 × 3 | 2 | **7.1** (7.0–7.3) | 7.2 | 11.5 | 11.3 | 10.7 (10.6–11.8) | **1.51×** Rust | yes |
| never | nbody 4096 × 10 | 2 | **196.7** (192.8–200.2) | 195.3 | 353.3 | 350.1 | 351.5 (347.3–356.2) | **1.78×** Rust | yes |

Ranges of the other columns are in `summary.md` and in the JSON. The non-sieve rows come from one
run (`final-2c.json`, 9 rounds). The sieve rows come from two later runs of the final sieve binary:
run A has 9 rounds (`final-2c-sieve.json`) and run B has 15 rounds (`final-2c-sieve-b.json`).

`final-2c.json` also has sieve rows, measured with an intermediate binary that loaded bools as bytes;
they read 1.20 / 1.18 / 1.07 / 1.06×. Profiling showed that binary's count loop was 2× slower (see
"Tried and dropped"), so the final binary stores bytes but loads `i1`. That run's stencil, mandel,
n-body, JSON and HTTP binaries are byte-identical to the final ones; `final2.log` checks this with
`cmp`.

The box was noisier during the two sieve runs: competitor sieve medians were up to 14% higher than in
the first run, and ranges were wider. Rounds are interleaved, so every variant saw the same
conditions.

Before this change, the thin rows were these (Neo before vs best, same runs):

- THP never, 1 worker: stencil 1M at 1.03× (Neo 34.6 vs Zig 35.6) and stencil 50M at 1.00× (1,764.7 vs
  1,758.8, so a loss within noise).
- THP never, 1–2 workers: the sieve at 0.98–1.01× (both runs).
- THP never, 2 workers: stencil 1M at 1.03× and stencil 50M at 0.95× (a loss to Zig native).
- THP madvise: the sieve at 1.01–1.10×.

## 4-worker stencil (voc-c-4c)

Vultr instance 76, `voc-c-4c-8gb-75s-amd`: AMD EPYC-Milan, 4 vCPUs (two cores, each with two SMT
threads). Every process was pinned to CPUs 0–3, with 4 workers and 15 interleaved rounds. All outputs
agreed. "Before" here is `main` at `5f96ca0`. Its stencil binary is byte-identical to the 2c run's
"before" binary, built from `6e18e65`, and Neo after's binary is byte-identical to the 2c run's
(`meta-4c.txt`).

| THP | Row | Neo after | Neo before | Zig | Zig native | Rust | vs best | Separate | Before vs best |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| madvise | stencil 1M × 20 | **18.1** (16.4–22.0) | 20.6 | 30.6 | 29.1 | 22.1 (20.5–51.7) | **1.22×** Rust | no | 1.07× |
| madvise | stencil 50M × 20 | **342.1** (315.2–394.2) | 473.0 | 622.5 | 586.0 (531.0–629.0) | 691.9 | **1.71×** Zig native | yes | 1.24× |
| never | stencil 1M × 20 | **19.1** (18.5–20.3) | 21.1 | 30.0 | 28.1 | 21.4 (20.5–24.3) | 1.12× Rust | yes | 1.01× |
| never | stencil 50M × 20 | **500.7** (450.7–561.7) | 607.8 | 603.1 | 583.3 (527.7–615.4) | 688.8 | 1.16× Zig native | no | 0.96× (loss) |

The target is met only on 50M with huge pages. Medians of user time, system time and minor faults from
the same runs (`final-4c.json`) show why the other rows fall short:

| THP | Row | Neo after user / sys (ms) | Neo after faults | Best competitor user / sys (ms) | Its faults |
|---|---|---:|---:|---:|---:|
| madvise | 1M | 49.0 / 9.4 | 956 | Rust 57.8 / 16.3 | 4,105 |
| never | 1M | 48.4 / 12.2 | 4,006 | Rust 59.5 / 12.9 | 4,105 |
| madvise | 50M | 1,198.1 / 55.9 | 1,236 | Zig native 1,587.0 / 426.0 | 199,850 |
| never | 50M | 1,313.5 / 415.6 | 195,412 | Zig native 1,613.1 / 425.8 | 199,851 |

- **50M without huge pages.** All five programs fault in the same two 400 MB arrays page by page, at
  405–426 ms of system time each. Neo's compute advantage remains (1.23× less user time than Zig
  native), but it is diluted by a fault cost that every program pays equally. With huge pages, Neo's
  `MADV_HUGEPAGE` removes almost all of those faults, giving 1.71×. The populate call in `cc6a885`
  applies to one worker only, because a single `madvise` call would serialize faulting that four workers
  otherwise do in parallel. Populating each worker's own chunk could recover part of this cost; it was
  not tried.
- **1M.** The working set is 16 MB, with about 4,000 faults for Neo and Rust alike. Neo uses the least
  user time (48–49 ms against Rust's 58–60 ms), but its wall time barely improves with more workers:
  22.5 ms with 1 worker on the 2c box, against 19.1 ms with 4 workers here. Rust goes from 49.0 to
  21.4 ms over the same change, which closes most of the gap. The cause was not investigated, and
  memory bandwidth is the likely limit. With huge pages the median ratio is 1.22×, but 4 of Neo's
  15 runs (the slowest 22.0 ms) are slower than Rust's fastest run (20.5 ms).

## What was slow, and what changed

Six commits on `claude/x86-margins-3bb69e`, each isolated in its own function or file:

1. **The stencil's vector interior still computed its boundary masks** (`f386df3`). `examples/stencil.neo` is
   `arr(i in 0..n) if i == 0 || i + 1 == n then xs[i] else (xs[i-1] + 2*xs[i] + xs[i+1]) % 1000003`.
   The 4-lane vector loop evaluated `i == 0 || i + 1 == n` on every lane and blended both arms, so the
   interior was bound by computing the masks, not by memory. `interior_assumptions` (neoc/vectorize.py)
   finds `==`/`!=` index comparisons whose targets cannot fall in the vector interior and emits a second
   vector loop with those comparisons fixed. A run-time guard computes the actual targets with an
   overflow check and selects that loop; the masked loop remains for every other case. Isolated
   effect, 1 worker: 1M × 20 went from 28.7 to 19.2 ms with THP madvise and from 33.6 to 24.0 ms with
   THP never; 50M × 20 went from 1,410 to 964 ms and from 1,757 to 1,296 ms (`exp4.log`).
   The same commit splits scalar comprehensions at a single loop-invariant index bound
   (`split_counted_loop`). The sieve's `k >= 2` fill becomes two constant fills, and the HTTP
   example's `cat` (`if i < n then a[i] else b[i - n]`) becomes two copies.
2. **Unsigned compares in the vectorized remainder** (`2d25bc1`). The strength-reduced `% 1000003`
   subtracts conditionally with `icmp uge`. SSE2 has no unsigned vector compare, so LLVM flipped the sign
   of both operands each time. The value is known to lie in [0, limit] with limit < 2^31, so a signed
   compare is exact.
3. **The sieve's marking loop** (`491a982`). This is memory-bound. Each prime below 64 streams through
   the whole 100 MB array. From 64 up, every store lands on its own 64-byte line, at about 4 ns per
   line. `neoc/strided.py` gives the loop
   `loop (a, j) while j < x next (set(a, j, v), j + s)` an unrolled prefix of four stores per iteration
   behind one range guard. On x86-64, when each store lands on its own line (step × size ≥ 64) of an
   array of at least 4 MiB, it loads first and stores only when the value differs. The line is fetched
   either way, but a skipped store leaves it clean, so it is not written back. Most composites are
   already marked by smaller primes. Isolated effect, 1 worker:
   - Unrolling: 410.0 → 397.1 ms with THP madvise and 442.0 → 421.2 ms with THP never (`exp6.log`).
   - Check-before-store: 389.7 → 368.0 ms with THP madvise and 428.8 → 415.2 ms with THP never
     (`exp7.log`).
4. **The sieve's fill stored 4 bytes per instruction** (`ec4ba9d`). Neo stored bool elements as `i1`,
   and LLVM's loop idiom pass recognizes no memset in `i1` stores. Bool elements are now stored as
   zero-extended bytes, so the fill becomes a `memset` call: 1.9% → 0.9% of the sieve's samples.
5. **Page faults without THP** (`cc6a885`). With one worker, a freshly mapped private block of 4 MiB or
   more is now pre-faulted over its requested bytes by one `madvise(MADV_POPULATE_WRITE)` call. The new
   array writes those bytes immediately anyway, so resident size is unchanged. Isolated effect, THP
   never, 1 worker (`exp5.log`):
   - stencil 1M: 22.8 → 21.5 ms
   - stencil 50M: 1,325 → 1,245 ms (both builds had the NT-store experiment on)
   - sieve: 447.7 → 434.7 ms

   With several workers the runtime keeps faulting each chunk on its own worker.
6. The harness and benchmark sources (`3f1023a`):
   - `bench/rust/src/sieve.rs`, the Rust sieve: rayon fill and count, sequential marking, the same
     algorithm as `examples/sieve.neo` and `bench/zig/sieve.zig`.
   - `bench/compute-margins/run.py` and `summarize.py`.
   - `http_ab.py`.
   - Two downside benchmarks for the strided lowering.

The interior specialization, the scalar split, the unrolled strided prefix and the bool byte stores
apply on every target, and the populate call applies on Linux. On ARM64, i64 array comprehensions take
the scalar path, so the interior specialization only reaches f64 bodies there. Check-before-store is
x86-64 only. ARM64 was not measured by this work.

## Tried and dropped

- **Non-temporal (streaming) stores for large vector array outputs**, x86-64, at 16 MiB and 4 MiB
  thresholds (`exp4.log`, `exp5.log`). With THP madvise they helped the 50M stencil (922.8 → 820.0 ms,
  1 worker). With THP never they hurt it: 1,174.9 → 1,244.6 ms with 1 worker and 750.5 → 842.8 ms with
  2 workers. THP never is the setting this work targets, so the code was removed.
- **Loading bool elements as bytes.** This lets LLVM vectorize the sieve's `sum(if marks[k] then 1 else 0)`
  with 16-byte loads. On SSE2, though, it widens every byte to i64 through unpack chains. Profiled, the
  count went from 3.7% to 7.4% of the sieve. In the A/B (`final2.log`, THP madvise), the sieve took
  404.1 ms with byte loads and byte stores, 398.5 ms with `i1` loads and `i1` stores, and 385.5 ms in
  the final form (byte stores, `i1` loads). Only the byte stores were kept.
- **Check-before-store at strides of 8, 16 or 32 bytes.** The sieve showed no gain over 64 bytes:
  410.6, 416.6, 412.3 and 415.2 ms for 8, 16, 32 and 64 bytes with THP never. At 16 bytes, a pass whose
  stores are never redundant got 23% slower (98.0 → 120.9 ms, `exp7.log`). The threshold stays at one
  element per line.
- **Not attempted: blocking/tiling the sieve.** The marking loop's order comes from the program's outer
  loop over primes. Interchanging it into a segmented sieve is an algorithm-level transformation, not
  a small isolated compiler change, so it was left out. It is what the sieve without huge pages would
  need to reach 1.2×.

## Costs and other rows

- **Strided downside** (64M flags, 3 rounds, THP madvise, final vs before, `final2.log`):

  | Case | Final | Before | Change |
  |---|---:|---:|---:|
  | Never-redundant pass, step 64 | 323.2 | 313.6 | +3.1% |
  | Half redundant in a pseudo-random pattern, step 64 | 488.1 | 517.1 | −5.6% |
  | Never-redundant pass, step 256 | 1,065.2 | 1,127.4 | −5.5% |
  | Half redundant, step 256 | 1,302.8 | 1,336.4 | −2.5% |

  The worst case measured is the never-redundant step-64 pass, which costs about 3%.
- **JSON** (`library_bench` doc × 1M and `orders_json` 1000 × 1000, 1 worker). The binaries differ only
  in the populate call and one signed compare in `utf8_encode`. No JSON block reaches 4 MiB: peak RSS
  is 1,920 KiB and minor faults are 157 for both binaries.

  | Run | THP | doc × 1M, after / before (ms) | orders 1000 × 1000, after / before (ms) |
  |---|---|---:|---:|
  | `final.log`, 9 rounds | madvise | 205.4 / 199.6 (overlapping ranges) | 190.1 / 190.0 |
  | `final.log`, 9 rounds | never | 201.3 / 202.1 | 194.1 / 195.3 |
  | `exp9.log`, 15 rounds | madvise | 197.5 / 198.2 | not rerun |
  | `exp9.log`, 15 rounds | never | 198.1 / 195.1 | not rerun |

  Both rows are unchanged within noise.
- **Mandelbrot** binaries are byte-identical before and after. **N-body** differs only in the runtime's
  large-block function and is unchanged.
- **HTTP example** (`examples/http.neo`). One worker on CPU 0, with `wrk -t1 -c16` for 5 s on CPU 1.
  Five interleaved rounds per path, on the 2c CI box (`logs/http-instr.log`). CPU 1 is CPU 0's SMT
  sibling, so req/s is only indicative. User-space instructions retired per request (`perf stat`
  attached to the server) do not depend on that load. Responses were byte-identical on every path.

  | Path | Instructions/request, before → after | req/s, before → after (medians) |
  |---|---:|---:|
  | `GET /` (constant response, control) | 2,786 → 2,786 | 81,398 → 81,512 |
  | `/smooth/1000` | 637,581 → 340,836 (−47%) | 22,717 → 36,368 |
  | `/smooth/10000` | 6,268,489 → 3,302,859 (−47%) | 2,913 → 5,420 |

  The handler's stencil drops from about 19.6 to 10.3 instructions per element (320,000 elements per
  request: 10,000 × 32 passes). Its `cat`s become `memcpy` calls.

## Not done

- **The 4-worker stencil rows without huge pages, and 1M with huge pages, miss the target.** See
  "4-worker stencil" for the measured causes. Per-worker populate was not tried.
- **HTTP req/s by the headline method**, which needs a separate load-generator core. The
  instruction counts above stand in for it. `bench/compute-margins/http_ab.py BEFORE AFTER` runs the
  headline method on a 4c box.

## CI

The full suite ran on a fresh Vultr `voc-c-2c-4gb-50s-amd` (instance 65: EPYC-Milan, Ubuntu 24.04,
Linux 6.8, clang 18.1.3, Bun 1.3.13) against `git archive` of `3f1023a`, which is the code measured
above. Logs are in `logs/ci.sh`, `logs/ci.log` and `logs/ci-neo-test.log`.

| Step | Result |
|---|---|
| `./neo test` (59 test scripts, 37 native cases) | exit 0, "37 native cases, 0 failed" |
| Empty-root runtime audit (`examples/http.neo`, `tests/freestanding_linux_smoke.py`) | PASS |
| Reproducible compiler bundle (`./neo release` twice, `cmp`) | identical, sha256 `bc9322f8…1e83` |
| Empty-root language, crypto and TLS (`tests/language_freestanding.py`) | PASS |

The ARM64 job of `verify.yml` was not run.

## Method

- **Harness:** `bench/compute-margins/run.py`, following `bench/zig/run_cli.py`.
  - One warm-up round, then 9 (or 15) rounds. Variants are interleaved, and the order reverses every
    other round.
  - Each process is pinned with `taskset`: CPU 0 for 1 worker, CPUs 0–1 for 2 workers and CPUs 0–3 for
    4 workers.
  - `NEO_THREADS`, `ZIG_THREADS` and `RAYON_NUM_THREADS` set the worker count.
  - GNU time records peak RSS and minor faults.
  - The harness writes the THP setting to `/sys/kernel/mm/transparent_hugepage/enabled` before each
    section and restores it afterwards. `defrag` stayed `madvise`.
  - Every output was checked: integers exactly, n-body within 1e-9 relative. All rows agreed.
  - The isolation runs (`exp*.log`, `final2.log`) used `ab.py`, the same interleaving without GNU
    time. Their absolute times are not directly comparable with `run.py`'s; compare within one log.
- **Machine:** Vultr `voc-c-2c-4gb-50s-amd`, instance 54, Amsterdam, created for this work and destroyed
  afterwards, as was the CI box (instance 65). Vultr's `list_instances` afterwards showed neither box;
  the five listed instances belong to other sessions.
  - CPU: AMD EPYC-Milan, 2 vCPUs, which are one core's two SMT threads. L2 is 512 KiB and L3 32 MiB.
  - OS: Ubuntu 24.04.5 LTS, Linux 6.8.0-146-generic. The default THP setting is `madvise`.
  - Nothing else ran during measurements.
- **4-worker machine:** Vultr `voc-c-4c-8gb-75s-amd`, instance 76, with the same CPU model, OS, kernel
  and toolchains. Vultr refused a 4c box with "maximum monthly fee limit" four times during the first
  part of this work, and three more times at three-minute intervals before the fourth retry succeeded.
  The box was destroyed after the run; Vultr's `list_instances` afterwards no longer showed it (the
  three listed instances belong to other sessions). No Scaleway box was needed. Sources were
  `git archive` of `main` (`5f96ca0`) and of `3f1023a`; their hashes are in `meta-4c.txt`.
- **Neo:**
  - "Before" is `6e18e65` (Neo 0.1.1).
  - "After" is the tree of `3f1023a`. Its `neoc/` and `runtime/` are byte-identical to the measured
    `fin2.tgz`.
  - Built with `./neo build … --no-cache` and clang 18.1.3.
- **Zig:** 0.17.0 (tarball sha256 `1cbe9df9…2026`).
  - Built with `zig build -Doptimize=ReleaseFast`, once with `-Dcpu=baseline` ("Zig") and once native.
  - The sieve and stencil Zig programs are unchanged from `bench/zig`.
- **Rust:** rustc 1.99.1 (`58cf8f9c3`), `cargo build --release` with the existing profile: opt-level 3,
  codegen-units 1, fat LTO.
- **Binary hashes, toolchains and source pack hashes:** `meta.txt`.

## Raw data

`bench/compute-margins/results/2026-11-03-vultr-2c/` holds:

- `final-2c.json`, `final-2c-sieve.json` and `final-2c-sieve-b.json`: every run's wall, user and system
  time, peak RSS, minor faults and output.
- `summary.md`, generated by `summarize.py`.
- `meta.txt`.
- `logs/`: every job script and its log, in order. `README.md` there names each experimental binary.
- `prototypes/`: the C prototypes used to locate the sieve and stencil bottlenecks.

`bench/compute-margins/results/2026-11-03-vultr-4c/` holds:

- `final-4c.json`, the 4-worker stencil run.
- `summary.md`.
- `meta-4c.txt`.
- `logs/`: the setup and run scripts and their logs.
