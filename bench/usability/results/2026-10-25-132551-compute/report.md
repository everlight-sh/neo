# Representative compute regressions — 2026-10-24

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. 7 process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 1,200×1,200, 300 iterations. Its outer dimension exceeds the 1,024-element Axon parallel-dispatch threshold; the retained initial 600×600 run did not spawn Axon workers. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 99.40 | 98.64–100.39 | 98.78 |
| mandel | 1 | Rust | 269.95 | 263.18–274.47 | 267.86 |
| mandel | 1 | Go | 274.89 | 271.01–283.63 | 272.46 |
| stencil | 1 | Axon | 22.15 | 21.51–23.20 | 20.44 |
| stencil | 1 | Rust | 36.99 | 35.72–38.07 | 35.17 |
| stencil | 1 | Go | 40.55 | 39.14–41.99 | 38.55 |
| nbody | 1 | Axon | 5.91 | 5.64–6.11 | 5.36 |
| nbody | 1 | Rust | 8.60 | 7.64–13.00 | 7.07 |
| nbody | 1 | Go | 10.13 | 9.29–11.12 | 8.44 |
| mandel | 4 | Axon | 55.20 | 49.05–79.00 | 110.11 |
| mandel | 4 | Rust | 81.51 | 73.46–85.32 | 302.80 |
| mandel | 4 | Go | 85.11 | 78.08–159.44 | 318.66 |
| stencil | 4 | Axon | 20.26 | 15.71–27.35 | 42.43 |
| stencil | 4 | Rust | 18.23 | 15.30–24.43 | 51.78 |
| stencil | 4 | Go | 27.49 | 19.94–41.34 | 55.94 |
| nbody | 4 | Axon | 4.25 | 2.53–5.43 | 6.50 |
| nbody | 4 | Rust | 6.15 | 3.58–6.48 | 9.92 |
| nbody | 4 | Go | 6.46 | 5.57–8.13 | 9.52 |

Raw commands, outputs, tool versions, builds, checksums and timings: `/axon/bench/usability/results/2026-10-25-132551-compute`.
