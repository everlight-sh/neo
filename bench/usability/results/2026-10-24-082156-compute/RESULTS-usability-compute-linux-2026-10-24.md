# Representative compute regressions — 2026-10-24

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Five process runs after one warmup; implementation order shuffled every round. One worker uses CPU 0; four workers use CPUs 0–3. AXON_THREADS, RAYON_NUM_THREADS and GOMAXPROCS match the budget. Timing includes startup, allocation, computation and shutdown. All integer checksums match; N-body energy agrees within relative tolerance 1e-9.

Mandelbrot: 600×600, 300 iterations. Stencil: 1,000,000 i64 elements, 20 passes. N-body: 1,024 bodies, 3 steps. These are representative shorter cases, not reruns of the larger historical report sizes. Axon includes checked safe-code arithmetic and SIMD/parallel transformations. Rust uses the existing Rayon implementations; Go uses its existing goroutine implementations. Layout, scheduling and algorithms differ; these are complete-stack measurements.

| Workload | Workers | Implementation | Median wall ms | Range ms | Median CPU ms |
|---|---:|---|---:|---:|---:|
| mandel | 1 | Axon | 47.93 | 29.12–68.23 | 39.90 |
| mandel | 1 | Rust | 81.95 | 70.16–136.01 | 76.28 |
| mandel | 1 | Go | 96.94 | 88.42–183.01 | 92.40 |
| stencil | 1 | Axon | 43.84 | 39.57–56.95 | 40.02 |
| stencil | 1 | Rust | 42.92 | 39.22–60.60 | 37.53 |
| stencil | 1 | Go | 55.74 | 47.99–64.25 | 43.30 |
| nbody | 1 | Axon | 7.69 | 6.05–9.08 | 5.82 |
| nbody | 1 | Rust | 8.97 | 7.88–13.30 | 7.12 |
| nbody | 1 | Go | 10.94 | 10.57–12.32 | 8.82 |
| mandel | 4 | Axon | 28.52 | 27.83–29.81 | 27.81 |
| mandel | 4 | Rust | 24.27 | 20.87–27.75 | 76.17 |
| mandel | 4 | Go | 25.60 | 23.78–30.08 | 81.58 |
| stencil | 4 | Axon | 30.65 | 29.44–31.26 | 76.08 |
| stencil | 4 | Rust | 25.82 | 16.51–35.19 | 48.31 |
| stencil | 4 | Go | 28.10 | 22.95–29.33 | 52.56 |
| nbody | 4 | Axon | 4.34 | 3.63–5.36 | 8.13 |
| nbody | 4 | Rust | 5.89 | 5.21–8.41 | 10.55 |
| nbody | 4 | Go | 8.75 | 7.80–21.02 | 10.58 |

Raw commands, outputs, tool versions, builds, checksums and timings: `/axon/bench/usability/results/2026-10-24-082156-compute`.
