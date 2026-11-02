# Representative compute regressions — 2026-10-25

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. 7 process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 1,200×1,200, 300 iterations. Its outer dimension exceeds the 1,024-element Axon parallel-dispatch threshold; the retained initial 600×600 run did not spawn Axon workers. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 98.49 | 97.97–99.40 | 97.90 |
| mandel | 1 | Rust | 262.11 | 259.32–264.13 | 260.47 |
| mandel | 1 | Go | 270.25 | 267.66–274.68 | 267.32 |
| stencil | 1 | Axon | 22.86 | 21.17–24.23 | 21.26 |
| stencil | 1 | Rust | 37.25 | 35.33–41.51 | 36.22 |
| stencil | 1 | Go | 43.00 | 39.60–57.20 | 40.79 |
| nbody | 1 | Axon | 5.64 | 5.49–6.85 | 5.17 |
| nbody | 1 | Rust | 7.77 | 7.44–8.87 | 7.00 |
| nbody | 1 | Go | 9.35 | 9.11–10.98 | 8.46 |
| mandel | 4 | Axon | 47.54 | 46.73–48.20 | 97.50 |
| mandel | 4 | Rust | 69.41 | 68.36–76.69 | 265.93 |
| mandel | 4 | Go | 72.24 | 71.26–73.03 | 273.11 |
| stencil | 4 | Axon | 11.30 | 10.97–11.59 | 26.71 |
| stencil | 4 | Rust | 12.90 | 12.41–14.67 | 39.32 |
| stencil | 4 | Go | 16.21 | 15.17–17.54 | 41.98 |
| nbody | 4 | Axon | 3.43 | 2.55–3.99 | 5.79 |
| nbody | 4 | Rust | 3.91 | 3.22–5.03 | 8.10 |
| nbody | 4 | Go | 5.84 | 5.24–7.06 | 8.81 |

Raw commands, outputs, tool versions, builds, checksums and timings: `/axon/bench/usability/results/2026-10-25-094336-compute`.
