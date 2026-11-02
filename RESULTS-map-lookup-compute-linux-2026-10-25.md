# Representative compute regressions — 2026-10-25

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. 7 process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 1,200×1,200, 300 iterations. Its outer dimension exceeds the 1,024-element Axon parallel-dispatch threshold; the retained initial 600×600 run did not spawn Axon workers. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 98.50 | 97.18–99.68 | 97.77 |
| mandel | 1 | Rust | 262.24 | 257.35–266.57 | 260.05 |
| mandel | 1 | Go | 269.78 | 267.32–276.05 | 268.24 |
| stencil | 1 | Axon | 21.54 | 21.19–22.86 | 19.98 |
| stencil | 1 | Rust | 37.03 | 35.70–37.59 | 35.83 |
| stencil | 1 | Go | 39.75 | 39.51–40.89 | 38.49 |
| nbody | 1 | Axon | 5.69 | 5.64–7.27 | 5.21 |
| nbody | 1 | Rust | 7.50 | 7.40–9.01 | 6.87 |
| nbody | 1 | Go | 10.44 | 8.98–11.19 | 8.48 |
| mandel | 4 | Axon | 47.21 | 46.85–49.52 | 97.77 |
| mandel | 4 | Rust | 69.25 | 68.59–74.11 | 265.43 |
| mandel | 4 | Go | 72.20 | 70.86–73.88 | 271.62 |
| stencil | 4 | Axon | 11.77 | 11.15–13.22 | 28.09 |
| stencil | 4 | Rust | 14.03 | 12.57–14.55 | 40.07 |
| stencil | 4 | Go | 17.42 | 15.43–18.24 | 43.37 |
| nbody | 4 | Axon | 3.70 | 2.54–4.02 | 5.74 |
| nbody | 4 | Rust | 3.70 | 3.49–5.55 | 8.02 |
| nbody | 4 | Go | 6.08 | 5.19–6.63 | 9.02 |

Raw commands, outputs, tool versions, builds, checksums and timings: `/axon/bench/usability/results/2026-10-25-115806-compute`.
