# Stencil after compiler and kernel-worker optimization — 2026-10-24

Native ARM64 Linux on Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Measured 2026-10-24T09:59:07.149111+00:00. 21 measured process runs after two warmups; seeded shuffled implementation order every round. One worker is pinned to CPU 0; four workers to CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. GNU time/taskset startup, initialization, allocation, every pass, checksum and shutdown are included. No emulation or persistent benchmark service. Host load can vary, so the previous Axon executable is rerun in the same interleaved rounds.

Axon, Rust/Rayon and Go sources are unchanged from the prior compute report: signed i64 data, the same seed, the same 3-point recurrence modulo 1,000,003, copied endpoints and all requested passes. Every checksum must agree across all four executables. Axon retains checked application arithmetic. No tiling, reduced iteration count, cached result, or changes to competitors.

| Elements | Passes | Workers | Implementation | Median wall ms | Min–max ms | Median CPU ms | Max process peak RSS MiB |
|---:|---:|---:|---|---:|---:|---:|---:|
| 1,000,000 | 20 | 1 | Axon | 21.37 | 20.40–23.03 | 20.16 | 15.25 |
| 1,000,000 | 20 | 1 | Axon previous | 36.75 | 35.26–41.30 | 35.77 | 15.25 |
| 1,000,000 | 20 | 1 | Rust | 36.30 | 34.80–41.98 | 35.12 | 16.75 |
| 1,000,000 | 20 | 1 | Go | 40.32 | 38.65–46.27 | 38.80 | 17.25 |
| 1,000,031 | 20 | 1 | Axon | 21.58 | 20.91–22.76 | 20.61 | 15.25 |
| 1,000,031 | 20 | 1 | Axon previous | 36.57 | 35.71–38.83 | 35.43 | 15.25 |
| 1,000,031 | 20 | 1 | Rust | 36.51 | 35.47–50.52 | 35.36 | 16.75 |
| 1,000,031 | 20 | 1 | Go | 40.06 | 39.19–42.02 | 38.54 | 17.12 |
| 65,537 | 100 | 1 | Axon | 6.66 | 6.25–7.60 | 5.74 | 1.38 |
| 65,537 | 100 | 1 | Axon previous | 11.74 | 11.13–12.29 | 10.77 | 1.38 |
| 65,537 | 100 | 1 | Rust | 12.76 | 12.06–13.27 | 11.70 | 2.50 |
| 65,537 | 100 | 1 | Go | 14.50 | 13.69–15.37 | 12.95 | 2.62 |
| 8,000,000 | 20 | 1 | Axon | 158.74 | 151.12–471.89 | 157.47 | 122.00 |
| 8,000,000 | 20 | 1 | Axon previous | 292.15 | 273.11–438.32 | 290.69 | 122.00 |
| 8,000,000 | 20 | 1 | Rust | 275.74 | 264.76–536.08 | 273.74 | 123.62 |
| 8,000,000 | 20 | 1 | Go | 316.18 | 284.77–879.92 | 314.05 | 124.12 |
| 1,000,000 | 1 | 1 | Axon | 8.56 | 8.03–12.64 | 7.49 | 15.25 |
| 1,000,000 | 1 | 1 | Axon previous | 9.69 | 8.73–23.79 | 8.42 | 15.25 |
| 1,000,000 | 1 | 1 | Rust | 8.50 | 7.46–11.09 | 7.07 | 16.75 |
| 1,000,000 | 1 | 1 | Go | 11.14 | 10.10–21.05 | 9.01 | 17.25 |
| 1,000,000 | 20 | 4 | Axon | 13.26 | 11.24–16.08 | 31.21 | 15.12 |
| 1,000,000 | 20 | 4 | Axon previous | 24.35 | 22.72–36.22 | 64.03 | 3.88 |
| 1,000,000 | 20 | 4 | Rust | 14.49 | 13.45–19.26 | 42.28 | 16.88 |
| 1,000,000 | 20 | 4 | Go | 18.12 | 16.29–22.39 | 44.47 | 17.50 |
| 1,000,031 | 20 | 4 | Axon | 13.23 | 10.68–43.91 | 30.51 | 15.00 |
| 1,000,031 | 20 | 4 | Axon previous | 25.49 | 20.87–51.41 | 66.50 | 3.88 |
| 1,000,031 | 20 | 4 | Rust | 14.75 | 12.76–29.71 | 44.00 | 16.88 |
| 1,000,031 | 20 | 4 | Go | 17.68 | 15.71–34.28 | 44.03 | 17.50 |
| 65,537 | 100 | 4 | Axon | 15.56 | 13.70–24.15 | 21.86 | 1.38 |
| 65,537 | 100 | 4 | Axon previous | 26.25 | 22.58–33.99 | 45.31 | 1.38 |
| 65,537 | 100 | 4 | Rust | 8.34 | 7.02–15.84 | 20.73 | 2.62 |
| 65,537 | 100 | 4 | Go | 11.97 | 10.61–14.20 | 17.22 | 3.00 |
| 8,000,000 | 20 | 4 | Axon | 64.14 | 59.79–99.69 | 204.13 | 122.00 |
| 8,000,000 | 20 | 4 | Axon previous | 148.62 | 134.98–276.23 | 477.26 | 30.62 |
| 8,000,000 | 20 | 4 | Rust | 80.17 | 76.81–136.03 | 288.84 | 123.75 |
| 8,000,000 | 20 | 4 | Go | 91.06 | 84.07–151.85 | 309.08 | 124.50 |
| 1,000,000 | 1 | 4 | Axon | 5.87 | 4.69–7.24 | 12.21 | 15.00 |
| 1,000,000 | 1 | 4 | Axon previous | 5.92 | 5.21–7.25 | 12.12 | 3.88 |
| 1,000,000 | 1 | 4 | Rust | 5.28 | 4.71–7.09 | 9.33 | 16.88 |
| 1,000,000 | 1 | 4 | Go | 6.93 | 5.98–12.11 | 10.28 | 17.50 |

