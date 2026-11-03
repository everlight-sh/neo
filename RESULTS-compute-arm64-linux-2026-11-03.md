# Neo compute kernels on ARM64 Linux: Neoverse-N1 vs Rust, Go and Bun (2026-11-03)

**Result: Neo wins every ARM64 compute row against Rust and Go, before and after this change.**
Real Neoverse-N1 hardware already put `main` ahead on every row. The losses in
[RESULTS-core-regression-linux-2026-10-27.md](RESULTS-core-regression-linux-2026-10-27.md) came from a
Linuxkit VM on an M1 Pro and do not reproduce on Linux ARM64 silicon. The compiler change in this round
makes Mandelbrot 1.69× faster and the stencil 1.03–1.05× faster. N-body is unchanged: its binary is
byte-identical, and it already runs at about 96% of the N1 divide/square-root unit's limit.

On x86-64 (EPYC-Milan), Mandelbrot gets 1.25× faster as a side effect, and every other compute executable
is byte-identical to main's. The full CI workflow passed on both machines.

| Case | Workers | Neo after | Neo before | Rust | Go | Bun | Best of Rust/Go ÷ Neo after | Before ÷ after |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mandel 1200×1200×300 | 1 | **124.3** | 210.3 | 238.4 | 228.4 | 358.1 | **1.84×** | 1.69× |
| stencil 1M×20 | 1 | **54.3** | 55.7 | 69.4 | 85.6 | 567.8 | **1.28×** | 1.03× |
| nbody 1024×3 | 1 | **21.3** | 21.4 | 24.2 | 24.3 | 160.5 | **1.14×** | 1.00× (same binary) |
| nbody 4096×10 | 1 | **768.8** | 768.9 | 885.4 | 866.3 | 1,573.8 | **1.13×** | 1.00× (same binary) |
| mandel 1200×1200×300 | 4 | **33.2** | 55.9 | 64.3 | 60.2 | — | **1.81×** | 1.68× |
| stencil 1M×20 | 4 | **17.5** | 18.4 | 22.4 | 29.9 | — | **1.28×** | 1.05× |
| nbody 1024×3 | 4 | **8.3** | 8.3 | 9.0 | 9.8 | — | **1.08×** | 1.00× (same binary) |
| nbody 4096×10 | 4 | **197.8** | 197.3 | 227.6 | 224.4 | — | **1.13×** | 1.00× (same binary) |

Median complete-process milliseconds over 9 interleaved rounds (`final.json`). The closest row is nbody
1024×3 on 4 workers, an 8 ms run with 4 thread starts. Its ranges overlap with Rust's (Neo 7.6–9.7 ms,
Rust 8.5–10.3 ms). Neo's median was lower in all three runs that measured it: 7.8 against 9.5 (baseline),
8.2 against 9.5 (`dev1.json`) and 8.3 against 9.0 (final).

Raw data, binary hashes and the box scripts are in `bench/core/results/2026-11-03-arm64-compute/`.

## Machine and versions

| | |
|---|---|
| Instance | Scaleway `BASIC2-A4C-8G`, fr-par-2, temporary, destroyed afterwards. `COPARM1` (dedicated Ampere) is no longer offered; every Ampere plan left is `BASIC2` with shared vCPUs. This is the smallest one with the 4 vCPUs the 4-worker rows need. |
| CPU | Ampere Altra, Neoverse-N1 r3p1, 4 vCPUs (one thread per core), QEMU `virt-6.2`, 2.0 GHz |
| RAM | 8 GB, no swap |
| OS | Ubuntu 24.04.5 LTS, Linux 6.8.0-147-generic aarch64; transparent huge pages `madvise` |
| Neo | clang 18.1.3 (Ubuntu 1ubuntu1), LLVM `-O3`, static ELF, `--no-cache` builds |
| Rust | 1.99.1, `bench/rust` release profile: `opt-level = 3`, `codegen-units = 1`, `lto = "fat"`, rayon |
| Go | 1.25.14 (newest 1.25.x), `GOTOOLCHAIN=local` |
| Bun | 1.3.13, `bench/core/compute.ts` (single-threaded, one-worker rows only) |

