# Representative compute regressions — 2026-10-24

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Five process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 600×600, 300 iterations. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative shorter cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 28.29 | 27.53–28.39 | 26.59 |
| mandel | 1 | Rust | 71.92 | 69.66–88.03 | 69.63 |
| mandel | 1 | Go | 74.42 | 73.26–105.45 | 72.87 |
| stencil | 1 | Axon | 37.70 | 37.43–38.72 | 36.75 |
| stencil | 1 | Rust | 37.65 | 36.45–38.39 | 36.36 |
| stencil | 1 | Go | 41.62 | 41.27–42.45 | 39.98 |
| nbody | 1 | Axon | 7.39 | 5.97–7.69 | 5.58 |
| nbody | 1 | Rust | 8.02 | 7.93–9.40 | 7.27 |
| nbody | 1 | Go | 12.54 | 11.54–18.19 | 9.62 |
| mandel | 4 | Axon | 29.50 | 28.42–33.00 | 27.56 |
| mandel | 4 | Rust | 23.06 | 22.45–26.74 | 81.26 |
| mandel | 4 | Go | 26.84 | 22.22–33.72 | 77.37 |
| stencil | 4 | Axon | 30.74 | 24.11–37.24 | 73.04 |
| stencil | 4 | Rust | 25.28 | 15.26–28.16 | 54.39 |
| stencil | 4 | Go | 25.47 | 22.71–30.15 | 49.26 |
| nbody | 4 | Axon | 5.04 | 4.87–7.00 | 8.93 |
| nbody | 4 | Rust | 6.09 | 5.46–8.86 | 9.45 |
| nbody | 4 | Go | 8.92 | 7.39–10.57 | 9.95 |

Raw commands, outputs, tool versions, builds, checksums and timings: `/axon/bench/usability/results/2026-10-24-082918-compute`.
