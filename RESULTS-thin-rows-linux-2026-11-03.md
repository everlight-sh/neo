# Thin Linux rows: huge pages with THP off, AES-GCM on x86-64 and AArch64 (2026-11-03)

After 0.1.2, three Linux rows were ahead of the best other language by less than 1.2×, or behind it:

- the x86-64 sieve with transparent huge pages (THP) set to `never`: 1.09–1.12×;
- the x86-64 4-worker stencil with THP `never`: 1.12–1.16×;
- HTTPS GET /1m on a new connection: 49–57 µs behind Bun on x86-64.

This round fixes all three. It also finds that HTTPS on Linux AArch64 was much slower than everything else: the
TLS client had no hardware AES-GCM there and fell back to ChaCha20-Poly1305, so a 1 MiB download took
2.7–4.4× as long as with the fastest other client. That is fixed too.

**Result.** Every row below now has a margin of at least 1.03× over the best other client or language,
measured against `main` (v0.1.2, `5a5d3f2`) on the same box in the same interleaved rounds. Two ARM compute
rows (the sieve and N-body) remain under 1.2×; see "Still thin".

| Row | Before | After | Best other | Margin before → after |
|---|---:|---:|---|---:|
| x86-64 sieve 100M, THP never, 1 worker | 506.5 ms | 394.4 ms | Zig 540.2 ms | 1.07× → **1.37×** |
| x86-64 sieve 100M, THP never, 4 workers | 465.6 ms | 377.9 ms | Rust 496.2 ms | 1.07× → **1.31×** |
| x86-64 stencil 1M×20, THP never, 4 workers | 14.5 ms | 13.1 ms | Rust 19.4 ms | 1.33× → **1.48×** |
| x86-64 stencil 50M×20, THP never, 4 workers | 496.1 ms | 385.9 ms | Zig native 603.5 ms | 1.22× → **1.56×** |
| AArch64 sieve 100M, THP never, 1 worker | 704.4 ms | 628.2 ms | Rust 738.2 ms | 1.05× → **1.18×** |
| AArch64 stencil 50M×20, THP never, 4 workers | 684.1 ms | 577.7 ms | Rust 893.3 ms | 1.31× → **1.55×** |
| x86-64 HTTPS /1m, new connection | 2,445 µs | 2,273 µs | Bun 2,364 µs | 0.97× → **1.04×** |
| x86-64 HTTPS /1m, kept-alive | 1,504 µs | 1,344 µs | Rust 1,387 µs | 0.92× → **1.03×** |
| x86-64 HTTPS /1m, resumed | 2,191 µs | 2,030 µs | Rust 2,185 µs ¹ | 1.00× → **1.08×** |
| AArch64 HTTPS /1m, new connection | 10,600 µs | 3,484 µs | Bun 3,905 µs | 0.37× → **1.12×** |
| AArch64 HTTPS /1m, kept-alive | 9,001 µs | 1,921 µs | Rust 2,038 µs | 0.23× → **1.06×** |
| AArch64 HTTPS /1m, resumed | 10,093 µs | 3,055 µs | Rust 3,169 µs ¹ | 0.31× → **1.04×** |

The margin is the best other median divided by Neo's. Compute rows are median complete-process wall time over
7 interleaved rounds. HTTPS rows are the median of 5 interleaved rounds of each client's per-request p50, 100
requests per round.

¹ As in the earlier HTTPS reports, the Rust client reuses one reqwest `Client` with pooling off, so rustls
resumes the TLS 1.3 session; it is compared with Neo's resumed row.

The x86-64 box here is an EPYC-Rome, not the EPYC-Milan of the 0.1.2 reports, so the "before" margins differ
from the ones quoted above. Every before/after pair in this report was measured on one box.

Raw data, scripts, machine details and binary hashes are in `bench/core/results/2026-11-03-thin-rows/`.

## Machines

Both boxes were temporary, created for this round and destroyed afterwards.

| | x86-64 | AArch64 |
|---|---|---|
| Instance | Vultr `voc-c-4c-8gb-75s-amd`, Amsterdam | Scaleway `BASIC2-A4C-8G`, fr-par-2 |
| CPU | AMD EPYC-Rome, 4 vCPUs = 2 cores × 2 SMT threads | Ampere Altra (Neoverse-N1), 4 vCPUs, one thread per core; `aes` and `pmull` in HWCAP |
| RAM | 8 GB | 8 GB |
| OS | Ubuntu 24.04.5, Linux 6.8.0-146-generic | Ubuntu 24.04.5, Linux 6.8.0-147-generic |
| THP | `enabled` set to `madvise` or `never` per row; `defrag=madvise` | same |
| Toolchains | clang 18.1.3, Go 1.25.14, Rust 1.99.1, Bun 1.3.13, Zig 0.17.0 | clang 18.1.3, Go 1.25.14, Rust 1.99.1, Bun 1.3.13 |