The competitor sources (`bench/rust/src`, `bench/go`, `bench/core/compute.ts`) are unchanged and were
built once on the box. Their hashes are in `final-sha256.txt`.

## Method

`bench/core/compute_compare.py`, added in this round, follows the method of the 2026-10-27 report:

- **Timing.** Complete-process wall time, including launch, allocation and teardown. Peak RSS comes from
  GNU time and CPU time from `getrusage`.
- **Rounds.** One warm-up round is excluded. The order of all variants is shuffled each round with a
  fixed seed (20261103).
- **Pinning.** One worker is pinned to CPU 0 (`taskset -c 0`) and four workers to CPUs 0–3, through
  `NEO_THREADS`, `RAYON_NUM_THREADS` and `GOMAXPROCS`.
- **Outputs.** Every output is checked: integers exactly, nbody energies within 1e-9 relative. They
  agreed in every run:
  - mandel: 79165632
  - stencil: 499998359740
  - nbody: −0.888664604141281 and −0.893848928815247
- **No overlap.** Builds, tests and measurements never overlapped on the box.

"Neo before" is `main` at 6e18e65, and "Neo after" is this branch. Both were built on the box from
source. The nbody and sieve executables are byte-identical between the two.

## What changed

All changes are in `neoc/vectorize.py`, plus their declarations and selection in `neoc/llvm.py`. They
apply to Linux AArch64 targets unless stated otherwise.

1. **Masked `sum` vectors are built from native-width groups** (`sum_width`).
   - **The problem.** The `sum` vectorizer computes K = 8 lanes at once. Mandelbrot's escape loop runs
     while any lane is active, under a `<8 x i1>` mask. LLVM splits a `<8 x double>` across four NEON
     registers. A mask that crosses registers or blocks is kept as a `v8i8` byte vector: in the
     loop-carried phi, in the `zext` that counts iterations and in the reduction. Every 64-bit `select`
     and every count add then widened it again with `umov`/`ushll`/`shl`/`cmlt` sequences.
   - **The fix.** VecGen now represents a K-lane value as K/W SSA values of `<W x T>`, with W = 2 on Linux
     AArch64: one Q register of f64 or i64. Every mask is then exactly the compare result of one register:
     - the iteration count becomes `sub k, k, mask`
     - selects become `bit`
     - the any-lane test becomes `orr` plus `umaxp`
   - **Other targets.** x86-64 and Darwin keep W = K (one group), so their VecGen IR keeps the same vector
     types.
2. **The masked loop is one block, and its mask is recomputed rather than carried** (all targets).
   - Each iteration evaluates the condition on the current state, ANDs it with the enclosing mask, and
     computes the successor under that mask.
   - A finished lane keeps the state its condition last failed on, and the same checks pass on it, so it
     keeps failing.
   - This removes the carried mask phi. A carried `<K x i1>` phi is a byte vector on AArch64 even with
     grouping.
3. **Vector `sum` loops run whole vectors unmasked** (all targets). At most one masked iteration then
   takes the tail. Before, every iteration built the "active lanes" mask and selected through it.
4. **i64 array comprehensions are vectorized on Linux AArch64.** This applies when every i64 operation in
   the body has a NEON instruction (`neon_native`):
   - add, subtract, compare and select
   - multiply by a power of two
   - remainder by a constant whose dividend is bounded (`remainder_bounded`, the existing compares and
     subtractions)

   Before, AArch64 vectorized only f64 arrays, because NEON has no 64-bit vector multiply or divide and
   forced 4-lane i64 bodies ran 2.8× slower. With W = 2 groups and that filter, the stencil body
   vectorizes, and bodies with a general multiply stay scalar.

The declarations of the vector intrinsics are now emitted once per width in use. The old code declared
the K-lane and 4-lane sets separately and broke when K = 4 (`invalid redefinition of llvm.sqrt.v4f64`).

