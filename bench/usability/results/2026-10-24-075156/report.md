# Axon usability workloads — Linux ARM64, 2026-10-24

Measured 2026-10-24T07:51:56.144369+00:00 on Linux-6.8.0-64-generic-aarch64-with-glibc2.39. Native aarch64, 8-vCPU/6-GiB Colima VM on Apple M1 Pro. Python/LLVM remain build tools; all measured Axon binaries have zero undefined imports.

The file CLI validates integer id/score and string name, filters score >= 100, stably sorts by score, writes UTF-8 JSON and fsyncs the output. All variants receive identical files and are verified against Python outside timing. The parsing workload constructs a different JSON document on each iteration, parses it, accesses fields and checksums values. Rust uses serde_json; Bun uses JSON.parse. Axon uses its initial source-slice JSON representation with defensive validation and owned value copies. This measures complete implementations, not isolated language arithmetic.

Process workloads use 5 measured runs after one warmup; variant order is shuffled each round. They run on CPU 0 with AXON_THREADS=1. Wall times include process startup, taskset and GNU time overhead, I/O and shutdown. CPU is child user+system time; maximum RSS is GNU time's peak for the command, not PSS or container working set. Short startup-heavy cases are sensitive to scheduler noise.

| Workload | Items | Implementation | Median wall ms | Run range ms | Median CPU ms | Max peak RSS MiB |
|---|---:|---|---:|---:|---:|---:|
| JSON file CLI | 100 | Axon | 3.12 | 2.89–4.07 | 1.92 | 1.38 |
| JSON file CLI | 100 | Rust | 3.79 | 3.54–4.45 | 2.33 | 1.88 |
| JSON file CLI | 100 | Bun | 19.92 | 18.67–25.39 | 17.31 | 39.38 |
| JSON file CLI | 1000 | Axon | 14.47 | 14.07–18.97 | 12.93 | 1.38 |
| JSON file CLI | 1000 | Rust | 9.39 | 8.94–14.55 | 7.69 | 3.25 |
| JSON file CLI | 1000 | Bun | 22.68 | 21.20–30.28 | 19.92 | 40.25 |
| Render + parse dynamic JSON + access fields | 1000 | Axon | 3.91 | 3.69–4.22 | 3.42 | 1.50 |
| Render + parse dynamic JSON + access fields | 1000 | Rust | 2.74 | 2.28–3.19 | 2.00 | 1.62 |
| Render + parse dynamic JSON + access fields | 1000 | Bun | 18.53 | 17.51–19.55 | 17.13 | 37.25 |
| Render + parse dynamic JSON + access fields | 10000 | Axon | 28.91 | 23.98–39.18 | 28.31 | 1.50 |
| Render + parse dynamic JSON + access fields | 10000 | Rust | 7.60 | 7.21–10.85 | 6.86 | 1.62 |
| Render + parse dynamic JSON + access fields | 10000 | Bun | 38.31 | 24.94–40.32 | 33.57 | 39.75 |
| Integer/UTF-8/vector/map operations | 10000 | Axon | 3.19 | 2.96–3.77 | 2.54 | 1.38 |

## Compiler workflow

Cold means --no-cache, including parsing, proofs, LLVM generation, compilation, linking and import audit. Warm means verified cached executable reuse, including dependency/compiler/options hashing and atomic publication. Three cold and five warm runs per application. This is a development compiler measurement, not runtime overhead.

| Project | Mode | Median ms | Min–max ms | Max compiler RSS MiB |
|---|---|---:|---:|---:|
| hello | cold | 1514.19 | 1480.28–1662.02 | 85.84 |
| hello | warm | 169.79 | 167.24–184.10 | 65.62 |
| json-cli | cold | 3228.35 | 3221.31–3298.35 | 98.32 |
| json-cli | warm | 256.56 | 228.14–273.64 | 65.62 |
| notes | cold | 4577.30 | 4526.75–5091.57 | 108.27 |
| notes | warm | 276.50 | 258.74–382.36 | 65.62 |
| webhook | cold | 4769.01 | 4735.56–4978.22 | 114.93 |
| webhook | warm | 272.72 | 264.27–278.22 | 65.62 |

## Stateful applications

Three fresh-journal runs per case. Notes uses eight concurrent Python clients, new HTTP connections per operation, 25 durable creates followed by 100 reads of the 25-note state. Writes include flock, journal append and fsync before acknowledgment. Servers run with the stated worker count; these application figures are end-to-end elapsed throughput and latency, not isolated server CPU or peak capacity. Test files use the container writable layer on the Linux VM disk; results are not production storage guarantees.

| Application/workload | Workers | Median operations/s | Run range operations/s | Median p50 ms | Median p99 ms |
|---|---:|---:|---:|---:|---:|
| notes: durable create | 1 | 1313.7 | 1172.3–1699.4 | 4.24 | 5.11 |
| notes: list 25 notes | 1 | 3580.5 | 3300.4–3861.1 | 1.81 | 5.43 |
| notes: durable create | 4 | 1617.8 | 1358.2–1818.5 | 4.04 | 4.58 |
| notes: list 25 notes | 4 | 3340.5 | 3247.4–3586.2 | 1.88 | 5.60 |
| webhook: durable enqueue to acknowledged delivery | 1 | 262.1 | 200.8–339.6 | not measured | not measured |

Webhook measures 20 persisted events through a local Python receiver to recorded successful delivery; it includes journal replay, claims, HTTP, fsyncs and completion records. There is one consumer plus the HTTP server. Receiver/client speed and the small batch affect the result.

Collections currently use concrete typed vectors and a linear string association map. This is an initial usable library, not a claim of generic containers or an optimized hash table. The dynamic JSON and collections workloads are deliberately broader than the earlier small SSR benchmark.

Checked signed arithmetic is now the safe-code default; explicit wrapping operations cover intentional wraparound. This is a documented semantic change. Correctness, fault recovery and dependency audits accompany performance; no universal language ranking follows.

Raw timings, stdout/stderr, time logs, inputs/outputs, build reports, tool versions, commands and hashes: `/axon/bench/usability/results/2026-10-24-075156`.
