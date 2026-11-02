# Stencil after compiler and kernel-worker optimization — 2026-10-24

Native ARM64 Linux on Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Measured 2026-10-24T10:07:02.308018+00:00. 21 measured process runs after two warmups; seeded shuffled implementation order every round. One worker is pinned to CPU 0; four workers to CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. GNU time/taskset startup, initialization, allocation, every pass, checksum and shutdown are included. No emulation or persistent benchmark service. Host load can vary, so the previous Axon executable is rerun in the same interleaved rounds.

Axon, Rust/Rayon and Go sources are unchanged from the prior compute report: signed i64 data, the same seed, the same 3-point recurrence modulo 1,000,003, copied endpoints and all requested passes. Every checksum must agree across all four executables. Axon retains checked application arithmetic. No tiling, reduced iteration count, cached result, or changes to competitors.

| Elements | Passes | Workers | Implementation | Median wall ms | Min–max ms | Median CPU ms | Max process peak RSS MiB |
|---:|---:|---:|---|---:|---:|---:|---:|
| 1,000,000 | 20 | 1 | Axon | 22.06 | 21.40–23.46 | 20.93 | 15.25 |
| 1,000,000 | 20 | 1 | Axon previous | 37.65 | 36.41–69.32 | 36.21 | 15.25 |
| 1,000,000 | 20 | 1 | Rust | 37.26 | 36.20–63.60 | 35.98 | 16.88 |
| 1,000,000 | 20 | 1 | Go | 41.47 | 39.85–44.98 | 39.77 | 17.25 |
| 1,000,031 | 20 | 1 | Axon | 22.24 | 20.82–26.03 | 20.93 | 15.25 |
| 1,000,031 | 20 | 1 | Axon previous | 37.38 | 35.92–41.33 | 36.25 | 15.25 |
| 1,000,031 | 20 | 1 | Rust | 37.25 | 35.71–45.69 | 35.94 | 16.75 |
| 1,000,031 | 20 | 1 | Go | 41.31 | 39.43–46.45 | 39.50 | 17.25 |
| 65,537 | 100 | 1 | Axon | 7.42 | 6.38–8.88 | 6.22 | 1.38 |
| 65,537 | 100 | 1 | Axon previous | 12.49 | 11.40–15.40 | 11.26 | 1.38 |
| 65,537 | 100 | 1 | Rust | 13.76 | 12.39–38.14 | 12.42 | 2.50 |
| 65,537 | 100 | 1 | Go | 15.88 | 13.94–88.67 | 14.05 | 2.62 |
| 8,000,000 | 20 | 1 | Axon | 158.04 | 153.71–173.95 | 156.72 | 122.00 |
| 8,000,000 | 20 | 1 | Axon previous | 279.48 | 273.83–358.91 | 278.17 | 122.00 |
| 8,000,000 | 20 | 1 | Rust | 275.07 | 268.87–353.48 | 273.60 | 123.50 |
| 8,000,000 | 20 | 1 | Go | 296.10 | 281.65–344.68 | 294.48 | 124.12 |
| 1,000,000 | 1 | 1 | Axon | 8.58 | 7.88–11.60 | 7.52 | 15.25 |
| 1,000,000 | 1 | 1 | Axon previous | 9.14 | 8.48–12.91 | 8.17 | 15.25 |
| 1,000,000 | 1 | 1 | Rust | 8.41 | 7.62–12.51 | 7.18 | 16.75 |
| 1,000,000 | 1 | 1 | Go | 10.46 | 9.28–19.48 | 8.75 | 17.25 |
| 1,000,000 | 20 | 4 | Axon | 13.90 | 11.81–21.82 | 31.63 | 15.00 |
| 1,000,000 | 20 | 4 | Axon previous | 26.46 | 22.35–41.92 | 66.65 | 3.88 |
| 1,000,000 | 20 | 4 | Rust | 15.17 | 13.14–24.51 | 43.35 | 16.88 |
| 1,000,000 | 20 | 4 | Go | 19.04 | 16.16–45.62 | 45.60 | 17.50 |
| 1,000,031 | 20 | 4 | Axon | 16.47 | 12.02–57.47 | 38.62 | 15.00 |
| 1,000,031 | 20 | 4 | Axon previous | 28.77 | 22.92–143.99 | 73.07 | 3.88 |
| 1,000,031 | 20 | 4 | Rust | 17.22 | 13.54–32.27 | 48.33 | 16.88 |
| 1,000,031 | 20 | 4 | Go | 19.20 | 16.52–57.00 | 47.12 | 17.50 |
| 65,537 | 100 | 4 | Axon | 8.26 | 6.99–12.76 | 6.82 | 1.38 |
| 65,537 | 100 | 4 | Axon previous | 32.36 | 25.18–78.57 | 52.39 | 1.38 |
| 65,537 | 100 | 4 | Rust | 11.97 | 6.97–57.15 | 24.81 | 2.62 |
| 65,537 | 100 | 4 | Go | 15.19 | 11.83–32.56 | 20.15 | 3.00 |
| 8,000,000 | 20 | 4 | Axon | 66.72 | 60.28–92.96 | 208.13 | 122.00 |
| 8,000,000 | 20 | 4 | Axon previous | 155.53 | 144.74–271.72 | 494.27 | 30.62 |
| 8,000,000 | 20 | 4 | Rust | 83.97 | 80.25–184.22 | 301.95 | 123.75 |
| 8,000,000 | 20 | 4 | Go | 92.68 | 86.35–232.58 | 318.17 | 124.38 |
| 1,000,000 | 1 | 4 | Axon | 6.19 | 5.62–13.61 | 12.53 | 15.00 |
| 1,000,000 | 1 | 4 | Axon previous | 6.23 | 5.68–8.38 | 12.63 | 3.88 |
| 1,000,000 | 1 | 4 | Rust | 5.53 | 4.88–7.54 | 9.61 | 16.88 |
| 1,000,000 | 1 | 4 | Go | 7.43 | 6.59–8.29 | 10.63 | 17.38 |