**Darwin.** Darwin ARM64 keeps 16 lanes in one group. Changes 2 and 3 alter its IR, and they could not be
measured: nothing may run on the Apple machine. Statically, the escape loop of `examples/mandel.neo` for
`arm64-apple-macos` loses all 30 mask-widening instructions (`shl`, `cmlt`, `ushll`, `uaddw`). In exchange
it gains register moves and `and`s: 216 → 232 instructions, and 38 → 35 Q-register spills/reloads.

## Lane-group sweep (mandel, 7 rounds, `lanes.json`)

| Variant | 1 worker | 4 workers |
|---|---:|---:|
| main (two-block loop, `<8 x double>`) | 209.8 | 55.2 |
| new loop form only, K = 8 in one `<8 x double>` group | 192.0 | 50.7 |
| K = 4 (2 groups of 2) | 142.4 | 37.7 |
| K = 6 (3 groups) | 129.1 | 34.4 |
| **K = 8 (4 groups), chosen** | **124.1** | **33.3** |
| K = 12 (6 groups) | 155.9 | 41.1 |
| K = 16 (8 groups) | 182.8 | 48.1 |

The loop form alone gains 9%. Grouping gains the rest. Beyond four groups the time rises again. That
fits register pressure, though the spills were not inspected: each group carries five values (zx, zy,
k, cx, cy), and NEON has 32 registers.

## Investigated without a change

| Question | Measurement | Finding |
|---|---|---|
| Does the worker pool start? | Persistent futex pool (`ax_par_for_shared`, `kernel_workers.py`) | Works on N1: 4-worker rows scale 3.7–3.9× on mandel and nbody 4096. |
| Chunks per thread (`chunks.json`, 4 workers, 9 rounds) | 8 (current), 16, 32 | Within noise on every row (mandel 34.1 / 33.3 / 33.4 ms; stencil 17.3 / 17.5 / 17.7 ms). Not changed. |
| Tuning (`tune.json`, 1 worker, 7 rounds) | `-mtune=neoverse-n1`, `-mtune=neoverse-v1`, `-mcpu=neoverse-n1` | Within noise; `-mcpu=neoverse-n1` was 3% slower on mandel. The generic target is kept, so binaries run on any ARMv8.0 core. |
| FMA contraction, the way Go fuses multiply-add on arm64 (`fma-contract.json`) | `contract` flag on every f64 `fadd`/`fsub`/`fmul` (a patched copy: mandel 8, nbody 27 fused instructions) | mandel 124.9 → 126.4 ms (slower); nbody 4096 769.3 → 761.0 ms (−1.1%). Outputs still agreed. Not adopted: Neo keeps unfused IEEE arithmetic, so results do not depend on the target. `-ffp-contract=fast` on the clang command line does nothing for `.ll` input; the binaries were byte-identical. |
| Loop alignment (`fma-align.json`, `align.json`, 9 rounds) | `-falign-loops=32` / `64`. Generic AArch64 emits no `.p2align` on loops at all; x86-64 already gets 32. | A trade, not adopted. It speeds up nbody 4096 by 1.6% (770.8 → 758.6 ms on 1 worker, 197.5 → 194.1 on 4), and 32 and 64 measure the same. It slows the JSON probes: orders 1000×1000 396.3 → 399.6 ms (non-overlapping ranges) and the 1M-document decode 370.5 → 372.0 ms. Mandel, stencil (1M and 50M) and sieve stay within noise. |

## N-body: the divide/square-root unit

nbody's inner loop is LLVM's own vectorized loop, not VecGen. Every pair needs one `fsqrt` and one `fdiv`
(`inv = m / (d2 * sqrt(d2))` in `kick`, `m*m / sqrt(...)` in `energy`). The same holds in all three
languages. `scripts/divbench2.c` measures reciprocal throughput on this box. The two runs in
`arm64-scaleway/divbench2.txt` and an earlier run agreed to 0.3%. The table is in nanoseconds because
the program's own clock estimate, a dependent `add` chain, drifted between 2.04 and 2.99 GHz on the
shared vCPU. The nominal clock is 2.0 GHz.

