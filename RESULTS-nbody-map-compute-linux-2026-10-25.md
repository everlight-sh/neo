# Representative compute regressions — 2026-10-25

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. 11 process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 1,200×1,200, 300 iterations. Its outer dimension exceeds the 1,024-element Axon parallel-dispatch threshold; the retained initial 600×600 run did not spawn Axon workers. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 100.23 | 98.04–178.39 | 99.65 |
| mandel | 1 | Rust | 266.50 | 262.49–309.13 | 265.72 |
| mandel | 1 | Go | 274.30 | 271.98–486.70 | 272.04 |
| stencil | 1 | Axon | 22.10 | 21.11–23.23 | 20.25 |
| stencil | 1 | Rust | 37.13 | 35.35–39.53 | 35.56 |
| stencil | 1 | Go | 41.26 | 39.28–43.63 | 39.73 |
| nbody | 1 | Axon | 6.76 | 5.99–10.85 | 5.44 |
| nbody | 1 | Rust | 8.27 | 7.57–12.41 | 7.19 |
| nbody | 1 | Go | 11.02 | 9.07–19.43 | 8.91 |
| mandel | 4 | Axon | 50.33 | 49.17–85.16 | 103.48 |
| mandel | 4 | Rust | 74.49 | 71.11–94.48 | 280.58 |
| mandel | 4 | Go | 77.67 | 74.23–129.81 | 291.56 |
| stencil | 4 | Axon | 12.10 | 10.53–19.04 | 29.28 |
| stencil | 4 | Rust | 14.71 | 12.52–25.58 | 42.20 |
| stencil | 4 | Go | 17.20 | 15.81–21.16 | 43.66 |
| nbody | 4 | Axon | 3.73 | 2.50–4.66 | 5.74 |
| nbody | 4 | Rust | 4.49 | 3.49–5.50 | 8.01 |
| nbody | 4 | Go | 6.11 | 4.86–7.45 | 9.04 |

Raw commands, outputs, tool versions, builds, checksums and timings: `/axon/bench/usability/results/2026-10-25-081540-compute`.