Four vCPUs are the fewest that run the 4-worker rows. Pinning follows the harnesses: one worker on CPU 0, four
workers on CPUs 0–3; for HTTPS the Go net/http server and every client run on CPU 0.

- "Before" is `main` at v0.1.2 (`5a5d3f2`).
- "After" is that commit plus this change (the tree this report describes).
- Every Neo executable was built with `./neo build … --no-cache`.

## Compute

x86-64 used `bench/compute-margins/run.py` (Neo after and before, Zig baseline and native, Rust). AArch64 used
`bench/core/compute_compare.py` (Neo after and before, Rust, Go); there is no Zig toolchain on that box. Both
write each THP setting to `/sys/kernel/mm/transparent_hugepage/enabled` before its rounds. Every output was
checked against the other variants.

### x86-64 (`x86-vultr/final.json`)

| THP | Row | Workers | Before ms | After ms | Change | Best other, ms | Margin before → after |
|---|---|---:|---:|---:|---:|---|---:|
| never | sieve 100M | 1 | 506.5 | 394.4 | −22.1% | Zig 540.2 | 1.07× → 1.37× |
| never | sieve 100M | 4 | 465.6 | 377.9 | −18.8% | Rust 496.2 | 1.07× → 1.31× |
| never | stencil 1M×20 | 1 | 26.6 | 22.2 | −16.5% | Zig 38.9 | 1.46× → 1.75× |
| never | stencil 1M×20 | 4 | 14.5 | 13.1 | −9.9% | Rust 19.4 | 1.33× → 1.48× |
| never | stencil 50M×20 | 1 | 1,410.4 | 1,020.2 | −27.7% | Zig 1,897.4 | 1.35× → 1.86× |
| never | stencil 50M×20 | 4 | 496.1 | 385.9 | −22.2% | Zig native 603.5 | 1.22× → 1.56× |
| never | mandel 1200×1200×300 | 1 / 4 | 119.9 / 32.2 | 119.8 / 32.2 | 0.0% | Zig native 206.1 / Rust 54.2 | 1.72× / 1.68× |
| never | nbody 1024×3 | 1 / 4 | 11.6 / 4.8 | 11.7 / 4.8 | +1.1% / −0.2% | Zig 17.9 / Rust 7.3 | 1.53× / 1.53× after |
| never | nbody 4096×10 | 1 / 4 | 383.8 / 100.0 | 383.6 / 99.8 | 0.0% | Zig native 693.2 / Rust 180.8 | 1.81× / 1.81× |
| madvise | sieve 100M | 1 | 391.9 | 381.4 | −2.7% | Zig 542.5 | 1.38× → 1.42× |
| madvise | sieve 100M | 4 | 350.1 | 355.1 | +1.4% | Zig 470.5 | 1.34× → 1.33× |
| madvise | stencil 1M×20 | 1 / 4 | 22.8 / 10.9 | 20.9 / 10.9 | −8.5% / −0.5% | Zig 39.1 / Rust 18.6 | 1.87× / 1.71× after |
| madvise | stencil 50M×20 | 1 / 4 | 1,010.7 / 327.7 | 1,008.0 / 327.7 | 0.0% | Zig 1,858.6 / Zig native 600.5 | 1.84× / 1.83× |
| madvise | mandel, nbody (all six rows) | 1, 4 | | | −2.3% to +0.3% | | 1.53×–1.81× after |

With THP `madvise` the new code does not run (see "Huge pages with THP off"). The madvise rows move by −8.5% to
+1.4%, inside each other's ranges: for example, the 4-worker sieve's ranges are 343–391 ms before and 351–398 ms
after. An earlier 9-round run (`collapse-ab.json`) put the same row at +3.8%. The sieve executables differ, since
the new allocator code is compiled in even where it does not run; whether that layout change costs anything was
not isolated. The mandel executable is byte-identical to main's.

### AArch64 (`arm64-scaleway/final-madvise.json`, `final-never.json`)