| Instruction | ns per instruction |
|---|---:|
| `fdiv d` | 1.67 |
| `fsqrt d` | 2.34 |
| `fdiv d` + `fsqrt d` | 4.02 |
| `fdiv v.2d` | 3.35 |
| `fsqrt v.2d` | 4.69 |
| `fdiv 2d` + `fsqrt 2d` | 8.03 |
| `fmul 2d`, 8 independent | 0.18 each |
| `frecpe 2d` | 0.34 |

- **No overlap.** Divide and square root share one unpipelined unit, so a pair of them costs the sum.
- **No vector gain.** The 2-lane forms cost exactly twice the scalar ones.

nbody 4096×10 runs 11 × 4096² = 184.5 M interactions (10 `kick`s and the `energy`). The whole process
takes 768.8 ms, or 4.17 ns per interaction. The divide and square root alone need 4.02 ns, which is 96%.
The margin over Go and Rust (1.13×) comes from everything around those two instructions, and it cannot
grow much more. Going faster would need one of two other ways to divide:
- **An approximate reciprocal square root** (`frsqrte` plus Newton steps). It is not exact.
- **A Markstein correctly rounded division built from FMAs.** After the range, zero and all-ones guards
  it needs, the estimate was only 1.1–1.3× faster, and it would trade the hardware's IEEE-exact `sqrt`
  and `/` for a reimplementation.

Neither was done.

## Stencil: memory bandwidth

Each pass of the 1M×20 stencil reads one 8 MB array and writes another; neither fits in N1's 1 MB L2.
`perf stat` on one worker (`arm64-scaleway/stencil-perf.txt`):

| Build | Instructions | Cycles | IPC |
|---|---:|---:|---:|
| main (scalar) | 494.6 M | 158.4 M | 3.12 |
| final (vector) | 293.5 M | 151.0 M | 1.94 |

Vectorizing removes 41% of the instructions but only 5% of the cycles. About 9 GB/s goes through one core,
counting the write-allocate reads (20 passes × 24 MB in 54.3 ms). Neo was already 1.25× ahead of Rust
before the change.

## x86-64 check

**x86-64 code is unchanged or faster.** The box was a temporary Vultr `voc-c-2c-4gb-50s-amd` in Amsterdam
(id 72): AMD EPYC-Milan, 2 vCPUs = 1 core × 2 SMT threads, Ubuntu 24.04, Linux 6.8.0-146, THP `madvise`.
This is the same plan and CPU as [RESULTS-zig-x86-linux-2026-11-02.md](RESULTS-zig-x86-linux-2026-11-02.md).
Versions were the same as on ARM: clang 18.1.3, Rust 1.99.1, Go 1.25.14. Bun was installed for the CI suite but not timed on x86.

Method: 7 rounds, with 1 worker on CPU 0 and 2 workers on CPUs 0–1, covering every compute row of that
report. On x86-64 the branch changes only Mandelbrot. The stencil, nbody and sieve executables are
byte-identical to main's (`x86-vultr/sha256.txt`). x86 keeps K = 8 lanes in one `<8 x double>` group; only
changes 2 and 3 above reach it.

