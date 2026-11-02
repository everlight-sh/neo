# Representative compute regressions — 2026-10-24

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Five process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 1,200×1,200, 300 iterations. Its outer dimension exceeds the 1,024-element Axon parallel-dispatch threshold; the retained initial 600×600 run did not spawn Axon workers. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 110.72 | 100.73–122.04 | 109.69 |
| mandel | 1 | Rust | 278.14 | 263.86–303.19 | 275.46 |
| mandel | 1 | Go | 277.68 | 271.75–301.90 | 276.39 |
| stencil | 1 | Axon | 38.43 | 36.68–43.24 | 37.41 |
| stencil | 1 | Rust | 36.36 | 35.92–39.64 | 35.71 |
| stencil | 1 | Go | 40.89 | 39.86–48.11 | 39.30 |
| nbody | 1 | Axon | 7.04 | 6.02–7.47 | 5.47 |
| nbody | 1 | Rust | 7.92 | 7.75–9.19 | 7.12 |
| nbody | 1 | Go | 11.12 | 10.90–11.32 | 9.10 |
| mandel | 4 | Axon | 55.00 | 54.56–83.96 | 112.72 |
| mandel | 4 | Rust | 80.09 | 76.35–90.96 | 303.99 |
| mandel | 4 | Go | 83.52 | 77.34–86.72 | 312.36 |
| stencil | 4 | Axon | 26.69 | 23.78–43.25 | 73.08 |
| stencil | 4 | Rust | 20.84 | 15.09–26.99 | 54.56 |
| stencil | 4 | Go | 20.95 | 18.17–25.69 | 49.65 |
| nbody | 4 | Axon | 4.31 | 3.48–7.13 | 8.66 |
| nbody | 4 | Rust | 6.12 | 4.78–6.34 | 9.77 |
| nbody | 4 | Go | 6.73 | 5.84–8.51 | 10.24 |

Raw commands, outputs, tool versions, builds, checksums and timings: `bench/usability/results/2026-10-24-083616-compute`.
