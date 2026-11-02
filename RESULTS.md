# Results

Machine: Apple M1 Pro, 10 cores. Apple clang version 21.0.0 (clang-2100.1.1.101); rustc 1.95.0 (59807616e 2026-04-14); go version go1.25.1 darwin/arm64.
Wall-clock time of the whole process, best of 7 runs (median in parentheses). 'vs Rust' is Rust's best time divided by that row's best time (above 1.00x = faster than Rust). CPU/wall is total CPU seconds over wall seconds, i.e. how many cores the process kept busy; the machine has 8 performance and 2 efficiency cores.

## mandel

Mandelbrot escape-time sum, 3000x3000 grid, 2000 max iterations (compute-bound, uneven rows). Args: `3000 3000 2000`.

| Language | Best | Median | vs Rust | CPU/wall |
|---|---|---|---|---|
| Neo | 0.459s | (0.498s) | 3.07x | 7.1 |
| Rust | 1.411s | (1.619s) | 1.00x | 7.0 |
| Go | 1.259s | (1.337s) | 1.12x | 8.8 |
| Rust (rayon, max_len 4) | 1.224s | (1.245s) | 1.15x | 9.0 |

Outputs: Neo = 3063818920, Rust = 3063818920, Go = 3063818731, Rust (rayon, max_len 4) = 3063818920

## stencil

3-point i64 stencil, n=50M, 20 passes, then checksum (memory-bound; every index carries a proof obligation). Args: `50000000 20`.

| Language | Best | Median | vs Rust | CPU/wall |
|---|---|---|---|---|
| Neo | 0.207s | (0.210s) | 1.07x | 8.0 |
| Rust | 0.221s | (0.231s) | 1.00x | 8.5 |
| Go | 0.324s | (0.531s) | 0.68x | 5.9 |

Outputs: Neo = 25000046624222, Rust = 25000046624222, Go = 25000046624222

## stencil_small

Same stencil, n=1M (8MB, cache-resident), 2000 passes: compute-bound, so bounds checks and per-pass dispatch overhead show. Args: `1000000 2000`.

| Language | Best | Median | vs Rust | CPU/wall |
|---|---|---|---|---|
| Neo | 0.402s | (0.432s) | 1.81x | 5.9 |
| Rust | 0.728s | (0.742s) | 1.00x | 7.7 |
| Go | 0.737s | (0.790s) | 0.99x | 4.6 |

Outputs: Neo = 499967939935, Rust = 499967939935, Go = 499967939935

## nbody

N-body, 16384 bodies, 10 leapfrog steps, softening 0.01, prints total energy. Neo: records laid out struct-of-arrays by the compiler and an order-free `sum`; Rust and Go: idiomatic array-of-structs. Args: `16384 10`.

| Language | Best | Median | vs Rust | CPU/wall |
|---|---|---|---|---|
| Neo | 0.406s | (0.426s) | 1.31x | 7.8 |
| Rust | 0.532s | (0.594s) | 1.00x | 8.2 |
| Go | 0.700s | (0.715s) | 0.76x | 7.3 |

Outputs: Neo = -0.89457810633378965, Rust = -0.89457810633378965, Go = -0.89457810633378931

## Reading the numbers (after the language additions)

- **Mandelbrot: Neo 3.1x idiomatic Rust, 2.7x tuned Rust and Go.** This is the cross-iteration vectoriser: the escape loop has a data-dependent trip count, so LLVM will not vectorise it for anyone. Neo's `sum` body has no dependencies between iterations, so the compiler runs 16 pixels per SIMD register with masked loops (`neoc/vectorize.py`); the checksum is identical to the scalar build. Lane counts of 2, 4, 8, 16 and 32 gave 1.78, 1.17, 0.72, 0.43 and 0.61 s; 16 is the default. Rust could match this only with hand-written SIMD.
- **Stencil, memory-bound: parity with Rust (1.07x), 1.6x Go.** Bandwidth-limited; nothing to win here.
- **Stencil, cache-resident: 1.8x Rust and Go.** The rayon `enumerate` shape leaves three bounds checks per element in Rust; Neo proved them away. A plain indexed Rust loop would close most of this gap (see RESULTS-http-compute.md).
- **N-body: 1.31x Rust, 1.72x Go.** Two language-level effects. `Arr Body n` is laid out struct-of-arrays by the compiler, so the inner loop streams contiguous planes; Rust's `Vec<Body>` is array-of-structs. And Neo's `sum` over `f64` is order-free by definition, so the reduction is emitted with `reassoc` and vectorises; Rust's `+=` chain must stay sequential. Energies agree to 15 digits across all three (each language's own reduction order differs in the last digit, and rayon's parallel sum is nondeterministic there).
- **Parallel efficiency** (CPU/wall) is similar across languages on each benchmark.

## Caveats

Two to four programs on one machine are not a language benchmark. All implementations are idiomatic first drafts, not tuned; each Rust program could be brought to Neo's level with manual SIMD, SoA data structures, `get_unchecked` or unsafe reassociation intrinsics. The point of every row is that Neo gets there from the naive program because the language removes the constraint that stops LLVM: false dependencies, a fixed layout, a fixed summation order, or a bounds check the compiler cannot see through. Timings are whole-process wall clock, best of 7, and vary about 10 to 20 percent between runs on this laptop.