| Case | Workers | Neo after | Neo before (main) | 2026-11-02 report | Rust | Go | Best of Rust/Go ÷ after |
|---|---:|---:|---:|---:|---:|---:|---:|
| mandel 1200×1200×300 | 1 | **116.2** | 145.4 | 145.5 | 202.9 | 205.7 | 1.75× |
| stencil 1M×20 | 1 | 30.0 | 30.2 (same binary) | 30.7 | 49.7 | 53.4 | 1.66× |
| stencil 50M×20 | 1 | 1,424.8 | 1,428.7 (same binary) | 1,420.7 | 2,356.4 | 2,447.3 | 1.65× |
| nbody 1024×3 | 1 | 11.7 | 11.7 (same binary) | 11.8 | 18.4 | 29.0 | 1.57× |
| nbody 4096×10 | 1 | 376.8 | 376.7 (same binary) | 377.1 | 687.0 | 1,190.5 | 1.82× |
| sieve 1e8 | 1 | 443.8 | 433.0 (same binary) | 439.0 | — | — | — |
| mandel 1200×1200×300 | 2 | **60.5** | 73.9 | 73.8 | 102.9 | 104.8 | 1.70× |
| stencil 1M×20 | 2 | 25.2 | 25.9 (same binary) | 28.4 | 28.4 | 38.4 | 1.13× |
| stencil 50M×20 | 2 | 822.2 | 825.1 (same binary) | 802.4 | 1,262.0 | 1,309.2 | 1.53× |
| nbody 1024×3 | 2 | 7.0 | 7.0 (same binary) | 7.1 | 10.6 | 16.6 | 1.51× |
| nbody 4096×10 | 2 | 194.5 | 194.2 (same binary) | 194.3 | 348.7 | 607.7 | 1.79× |
| sieve 1e8 | 2 | 426.4 | 426.7 (same binary) | 428.5 | — | — | — |

- **Mandelbrot is 1.25× faster on 1 worker and 1.22× on 2.** The ranges do not overlap: 115.9–122.0
  against 143.2–146.2 ms, and 59.3–65.9 against 73.0–74.5 ms.
- **Main reproduces the 2026-11-02 numbers within 3%.** The one exception is stencil 1M on 2 workers,
  which ran faster today: 25.9 against 28.4 ms.
- **Sieve 1 worker shows the box noise.** The two executables are identical, yet their medians differ by
  2.5% (443.8 against 433.0 ms), with ranges 430.3–456.3 and 426.6–445.7.
- **Rust and Go are context only.** The 2026-11-02 report compared against Zig. These rows show Neo ahead
  of both on every x86 row.

**Not adopted: 2 lanes per vector on x86-64 as well.** Variants from the experiment copy (`x86-compute.json`):

- `w2` (K = 8 in 4 groups of 2, as on ARM): Mandelbrot 100.2 ms on 1 worker and 51.7 ms on 2. That is
  1.45× faster than main and 1.16× faster than this branch.
  - Reason: baseline x86-64 is SSE2, 128-bit registers like NEON. LLVM splits a `<8 x double>` mask into
    four XMM registers and repacks it with `packssdw`/`pmovmskb`. With width 2 the mask is one `cmplepd`
    result per register, and `movmskpd` tests it. The escape loop shrinks from 186 to 162 instructions.
  - Not changed here: x86 compute margins belong to another session, and this round was scoped to ARM.
  - To adopt it, `sum_width` returns 2 for x86-64 as well (a one-line change), then re-measure.
- `k4w2` (K = 4): 112.3 / 58.0 ms, slower than `w2`.
- `aw2` (2-lane array vectors on x86): stencil 1M 37.0 against 30.0 ms. Not useful; x86 keeps 4.

## Full CI

Every step of `.github/workflows/verify.yml` passed on both boxes. `scripts/ci.sh` runs them as root, so
without `sudo`:

1. `./neo test`
2. the empty-root HTTP audit
3. two `./neo release` bundles compared with `cmp`
4. the empty-root language, crypto and TLS run

| Box | `./neo test` | Release bundle SHA-256 (both builds equal) | Log |
|---|---|---|---|
| ARM64 Neoverse-N1 | 37 native cases, 0 failed, 26 min 31 s | `755d1f4e…` | `arm64-scaleway/ci-final.log` |
| x86-64 EPYC-Milan | 37 native cases, 0 failed, 13 min 41 s | `064f0aaf…` | `x86-vultr/ci-final.log` |