## Changes and limits

- General scalar array comprehensions now emit four-lane vectors for arithmetic and affine reads. The compiler intersects every source array’s valid interval, including speculative branch loads; prefix, suffix and vector tails remain scalar. Checked arithmetic uses masked overflow checks unless existing lexical/whole-program facts prove safety. Bounded remainders also lower inside vectors.
- Allocation-free vector bodies on Linux use raw clone(CLONE_VM | SIGCHLD) workers with separate aligned stacks and waitable process identities. Axon owns scheduling, stack allocation, joins and spawn-failure fallback. A small compiler-emitted ARM64/x86-64 stack-switch boundary makes the raw syscall; it calls no library. Workers never touch the allocator. Allocating bodies retain isolated fork workers. Stacks and contexts stay alive through the join.
- The runtime still creates workers per parallel region; this does not implement a persistent pool. macOS keeps fork workers and its platform-required libSystem loader command. Native performance was measured only on Linux ARM64; x86-64 correctness under emulation is separate evidence.
- RSS is GNU time’s maximum per-process resident high-water mark, not summed worker RSS, cgroup memory or virtual reservations. Shared-address worker mappings must not be counted repeatedly. CPU includes waited descendants.
- Linux Axon executables have no undefined symbols, ELF interpreter, DT_NEEDED entry, C runtime or shared-library dependency. Python/LLVM remain build tools. See retained nm/readelf output.

## Binary size

| Implementation | Bytes |
|---|---:|
| Axon | 25,520 |
| Axon previous | 23,512 |
| Rust | 559,984 |
| Go | 2,300,760 |

Raw commands, outputs, build reports, tool versions, checksums, samples and hashes: `/axon/bench/stencil/results/2026-10-24-095907`.