## Changes and limits

- General scalar array comprehensions now emit four-lane vectors for arithmetic and affine reads. The compiler intersects every source array’s valid interval, including speculative branch loads; prefix, suffix and vector tails remain scalar. Checked arithmetic uses masked overflow checks unless existing lexical/whole-program facts prove safety. Bounded remainders also lower inside vectors.
- Allocation-free vector bodies on Linux use raw clone(CLONE_VM | SIGCHLD) workers with separate aligned stacks and waitable process identities. Axon owns scheduling, stack allocation, joins and spawn-failure fallback. A small compiler-emitted ARM64/x86-64 stack-switch boundary makes the raw syscall; it calls no library. Workers never touch the allocator. Allocating bodies retain isolated fork workers. Stacks and contexts stay alive through the join.
- Straight-line vector bodies use an estimated work threshold (one million AST work units per configured worker) before creating workers. Small cheap passes can run sequentially within the four-CPU budget. Calls/loops retain the existing range threshold. The runtime still creates workers per parallel region; this does not implement a persistent pool. macOS keeps fork workers and its platform-required libSystem loader command. Native performance was measured only on Linux ARM64; x86-64 correctness under emulation is separate evidence. [QEMU 8.2.2 rejects this waitable CLONE_VM form](https://github.com/qemu/qemu/blob/v8.2.2/linux-user/syscall.c#L6172-L6175), so its tests exercise the sequential spawn-failure fallback; native x86-64 worker ABI verification remains for the configured CI job.
- RSS is GNU time’s maximum per-process resident high-water mark, not summed worker RSS, cgroup memory or virtual reservations. Shared-address worker mappings must not be counted repeatedly. CPU includes waited descendants.
- Linux Axon executables have no undefined symbols, ELF interpreter, DT_NEEDED entry, C runtime or shared-library dependency. Python/LLVM remain build tools. See retained nm/readelf output.

## Binary size

| Implementation | Bytes |
|---|---:|
| Axon | 25,704 |
| Axon previous | 23,512 |
| Rust | 559,984 |
| Go | 2,300,760 |

Raw commands, outputs, build reports, tool versions, checksums, samples and hashes: `/axon/bench/stencil/results/2026-10-24-100702`.

## Verification and regression results

The complete suite passed on macOS and native ARM64 Linux after the final changes. A complete explicit-QEMU x86-64 run passed before the final scheduling threshold, followed by final SIMD/array/worker-fallback tests on x86-64. The configured native x86-64 CI job has not been run here; the x86-64 shared-address stack switch cannot be exercised by this QEMU clone implementation. Native ARM64 worker creation/callback/shared writes/joins passed 20 direct ABI probes, including empty-root execution.

Per platform, stencil differential coverage includes 2,080 signed-seed/tail/pass-count cases with range optimization on/off. Additional SIMD-on/off checks cover affine offsets, several source arrays, negative origins, empty interiors, f64 loads/stores, masked overflow, active overflow (including a child worker), near-i64-limit induction, allocating-body isolation and forced clone EAGAIN fallback. Full suites also cover compiler/reference equivalence, JSON strictness and ownership, applications, HTTP/pipelining and the React example.

A fresh container built the HTTP server, stencil and direct worker ABI probe. Each ran inside an otherwise empty root with no loader, libraries, /proc or runtime files. Static symbol/ELF audits passed. No C runtime dependency was introduced.

The RSS column needs care when comparing previous/current Axon: fork workers touch their shares in separate address spaces, whereas CLONE_VM workers share one RSS account. The lower previous per-process RSS does not establish a lower physical footprint. This run did not separately measure cgroup peak memory.

The original 1,000,000-element/20-pass case: Axon won 21/21 single-CPU rounds and 14/21 four-CPU rounds against Rust. Four-CPU medians are 13.90 vs 15.17 ms (8.4% lower wall time), with 31.63 vs 43.35 CPU ms (27.0% lower CPU time). The preserved previous Axon executable measured 26.46 ms in these rounds. Timing ranges overlap on this shared host. Rust retains the one-pass win (5.53 vs Axon 6.19 ms on four CPUs).

[Separate nine-run Mandelbrot/stencil/N-body regression report](RESULTS-compute-after-stencil-linux-2026-10-24.md) also checks all outputs and one/four CPU budgets.

Unchanged dynamic JSON workload, 1,000,000 documents, one CPU, nine measured runs after two warmups with shuffled order:

| Implementation | Median wall ms | Min–max ms |
|---|---:|---:|
| Axon | 341.60 | 319.12–541.41 |
| Axon before stencil | 337.02 | 326.53–398.73 |
| Rust | 443.74 | 425.69–567.53 |

JSON remains faster than Rust. The small difference between current and previous Axon is within the observed run ranges. JSON commands, checksums and samples are retained in `.kernel-build/stencil-opt/json-regression.json`.

Validation manifest, test logs, reproduction scripts and source snapshot: `.kernel-build/stencil-opt/validation.json` and `.kernel-build/stencil-opt/source.tar.gz`.
