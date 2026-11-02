# Representative compute regressions — 2026-10-24

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. 9 process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 1,200×1,200, 300 iterations. Its outer dimension exceeds the 1,024-element Axon parallel-dispatch threshold; the retained initial 600×600 run did not spawn Axon workers. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 107.00 | 102.32–132.56 | 105.84 |
| mandel | 1 | Rust | 290.07 | 269.36–310.75 | 287.95 |
| mandel | 1 | Go | 304.96 | 281.11–340.86 | 300.22 |
| stencil | 1 | Axon | 26.44 | 22.57–42.43 | 24.68 |
| stencil | 1 | Rust | 51.76 | 43.24–114.59 | 50.34 |
| stencil | 1 | Go | 63.09 | 46.28–114.19 | 58.98 |
| nbody | 1 | Axon | 7.50 | 6.03–10.70 | 6.06 |
| nbody | 1 | Rust | 9.55 | 8.79–10.72 | 7.78 |
| nbody | 1 | Go | 12.56 | 10.36–14.44 | 10.12 |
| mandel | 4 | Axon | 52.33 | 50.62–75.64 | 107.40 |
| mandel | 4 | Rust | 76.97 | 73.83–94.13 | 288.47 |
| mandel | 4 | Go | 80.24 | 78.37–107.48 | 298.85 |
| stencil | 4 | Axon | 14.33 | 12.31–20.16 | 33.13 |
| stencil | 4 | Rust | 16.04 | 14.51–22.94 | 48.51 |
| stencil | 4 | Go | 20.28 | 17.33–28.91 | 48.12 |
| nbody | 4 | Axon | 5.07 | 4.01–6.07 | 8.49 |
| nbody | 4 | Rust | 5.28 | 4.03–6.02 | 9.23 |
| nbody | 4 | Go | 7.42 | 6.36–8.54 | 10.34 |

Raw commands, outputs, tool versions, builds, checksums and timings: `/axon/bench/usability/results/2026-10-24-100851-compute`.