| THP | Row | Workers | Before ms | After ms | Change | Best other, ms | Margin before → after |
|---|---|---:|---:|---:|---:|---|---:|
| never | sieve 100M | 1 | 704.4 | 628.2 | −10.8% | Rust 738.2 | 1.05× → 1.18× |
| never | sieve 100M | 4 | 700.5 | 631.3 | −9.9% | Rust 724.0 | 1.03× → 1.15× |
| never | stencil 1M×20 | 1 | 51.0 | 47.4 | −7.1% | Rust 69.2 | 1.35× → 1.46× |
| never | stencil 1M×20 | 4 | 18.8 | 17.0 | −9.3% | Rust 22.8 | 1.21× → 1.34× |
| never | stencil 50M×20 | 1 | 2,376.6 | 2,111.7 | −11.1% | Rust 3,228.7 | 1.36× → 1.53× |
| never | stencil 50M×20 | 4 | 684.1 | 577.7 | −15.6% | Rust 893.3 | 1.31× → 1.55× |
| never | nbody 1024×3 | 1 / 4 | 21.4 / 9.1 | 21.2 / 8.9 | −0.9% / −1.6% | Rust 24.2 / Rust 10.4 | 1.14× / 1.17× after |
| never | nbody 4096×10 | 1 / 4 | 775.2 / 196.2 | 776.7 / 198.1 | +0.2% / +0.9% | Go 874.2 / Go 224.3 | 1.13× / 1.13× after |
| never | mandel 1200×1200×300 | 1 / 4 | 124.5 / 33.5 | 124.9 / 38.6 | +0.3% / +15.3% | Go 229.1 / Go 62.8 | 1.83× / 1.63× after |
| madvise | sieve 100M | 1 / 4 | 625.2 / 621.4 | 623.5 / 625.3 | −0.3% / +0.6% | Rust 732.3 / Rust 708.5 | 1.17× / 1.13× after |
| madvise | stencil 1M×20 | 1 / 4 | 47.8 / 16.8 | 47.4 / 16.2 | −0.8% / −3.6% | Rust 70.6 / Rust 23.2 | 1.49× / 1.44× after |
| madvise | stencil 50M×20 | 1 / 4 | 2,100.5 / 534.3 | 2,099.3 / 553.8 | −0.1% / +3.7% | Rust 3,215.4 / Rust 894.4 | 1.53× / 1.62× after |
| madvise | nbody, mandel (all six rows) | 1, 4 | | | −8.9% to +0.9% | | 1.12×–1.84× after |

Two rows move without a code change:

- **Mandel, 4 workers, never: +15.3%.** Its executable is byte-identical to main's. Both variants' runs spread
  between 33 and 51 ms. After: 33.3, 33.3, 34.5, 38.6, 42.2, 44.2 and 45.2 ms. Before: 33.1, 33.3, 33.5, 33.5,
  34.5, 43.1 and 51.1 ms. This is how noisy a 4-worker run of a few tens of milliseconds is on this shared-vCPU
  plan.
- **Stencil 50M, 4 workers, madvise: +3.7%.** The final executables are byte-identical to those of an earlier
  run (`collapse-ab-madvise.json`), and in that run the same row was 537.1 against 539.2 ms (−0.4%).

## HTTPS

`scripts/ab-https.sh` runs every client in turn, 100 sequential GET /1m requests each, five rounds. The
clients are:

- main's `fetch.neo` and this tree's, each on a new connection, kept-alive and resumed;
- Bun `fetch`, new and kept-alive;
- Rust reqwest, new (which resumes) and kept-alive;
- Go net/http, new and kept-alive.

Each cell is the median of the five rounds' p50, in µs.

| | Neo main | Neo now | Bun | Rust | Go |
|---|---:|---:|---:|---:|---:|
| **x86-64** (`x86-vultr/https-ab.log`) | | | | | |
| New connection | 2,445 | **2,273** | 2,364 | 2,185 ¹ | 3,442 |
| Kept-alive | 1,504 | **1,344** | 1,589 | 1,387 | 2,359 |
| Resumed | 2,191 | **2,030** | — | 2,185 ¹ | — |
| **AArch64** (`arm64-scaleway/https-ab.log`) | | | | | |
| New connection | 10,600 | **3,484** | 3,905 | 3,169 ¹ | 5,737 |
| Kept-alive | 9,001 | **1,921** | 2,395 | 2,038 | 3,250 |
| Resumed | 10,093 | **3,055** | — | 3,169 ¹ | — |

Small requests did not get slower. The AArch64 handshake now runs on AES-GCM instead of ChaCha20-Poly1305, so
it was checked separately:

| Interleaved check | Neo main | Neo now |
|---|---:|---:|
| x86-64, one request per process (GET /hello, 400 runs each) | 2.203 ms | 2.182 ms |
| AArch64, one request per process (GET /hello, 400 runs each) | 6.424 ms | 6.452 ms |
| AArch64, GET /hello on a new connection (5 rounds, p50) | 1,612 µs | 1,629 µs |
| AArch64, GET /hello resumed | 1,092 µs | 1,090 µs |
| AArch64, GET /hello kept-alive | 74.6 µs | 71.4 µs |