The two bundle hashes differ because the ARM run came before two non-functional edits to
`neoc/vectorize.py`: a docstring class name, and parentheses that only make the existing `and`/`or`
precedence explicit. The x86 run used the committed tree. The ARM box also passed `./neo test` earlier on
the experiment tree (`neo-test-dev.log`).

## Caveats

- **Shared vCPUs.** The box is a shared-vCPU plan. Interleaving puts every variant through the same
  neighbour noise, but single runs vary. In `final.json`, the 4-worker mandel and stencil rows have
  outliers up to 1.5× their median (ranges below). In `align.json`, each variant had one 1-worker nbody 4096
  run over 2.1 s, about 2.8× its median. Medians are robust to this; maxima are not.
- **Different hardware than the old report.** The 2026-10-27 numbers came from an M1 Pro VM. They are not
  comparable with these, and nothing here says how Neo runs on Apple silicon itself.
- **Rust and Go are as written.** Their sources are the existing `bench/` programs, unchanged: Rust uses
  rayon and Go uses goroutines. Layout and scheduling differ between the languages, and only the outputs
  are required to match.

## Ranges (min–max ms over 9 rounds, `final.json`)

| Case | Workers | Neo after | Neo before | Rust | Go | Bun |
|---|---:|---|---|---|---|---|
| mandel | 1 | 123.6–124.8 | 209.5–210.7 | 237.6–238.8 | 227.8–228.9 | 351.2–361.3 |
| stencil | 1 | 53.2–55.9 | 54.9–56.7 | 68.3–69.8 | 84.5–87.2 | 566.1–606.5 |
| nbody 1024 | 1 | 20.9–22.3 | 20.7–22.0 | 23.7–24.6 | 24.1–25.5 | 158.6–166.7 |
| nbody 4096 | 1 | 768.3–769.2 | 768.7–769.9 | 885.2–886.2 | 865.5–866.9 | 1,569.5–1,574.5 |
| mandel | 4 | 33.0–35.8 | 55.1–74.3 | 62.0–82.0 | 59.8–63.5 | — |
| stencil | 4 | 17.1–21.4 | 17.8–26.7 | 21.9–24.6 | 27.3–34.5 | — |
| nbody 1024 | 4 | 7.6–9.7 | 7.4–9.2 | 8.5–10.3 | 9.6–11.2 | — |
| nbody 4096 | 4 | 195.6–200.9 | 196.3–200.4 | 226.4–228.7 | 222.0–233.2 | — |

## CPU time and peak RSS (median CPU ms / peak RSS MiB, `final.json`)

| Case | Workers | Neo after | Neo before | Rust | Go | Bun |
|---|---:|---:|---:|---:|---:|---:|
| mandel | 1 | 123.7 / 1.4 | 209.8 / 1.4 | 237.9 / 1.8 | 227.8 / 4.9 | 357.6 / 45.3 |
| stencil | 1 | 53.7 / 15.2 | 55.1 / 15.2 | 68.8 / 16.9 | 84.9 / 17.4 | 567.1 / 82.1 |
| nbody 1024 | 1 | 20.8 / 1.5 | 20.8 / 1.4 | 23.6 / 1.9 | 23.8 / 2.1 | 160.0 / 48.9 |
| nbody 4096 | 1 | 768.1 / 1.5 | 768.2 / 1.4 | 884.7 / 2.2 | 865.6 / 5.8 | 1,572.9 / 51.6 |
| mandel | 4 | 123.1 / 1.5 | 209.3 / 1.5 | 237.9 / 1.8 | 227.5 / 4.6 | — |
| stencil | 4 | 54.7 / 15.0 | 58.3 / 15.0 | 74.3 / 16.8 | 87.8 / 17.5 | — |
| nbody 1024 | 4 | 21.5 / 1.5 | 21.3 / 1.5 | 24.9 / 1.8 | 24.7 / 2.1 | — |
| nbody 4096 | 4 | 771.1 / 1.5 | 770.3 / 1.5 | 890.6 / 2.3 | 870.4 / 5.9 | — |
