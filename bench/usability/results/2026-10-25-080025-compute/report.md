# Representative compute regressions — 2026-10-24

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. 11 process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 1,200×1,200, 300 iterations. Its outer dimension exceeds the 1,024-element Axon parallel-dispatch threshold; the retained initial 600×600 run did not spawn Axon workers. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 101.78 | 97.55–108.29 | 101.13 |
| mandel | 1 | Rust | 265.25 | 262.71–303.57 | 263.18 |
| mandel | 1 | Go | 275.23 | 267.21–304.20 | 274.01 |
| stencil | 1 | Axon | 61.64 | 59.44–70.23 | 60.86 |
| stencil | 1 | Rust | 37.77 | 35.82–42.85 | 36.26 |
| stencil | 1 | Go | 42.21 | 39.98–54.33 | 39.88 |
| nbody | 1 | Axon | 5.85 | 5.55–7.00 | 5.24 |
| nbody | 1 | Rust | 7.71 | 7.28–8.94 | 6.99 |
| nbody | 1 | Go | 9.65 | 9.25–37.17 | 8.49 |
| mandel | 4 | Axon | 58.68 | 49.37–195.64 | 120.41 |
| mandel | 4 | Rust | 93.20 | 72.63–242.02 | 347.10 |
| mandel | 4 | Go | 97.87 | 78.87–132.59 | 353.08 |
| stencil | 4 | Axon | 59.78 | 46.08–145.72 | 130.94 |
| stencil | 4 | Rust | 18.75 | 14.63–35.29 | 49.46 |
| stencil | 4 | Go | 28.39 | 17.41–44.14 | 54.12 |
| nbody | 4 | Axon | 3.77 | 2.66–7.41 | 6.29 |
| nbody | 4 | Rust | 5.12 | 4.05–7.75 | 9.05 |
| nbody | 4 | Go | 7.51 | 6.08–12.11 | 10.22 |

Raw commands, outputs, tool versions, builds, checksums and timings: `/axon/bench/usability/results/2026-10-25-080025-compute`.