The AArch64 new-connection runs overlap (1,593–1,709 µs before, 1,588–1,754 µs after); Bun's were 1,729–1,871 µs
in the same rounds.

The full harness, `bench/fetch/run.py --schemes https`, was also run on the final tree on both boxes; its tables
are in `fetch-final/` next to main's in `fetch-main/`. Those were separate runs, and this shared-vCPU AArch64 box
drifts between runs. For example, one request per process read 4.72 ms on main and 5.61 ms on the final tree
there, while the interleaved check above shows the two level at 6.4 ms. The interleaved tables are the
comparison.

On x86-64, a client process that downloads 200 × 1 MiB over one connection (`scripts/prof-ab.sh`) went from:

- 1.429 G to 0.904 G instructions;
- 602 M to 485 M cycles.

The GCM kernel's share of sampled cycles fell from 52.9% to 40.0%. That is about 1.52 cycles per byte before and
0.92 after, by share × cycles ÷ 209,715,200 bytes.

## What changed

### Huge pages with THP off (`runtime/core.neo`, `runtime/platform_*.neo`)

Large private blocks (4 MiB and up) already ask for huge pages with `MADV_HUGEPAGE`. With THP set to `never`,
the kernel ignores that advice, so a 400 MB array faulted in 4 KiB at a time. Avoiding that makes the sieve and
the stencil 7–28% faster with THP off (tables above).

- **Detection.** On Linux the runtime now reads `/sys/kernel/mm/transparent_hugepage/enabled` once per process
  and caches the answer.
- **Collapse.** When THP is `never`, `rt_large_block` writes one zero byte into each 2 MiB region that a fresh
  block's requested bytes cover entirely. That creates the page tables. One `MADV_COLLAPSE` (Linux 6.1+) then
  backs all those regions with huge pages; unlike `MADV_HUGEPAGE`, it works whatever the THP setting.
- **Fallback.** An unreadable file, any other setting, or a failed collapse (an older kernel, or no free huge
  page) caches "advice" and keeps the old path.
- **Where it runs.** Only fresh private blocks of 4 MiB and up. Reused blocks and shared blocks are untouched,
  and so is every Darwin target: `rt_collapse` and `rt_huge_fallback` are constant there.

`scripts/collapse.c` is the C probe that first checked that `MADV_COLLAPSE` succeeds under `never`, on the
x86-64 box. On the final AArch64 executable, the 50M stencil under `never` makes one `openat` of the setting, and
`MADV_COLLAPSE` returns 0 on both 400 MB arrays, with 1 worker and with 4.

The 4-worker 50M stencil is still slower with THP off than with madvise: 385.9 against 327.7 ms on x86-64. Each
block's collapse runs in one thread, while with madvise the workers fault their own parts in parallel; that
difference was not measured separately.

### Faster AES-GCM on x86-64 (`stdlib/aes.neo`, `neoc/llvm.py`, `neoc/check.py`)

- **`block_xor_low` / `block_xor_high`.** These new builtins return the halves of the XOR of two 128-bit blocks,
  emitted as one `xor <2 x i64>`. AES and GHASH values used to be combined with two scalar XORs, which moved them
  between vector and general registers on every step. Now LLVM keeps them in XMM registers (NEON registers on
  AArch64).
- **A shift-free GHASH reduction.** Each key power is stored multiplied by x⁻¹: a 1-bit left shift, with the bit
  shifted out folded back in as bits 0, 121, 126 and 127. Products then need no 1-bit shift. The 256-bit
  Karatsuba product is reduced with two carry-less multiplies by 0xC2…00 instead of the earlier shift-and-XOR
  sequence (Gueron and Kounavis, algorithm 5).
- **In-place output with proven bounds.** The 8-block loop writes the output through a set-only loop state.
  Refinement types on its index (`at:i64{at>=0}` with `at+128<=count`, and `at+128<=m` on the loads) prove every
  load and store in bounds. `check.py` now proves constant-width `byte_write_le` bounds the same way it already
  proved `byte_read_le`, and `llvm.py` drops the width and bounds traps when they are proven.
- **One store per word.** `byte_write_le` with a constant width of 1, 2, 4 or 8 now lowers to a single
  little-endian store, as `byte_read_le` already loaded. clang 18 did not merge the old per-byte stores: an
  8-block step wrote its 128 output bytes with 128 byte stores.

### AES-GCM on Linux AArch64 (`neoc/llvm.py`)

