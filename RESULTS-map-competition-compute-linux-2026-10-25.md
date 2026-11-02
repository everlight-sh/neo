# Representative compute regressions — 2026-10-25

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. 7 process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 1,200×1,200, 300 iterations. Its outer dimension exceeds the 1,024-element Axon parallel-dispatch threshold; the retained initial 600×600 run did not spawn Axon workers. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 98.24 | 97.39–100.91 | 97.53 |
| mandel | 1 | Rust | 260.58 | 257.30–280.15 | 259.77 |
| mandel | 1 | Go | 270.78 | 266.63–274.21 | 268.34 |
| stencil | 1 | Axon | 21.97 | 21.54–24.06 | 20.53 |
| stencil | 1 | Rust | 36.10 | 35.53–38.51 | 35.35 |
| stencil | 1 | Go | 40.55 | 39.85–41.96 | 38.57 |
| nbody | 1 | Axon | 6.07 | 5.64–7.32 | 5.44 |
| nbody | 1 | Rust | 8.03 | 7.54–9.05 | 7.05 |
| nbody | 1 | Go | 10.55 | 9.58–11.16 | 8.77 |
| mandel | 4 | Axon | 47.40 | 46.60–50.10 | 97.78 |
| mandel | 4 | Rust | 69.74 | 68.45–74.46 | 264.82 |
| mandel | 4 | Go | 72.17 | 70.77–73.10 | 273.13 |
| stencil | 4 | Axon | 11.32 | 10.11–11.83 | 27.63 |
| stencil | 4 | Rust | 14.18 | 12.13–15.42 | 40.78 |
| stencil | 4 | Go | 16.95 | 15.77–18.09 | 42.46 |
| nbody | 4 | Axon | 3.58 | 2.60–3.80 | 5.60 |
| nbody | 4 | Rust | 4.48 | 3.39–5.08 | 8.01 |
| nbody | 4 | Go | 5.72 | 4.94–6.53 | 9.00 |

Raw commands, outputs, tool versions, builds, checksums and timings: `/axon/bench/usability/results/2026-10-25-103858-compute`.
