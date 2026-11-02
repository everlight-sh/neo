# Representative compute regressions — 2026-10-24

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. 7 process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 1,200×1,200, 300 iterations. Its outer dimension exceeds the 1,024-element Axon parallel-dispatch threshold; the retained initial 600×600 run did not spawn Axon workers. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 98.95 | 97.17–100.18 | 98.29 |
| mandel | 1 | Rust | 261.75 | 256.93–266.06 | 260.14 |
| mandel | 1 | Go | 273.14 | 267.75–277.55 | 271.79 |
| stencil | 1 | Axon | 20.71 | 20.29–21.51 | 19.96 |
| stencil | 1 | Rust | 35.23 | 34.35–38.68 | 34.49 |
| stencil | 1 | Go | 39.81 | 38.40–42.76 | 38.44 |
| nbody | 1 | Axon | 5.78 | 5.58–6.99 | 5.33 |
| nbody | 1 | Rust | 9.02 | 7.55–9.63 | 7.21 |
| nbody | 1 | Go | 10.80 | 9.65–11.69 | 8.78 |
| mandel | 4 | Axon | 47.36 | 46.79–48.37 | 98.66 |
| mandel | 4 | Rust | 69.69 | 68.16–71.56 | 265.36 |
| mandel | 4 | Go | 72.34 | 70.87–75.13 | 274.14 |
| stencil | 4 | Axon | 10.61 | 10.01–11.68 | 27.71 |
| stencil | 4 | Rust | 13.31 | 11.96–15.15 | 40.80 |
| stencil | 4 | Go | 16.19 | 15.40–17.44 | 41.50 |
| nbody | 4 | Axon | 4.23 | 3.16–4.90 | 6.97 |
| nbody | 4 | Rust | 3.70 | 3.09–5.44 | 8.14 |
| nbody | 4 | Go | 5.31 | 4.92–8.16 | 9.04 |

Raw commands, outputs, tool versions, builds, checksums and timings: `/axon/bench/usability/results/2026-10-24-175221-compute`.
