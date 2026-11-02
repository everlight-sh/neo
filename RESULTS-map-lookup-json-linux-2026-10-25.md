# JSON regression benchmark — 2026-10-25

Measured 2026-10-25T11:58:23.483652+00:00 on native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Each command is pinned to CPU 0; AXON_THREADS=1. No CPU emulation. 7 measured process runs after two warmups, with implementation order shuffled each round. GNU time/taskset startup, construction, parsing, field access, destruction and process shutdown are included.

This is the unchanged `examples/library_bench.ax` workload from the usability report: construct a different JSON object each iteration, fully validate/parse it, read integer id and decoded UTF-8 name, count array elements and checksum the result. Rust still uses the unmodified optimized serde_json::Value implementation; Bun still uses the unmodified JSON.parse implementation. The previous Axon executable is preserved and rerun in this session. Every output is checked. This measures the complete JSON workflow, not an isolated parser instruction or every JSON input shape.

| Documents | Implementation | Median wall ms | Min–max ms | Median CPU ms | Max process peak RSS MiB |
|---:|---|---:|---:|---:|---:|
| 10,000 | Axon | 4.72 | 4.58–4.97 | 3.85 | 1.38 |
| 10,000 | Axon previous | 4.76 | 4.34–5.00 | 3.76 | 1.38 |
| 10,000 | Rust | 6.56 | 6.20–8.06 | 5.51 | 1.62 |
| 10,000 | Bun | 21.19 | 20.65–22.70 | 19.25 | 41.12 |
| 100,000 | Axon | 30.01 | 29.55–31.99 | 29.08 | 1.38 |
| 100,000 | Axon previous | 29.54 | 28.82–33.38 | 28.12 | 1.50 |
| 100,000 | Rust | 44.45 | 43.42–45.70 | 42.89 | 1.62 |
| 100,000 | Bun | 59.16 | 56.32–62.08 | 57.31 | 73.50 |
| 1,000,000 | Axon | 277.18 | 272.85–278.74 | 275.82 | 1.38 |
| 1,000,000 | Axon previous | 267.45 | 265.33–269.38 | 266.35 | 1.38 |
| 1,000,000 | Rust | 401.66 | 396.56–404.34 | 400.30 | 1.62 |
| 1,000,000 | Bun | 363.44 | 356.73–385.25 | 361.29 | 108.75 |

## Scope of this rerun

The baseline executable was freshly built from the compiler/stdlib snapshot taken at the start of the map-lookup task. The JSON grammar and parser sources are unchanged. The current compiler adds short word-to-byte stores, while shared string helpers add packed formatting and checked short-integer parsing. The map layout also changes in this task.

At 1M documents, this complete workflow is 3.6% slower than that Axon baseline (267.45 → 277.18 ms), while remaining faster than the measured Rust and Bun cases. The raw measurements retain this regression.

Axon remains source-slice/index based, while Rust constructs serde_json::Value and Bun constructs JavaScript values. Their representations and memory policies differ. Native x86 performance, other parser libraries, arbitrary schemas, and universal language-performance rankings are not established here. Local VM measurements share the physical host; inspect the complete run ranges. Peak RSS is GNU time accounting, not Docker working set or PSS.

Raw commands, outputs, tool versions, binary/source hashes, dependency audits and timings: `/axon/bench/json/results/2026-10-25-115823`.
