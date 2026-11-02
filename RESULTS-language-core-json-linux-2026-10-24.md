# Dynamic JSON workload after optimization — 2026-10-24

Measured 2026-10-24T18:12:35.383755+00:00 on native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Each command is pinned to CPU 0; AXON_THREADS=1. No CPU emulation. 7 measured process runs after two warmups, with implementation order shuffled each round. GNU time/taskset startup, construction, parsing, field access, destruction and process shutdown are included.

This is the unchanged `examples/library_bench.ax` workload from the usability report: construct a different JSON object each iteration, fully validate/parse it, read integer id and decoded UTF-8 name, count array elements and checksum the result. Rust still uses the unmodified optimized serde_json::Value implementation; Bun still uses the unmodified JSON.parse implementation. The previous Axon executable is preserved and rerun in this session. Every output is checked. This measures the complete JSON workflow, not an isolated parser instruction or every JSON input shape.

| Documents | Implementation | Median wall ms | Min–max ms | Median CPU ms | Max process peak RSS MiB |
|---:|---|---:|---:|---:|---:|
| 10,000 | Axon | 5.29 | 5.14–5.73 | 4.33 | 1.38 |
| 10,000 | Axon previous | 5.06 | 4.78–5.87 | 4.24 | 1.38 |
| 10,000 | Rust | 6.89 | 6.73–8.24 | 5.76 | 1.62 |
| 10,000 | Bun | 22.74 | 21.69–26.64 | 20.54 | 41.12 |
| 100,000 | Axon | 32.62 | 31.79–32.98 | 31.46 | 1.38 |
| 100,000 | Axon previous | 32.65 | 32.16–33.14 | 31.64 | 1.38 |
| 100,000 | Rust | 43.33 | 42.11–48.16 | 41.95 | 1.62 |
| 100,000 | Bun | 57.63 | 55.28–59.82 | 55.43 | 73.50 |
| 1,000,000 | Axon | 305.15 | 302.20–307.35 | 304.13 | 1.38 |
| 1,000,000 | Axon previous | 304.84 | 299.98–309.15 | 303.78 | 1.38 |
| 1,000,000 | Rust | 400.80 | 390.19–405.85 | 399.44 | 1.62 |
| 1,000,000 | Bun | 359.53 | 356.08–382.62 | 357.45 | 108.75 |

## What changed

- UTF-8 validation is integrated with string scanning; strict validation, Unicode scalar rules and the depth limit remain enforced.
- Object validation builds member offsets in the same pass. Lookups use that index, and reverse search preserves last-duplicate-key semantics. The index grows geometrically rather than with the byte size of string payloads.
- `sealed type` restricts construction/updates to the declaring module. Parsed JSON values retain their validation invariant; callers can read fields and copy bytes, but cannot forge raw/kind/index combinations.
- Pure internal record calls borrow live arguments. Escaping children acquire ownership before return; temporaries remain alive through calls. Empty arrays are canonical non-owning values, and static string fields stay immutable.
- Bounded nonrecursive functions called with literal strings receive an inlining hint. Allocator headers cache their size-class index instead of recomputing it on every release.

Axon remains source-slice/index based, while Rust constructs serde_json::Value and Bun constructs JavaScript values. Their representations and memory policies differ. Native x86 performance, other parser libraries, arbitrary schemas, and universal language-performance rankings are not established here. Local VM measurements share the physical host; inspect the complete run ranges. Peak RSS is GNU time accounting, not Docker working set or PSS.

Raw commands, outputs, tool versions, binary/source hashes, dependency audits and timings: `/axon/bench/json/results/2026-10-24-181235`.
