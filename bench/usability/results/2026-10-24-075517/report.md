# Axon usability workloads — Linux ARM64, 2026-10-24

Measured 2026-10-24T07:55:17.678347+00:00 on Linux-6.8.0-64-generic-aarch64-with-glibc2.39. Native aarch64, 8-vCPU/6-GiB Colima VM on Apple M1 Pro. Python/LLVM remain build tools; all measured Axon binaries have zero undefined imports.

The file CLI validates integer id/score and string name, filters score >= 100, stably sorts by score, writes UTF-8 JSON and fsyncs the output. All variants receive identical files and are verified against Python outside timing. The parsing workload constructs a different JSON document on each iteration, parses it, accesses fields and checksums values. Rust uses serde_json; Bun uses JSON.parse. Axon uses its initial source-slice JSON representation with defensive validation and owned value copies. This measures complete implementations, not isolated language arithmetic.

Process workloads use 5 measured runs after one warmup; variant order is shuffled each round. They run on CPU 0 with AXON_THREADS=1. Wall times include process startup, taskset and GNU time overhead, I/O and shutdown. CPU is child user+system time; maximum RSS is GNU time's peak for the command, not PSS or container working set. Short startup-heavy cases are sensitive to scheduler noise.

| Workload | Items | Implementation | Median wall ms | Run range ms | Median CPU ms | Max peak RSS MiB |
|---|---:|---|---:|---:|---:|---:|
| JSON file CLI | 100 | Axon | 2.99 | 2.79–3.48 | 1.90 | 1.38 |
| JSON file CLI | 100 | Rust | 3.50 | 3.33–3.97 | 2.23 | 1.88 |
| JSON file CLI | 100 | Bun | 21.37 | 18.90–23.94 | 18.88 | 39.38 |
| JSON file CLI | 1000 | Axon | 14.04 | 13.48–14.50 | 12.53 | 1.38 |
| JSON file CLI | 1000 | Rust | 8.43 | 8.28–8.68 | 6.97 | 3.25 |
| JSON file CLI | 1000 | Bun | 19.44 | 19.03–22.63 | 17.23 | 40.00 |
| Render + parse dynamic JSON + access fields | 1000 | Axon | 3.73 | 3.40–4.80 | 3.32 | 1.38 |
| Render + parse dynamic JSON + access fields | 1000 | Rust | 2.30 | 2.13–2.79 | 1.84 | 1.62 |
| Render + parse dynamic JSON + access fields | 1000 | Bun | 17.71 | 16.93–19.30 | 16.34 | 37.25 |
| Render + parse dynamic JSON + access fields | 10000 | Axon | 22.98 | 22.43–23.43 | 22.51 | 1.50 |
| Render + parse dynamic JSON + access fields | 10000 | Rust | 6.12 | 6.04–6.47 | 5.60 | 1.62 |
| Render + parse dynamic JSON + access fields | 10000 | Bun | 21.66 | 21.32–22.92 | 20.50 | 40.12 |
| Integer/UTF-8/vector/map operations | 10000 | Axon | 2.66 | 2.56–2.94 | 2.29 | 1.38 |

## Compiler workflow

Cold means --no-cache, including parsing, proofs, LLVM generation, compilation, linking and import audit. Warm means verified cached executable reuse, including dependency/compiler/options hashing and atomic publication. Three cold and five warm runs per application. This is a development compiler measurement, not runtime overhead.

| Project | Mode | Median ms | Min–max ms | Max compiler RSS MiB |
|---|---|---:|---:|---:|
| hello | cold | 1569.37 | 1531.97–1923.16 | 85.83 |
| hello | warm | 240.66 | 185.05–391.05 | 65.62 |
| json-cli | cold | 3836.24 | 3482.25–6656.79 | 96.95 |
| json-cli | warm | 239.18 | 234.08–298.24 | 65.62 |
| notes | cold | 4862.18 | 4316.14–5312.41 | 108.35 |
| notes | warm | 263.99 | 261.94–272.45 | 65.62 |
| webhook | cold | 4987.48 | 4821.68–5464.49 | 114.93 |
| webhook | warm | 268.08 | 256.56–275.56 | 65.62 |

## Stateful applications

Three fresh-journal runs per case. Notes uses eight concurrent Python clients, new HTTP connections per operation, 25 durable creates followed by 100 reads of the 25-note state. Writes include flock, journal append and fsync before acknowledgment. Servers run with the stated worker count; these application figures are end-to-end elapsed throughput and latency, not isolated server CPU or peak capacity. Test files use the container writable layer on the Linux VM disk; results are not production storage guarantees.

| Application/workload | Workers | Median operations/s | Run range operations/s | Median p50 ms | Median p99 ms |
|---|---:|---:|---:|---:|---:|
| notes: durable create | 1 | 1626.1 | 1450.8–1756.8 | 3.91 | 4.19 |
| notes: list 25 notes | 1 | 3715.5 | 3706.1–3888.3 | 1.81 | 4.48 |
| notes: durable create | 4 | 1615.7 | 1599.0–1660.7 | 3.97 | 4.58 |
| notes: list 25 notes | 4 | 3428.8 | 3392.5–3479.4 | 1.87 | 5.12 |
| webhook: durable enqueue to acknowledged delivery | 1 | 348.7 | 347.6–355.4 | not measured | not measured |

Webhook measures 20 persisted events through a local Python receiver to recorded successful delivery; it includes journal replay, claims, HTTP, fsyncs and completion records. There is one consumer plus the HTTP server. Receiver/client speed and the small batch affect the result.

Collections currently use concrete typed vectors and a linear string association map. This is an initial usable library, not a claim of generic containers or an optimized hash table. The dynamic JSON and collections workloads are deliberately broader than the earlier small SSR benchmark.

Checked signed arithmetic is now the safe-code default; explicit wrapping operations cover intentional wraparound. This is a documented semantic change. Correctness, fault recovery and dependency audits accompany performance; no universal language ranking follows.

Raw timings, stdout/stderr, time logs, inputs/outputs, build reports, tool versions, commands and hashes: `/axon/bench/usability/results/2026-10-24-075517`.