Before, `aes_hardware()` was false on every target but x86-64, the AES builtins trapped there, and the TLS
client offered ChaCha20-Poly1305 first. With it, a kept-alive 1 MiB request took 9.0 ms on this CPU; with
AES-GCM it takes 1.9 ms.

On Linux AArch64 the builtins now lower to the ARMv8 Cryptography Extension:

- **AES round.** `aes_round` is AESE with a zero key, then AESMC, then an XOR with the round key; LLVM folds that
  XOR into the next AESE. `aes_final_round` is AESE, then the XOR.
- **Other builtins.** `carryless_mul_low/high` is PMULL, and `block_xor` is EOR.
- **Detection.** `aes_hardware()` finds `AT_HWCAP` in the auxiliary vector, which follows `envp`'s terminating
  null. It requires the AES and PMULL bits, and caches the answer.
- **Compilation.** Functions that use the builtins, and their callers that force-inline them, are compiled with
  `+aes`.

With that, the TLS client offers AES-128-GCM first on this CPU, as it already did on x86-64.

macOS is unchanged here: `aes_hardware()` is still false and the builtins still trap, so the macOS client keeps
ChaCha20 first.

### Tests

- `tests/test_systems.py` checks the AArch64 Linux lowering (AESE, AESMC, PMULL64, `+aes`, no trap), that
  arm64 macOS still traps, and that `block_xor` needs `unsafe` and lowers to a vector XOR.
- `tests/test_proved_checks.py` checks that a guarded constant-width `byte_write_le` has no runtime check and
  an unguarded one keeps its bounds check.

## Correctness

On both boxes, with the final tree:

- **`tests/aes_language.py` passes.** It covers NIST AES-128 block and GCM vectors, and 40 GCM cases compared
  with Go's `crypto/aes` through both the portable and the fast path, with `aes_hardware()` true. It also covers
  boundary sizes (0 to 16,385 bytes), round trips, and no plaintext after a corrupted tag or nonce.
- **`python3 -m unittest tests.test_systems tests.test_proved_checks`: 30 tests pass.**
- **The `verify.yml` steps pass** (`scripts/ci.sh`; logs in `x86-vultr/ci.log` and `arm64-scaleway/ci.log`):
  - `./neo test`: 31 Bun tests, server-rendering parity with React on 1 and 4 workers, and 40 native cases;
  - the freestanding HTTP smoke test from an empty root;
  - a reproducible `neo release`;
  - the empty-root language, crypto and TLS fixtures.

## Tried and dropped

**Check before store, AArch64 sieve.** The sieve could skip the store when the byte is already cleared. On
the N1 that made the sieve slower: 590 → 785 ms (+33%) with THP madvise and 604 → 807 ms (+34%) with never,
medians of 9 interleaved rounds (`cbs.log`). It is not in this change. It did help two of the four strided
microbenchmarks in the same log (flip and random at stride 64), but not at stride 256.
`scripts/arm-cbs.sh` is the experiment.

## macOS

Nothing ran on macOS. Its executables were built there and compared, without being run:

- **Compute and HTTP executables:** `sieve`, `stencil`, `nbody` and `http` have the same machine code as main's.
  The collapse path folds away there, because `rt_huge_fallback` is the constant false.
- **The TLS client (`bench/fetch/fetch.neo`) changes.**
  - 128 of its 206 functions differ, and 98 of those keep the same instruction count.
  - The largest changes are in the TLS handshake functions: `tls12_handshake` 31,339 → 31,193 instructions,
    `tls13_handshake` 17,226 → 17,109, `tls_handshake` 17,773 → 17,877, and `poly_finish` 194 → 166.
  - The cause is the two `byte_write_le` changes, which apply on every target: the one-store lowering, and
    dropping its checks where the bounds are proven. The same bytes are written in the same little-endian
    order as before. They were not measured separately on macOS.
- **AES-GCM is still off** there, as described above.

## Still thin

- **AArch64 sieve: 1.13–1.18×** against Rust under both THP settings. Check-before-store was slower; see
  "Tried and dropped".
- **AArch64 N-body: 1.12–1.17×.** It already runs at about 96% of the N1's divide and square-root throughput
  (`RESULTS-compute-arm64-linux-2026-11-03.md`).
- **HTTPS copies.** HTTPS bodies are still copied about three times per MiB: the record slice, the body append,
  and growth reallocations. Each record is also zero-filled. `memcpy` and `memset` are 15% of the kept-alive
  client's samples on x86-64. Decrypting into the body buffer, and sizing it from `Content-Length`, would remove
  most of that.
