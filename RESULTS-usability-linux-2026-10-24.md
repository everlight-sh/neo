# Axon usability workloads — Linux ARM64, 2026-10-24

Measured 2026-10-24T08:28:14.920298+00:00 on Linux-6.8.0-64-generic-aarch64-with-glibc2.39. Native aarch64, 8-vCPU/6-GiB Colima VM on Apple M1 Pro. Python/LLVM remain build tools; all measured Axon binaries have zero undefined imports.

The file CLI validates integer id/score and string name, filters score >= 100, stably sorts by score, writes UTF-8 JSON and fsyncs the output. All variants receive identical files and are verified against Python outside timing. The parsing workload constructs a different JSON document on each iteration, parses it, accesses fields and checksums values. Rust uses serde_json; Bun uses JSON.parse. Axon uses its initial source-slice JSON representation with defensive validation and owned value copies. This measures complete implementations, not isolated language arithmetic.

Process workloads use 5 measured runs after one warmup; variant order is shuffled each round. They run on CPU 0 with AXON_THREADS=1. Wall times include process startup, taskset and GNU time overhead, I/O and shutdown. CPU is child user+system time; maximum RSS is GNU time's peak for the command, not PSS or container working set. Short startup-heavy cases are sensitive to scheduler noise.

| Workload | Items | Implementation | Median wall ms | Run range ms | Median CPU ms | Max peak RSS MiB |
|---|---:|---|---:|---:|---:|---:|
| JSON file CLI | 100 | Axon | 5.68 | 4.90–6.47 | 3.28 | 1.38 |
| JSON file CLI | 100 | Rust | 5.40 | 4.84–17.52 | 3.19 | 1.88 |
| JSON file CLI | 100 | Bun | 27.95 | 25.83–38.52 | 24.46 | 39.50 |
| JSON file CLI | 1000 | Axon | 17.01 | 14.98–110.93 | 14.55 | 1.38 |
| JSON file CLI | 1000 | Rust | 45.05 | 9.87–63.33 | 18.30 | 3.25 |
| JSON file CLI | 1000 | Bun | 25.36 | 24.03–131.32 | 22.01 | 40.00 |
| Render + parse dynamic JSON + access fields | 1000 | Axon | 7.16 | 5.06–12.36 | 5.07 | 1.50 |
| Render + parse dynamic JSON + access fields | 1000 | Rust | 3.89 | 3.44–6.95 | 3.05 | 1.62 |
| Render + parse dynamic JSON + access fields | 1000 | Bun | 33.90 | 20.24–41.19 | 30.36 | 37.12 |
| Render + parse dynamic JSON + access fields | 10000 | Axon | 31.46 | 25.04–47.33 | 28.63 | 1.50 |
| Render + parse dynamic JSON + access fields | 10000 | Rust | 8.46 | 7.42–12.17 | 7.06 | 1.62 |
| Render + parse dynamic JSON + access fields | 10000 | Bun | 34.83 | 26.04–55.62 | 32.40 | 40.12 |
| Integer/UTF-8/vector/map operations | 10000 | Axon | 4.44 | 4.23–5.17 | 3.55 | 1.50 |

## Compiler workflow

Cold means --no-cache, including parsing, proofs, LLVM generation, compilation, linking and import audit. Warm means verified cached executable reuse, including dependency/compiler/options hashing and atomic publication. Three cold and five warm runs per application. This is a development compiler measurement, not runtime overhead.

| Project | Mode | Median ms | Min–max ms | Max compiler RSS MiB |
|---|---|---:|---:|---:|
| hello | cold | 2125.23 | 1911.69–2171.31 | 85.86 |
| hello | warm | 210.78 | 183.87–242.32 | 65.62 |
| json-cli | cold | 4054.27 | 3705.47–4707.94 | 96.90 |
| json-cli | warm | 290.34 | 276.91–339.40 | 65.62 |
| notes | cold | 4085.50 | 4062.80–4487.91 | 106.88 |
| notes | warm | 286.09 | 278.08–325.33 | 65.62 |
| webhook | cold | 5061.76 | 4820.99–6108.18 | 114.91 |
| webhook | warm | 306.58 | 290.24–315.00 | 65.62 |

## Stateful applications

Three fresh-journal runs per case. Notes uses eight concurrent Python clients, new HTTP connections per operation, 25 durable creates followed by 100 reads of the 25-note state. Writes include flock, journal append and fsync before acknowledgment. Servers run with the stated worker count; these application figures are end-to-end elapsed throughput and latency, not isolated server CPU or peak capacity. Test files use the container writable layer on the Linux VM disk; results are not production storage guarantees.

| Application/workload | Workers | Median operations/s | Run range operations/s | Median p50 ms | Median p99 ms |
|---|---:|---:|---:|---:|---:|
| notes: durable create | 1 | 970.8 | 948.6–1100.1 | 6.28 | 7.39 |
| notes: list 25 notes | 1 | 2801.1 | 2462.4–2895.6 | 2.32 | 7.00 |
| notes: durable create | 4 | 1078.0 | 1061.9–1132.8 | 6.14 | 7.11 |
| notes: list 25 notes | 4 | 2819.2 | 2431.4–2937.6 | 2.35 | 6.89 |
| webhook: durable enqueue to acknowledged delivery | 1 | 252.7 | 248.9–262.1 | not measured | not measured |

Webhook measures 20 persisted events through a local Python receiver to recorded successful delivery; it includes journal replay, claims, HTTP, fsyncs and completion records. There is one consumer plus the HTTP server. Receiver/client speed and the small batch affect the result.

Collections currently use concrete typed vectors and a linear string association map. This is an initial usable library, not a claim of generic containers or an optimized hash table. The dynamic JSON and collections workloads are deliberately broader than the earlier small SSR benchmark.

Checked signed arithmetic is now the safe-code default; explicit wrapping operations cover intentional wraparound. This is a documented semantic change. Correctness, fault recovery and dependency audits accompany performance; no universal language ranking follows.

Raw timings, stdout/stderr, time logs, inputs/outputs, build reports, tool versions, commands and hashes: `bench/usability/results/2026-10-24-082814`.
