# Axon usability workloads — Linux ARM64, 2026-10-24

Measured 2026-10-24T09:28:42.332005+00:00 on Linux-6.8.0-64-generic-aarch64-with-glibc2.39. Native aarch64, 8-vCPU/6-GiB Colima VM on Apple M1 Pro. Python/LLVM remain build tools; all measured Axon binaries have zero undefined imports.

The file CLI validates integer id/score and string name, filters score >= 100, stably sorts by score, writes UTF-8 JSON and fsyncs the output. All variants receive identical files and are verified against Python outside timing. The parsing workload constructs a different JSON document on each iteration, parses it, accesses fields and checksums values. Rust uses serde_json; Bun uses JSON.parse. Axon uses validated source slices with cached member indexes and owned value copies. This measures complete implementations, not isolated language arithmetic.

Process workloads use 5 measured runs after one warmup; variant order is shuffled each round. They run on CPU 0 with AXON_THREADS=1. Wall times include process startup, taskset and GNU time overhead, I/O and shutdown. CPU is child user+system time; maximum RSS is GNU time's peak for the command, not PSS or container working set. Short startup-heavy cases are sensitive to scheduler noise.

| Workload | Items | Implementation | Median wall ms | Run range ms | Median CPU ms | Max peak RSS MiB |
|---|---:|---|---:|---:|---:|---:|
| JSON file CLI | 100 | Axon | 2.48 | 1.86–3.67 | 1.37 | 1.38 |
| JSON file CLI | 100 | Rust | 3.45 | 3.14–3.88 | 2.25 | 1.88 |
| JSON file CLI | 100 | Bun | 18.94 | 17.50–19.26 | 16.42 | 40.38 |
| JSON file CLI | 1000 | Axon | 4.60 | 4.34–4.96 | 3.35 | 1.38 |
| JSON file CLI | 1000 | Rust | 8.39 | 8.24–8.66 | 6.94 | 3.25 |
| JSON file CLI | 1000 | Bun | 18.57 | 18.13–19.24 | 16.38 | 41.00 |
| Render + parse dynamic JSON + access fields | 1000 | Axon | 1.69 | 1.64–2.18 | 1.33 | 1.38 |
| Render + parse dynamic JSON + access fields | 1000 | Rust | 2.38 | 2.16–2.55 | 1.88 | 1.62 |
| Render + parse dynamic JSON + access fields | 1000 | Bun | 15.94 | 15.80–18.94 | 14.63 | 38.25 |
| Render + parse dynamic JSON + access fields | 10000 | Axon | 4.66 | 4.51–4.96 | 4.15 | 1.38 |
| Render + parse dynamic JSON + access fields | 10000 | Rust | 6.30 | 5.88–9.20 | 5.52 | 1.62 |
| Render + parse dynamic JSON + access fields | 10000 | Bun | 20.78 | 20.02–35.27 | 19.32 | 41.12 |
| Integer/UTF-8/vector/map operations | 10000 | Axon | 2.30 | 2.20–2.60 | 1.93 | 1.38 |

## Compiler workflow

Cold means --no-cache, including parsing, proofs, LLVM generation, compilation, linking and import audit. Warm means verified cached executable reuse, including dependency/compiler/options hashing and atomic publication. Three cold and five warm runs per application. This is a development compiler measurement, not runtime overhead.

| Project | Mode | Median ms | Min–max ms | Max compiler RSS MiB |
|---|---|---:|---:|---:|
| hello | cold | 1956.80 | 1748.31–2101.06 | 85.98 |
| hello | warm | 203.60 | 177.30–272.00 | 65.50 |
| json-cli | cold | 3882.85 | 3858.12–6093.66 | 102.00 |
| json-cli | warm | 241.14 | 236.03–254.79 | 65.50 |
| notes | cold | 4414.50 | 4189.09–4463.95 | 110.62 |
| notes | warm | 279.39 | 268.90–324.56 | 65.50 |
| webhook | cold | 7429.66 | 6125.86–16824.69 | 118.11 |
| webhook | warm | 285.16 | 274.42–350.71 | 65.50 |

## Stateful applications

Three fresh-journal runs per case. Notes uses eight concurrent Python clients, new HTTP connections per operation, 25 durable creates followed by 100 reads of the 25-note state. Writes include flock, journal append and fsync before acknowledgment. Servers run with the stated worker count; these application figures are end-to-end elapsed throughput and latency, not isolated server CPU or peak capacity. Test files use the container writable layer on the Linux VM disk; results are not production storage guarantees.

| Application/workload | Workers | Median operations/s | Run range operations/s | Median p50 ms | Median p99 ms |
|---|---:|---:|---:|---:|---:|
| notes: durable create | 1 | 1526.6 | 1174.2–1663.5 | 4.32 | 5.24 |
| notes: list 25 notes | 1 | 3684.3 | 3676.4–3762.7 | 1.82 | 4.99 |
| notes: durable create | 4 | 1463.0 | 1262.8–1631.6 | 4.49 | 5.60 |
| notes: list 25 notes | 4 | 3344.0 | 2829.2–3425.4 | 1.99 | 6.06 |
| webhook: durable enqueue to acknowledged delivery | 1 | 312.8 | 263.9–320.9 | not measured | not measured |

Webhook measures 20 persisted events through a local Python receiver to recorded successful delivery; it includes journal replay, claims, HTTP, fsyncs and completion records. There is one consumer plus the HTTP server. Receiver/client speed and the small batch affect the result.

Collections currently use concrete typed vectors and a linear string association map. This is an initial usable library, not a claim of generic containers or an optimized hash table. The dynamic JSON and collections workloads are deliberately broader than the earlier small SSR benchmark.

Checked signed arithmetic is now the safe-code default; explicit wrapping operations cover intentional wraparound. This is a documented semantic change. Correctness, fault recovery and dependency audits accompany performance; no universal language ranking follows.

Raw timings, stdout/stderr, time logs, inputs/outputs, build reports, tool versions, commands and hashes: `bench/usability/results/2026-10-24-092842`.
