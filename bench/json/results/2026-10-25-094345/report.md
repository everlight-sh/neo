# Dynamic JSON workload after optimization — 2026-10-24

Measured 2026-10-25T09:43:45.618657+00:00 on native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Each command is pinned to CPU 0; AXON_THREADS=1. No CPU emulation. 7 measured process runs after two warmups, with implementation order shuffled each round. GNU time/taskset startup, construction, parsing, field access, destruction and process shutdown are included.

This is the unchanged `examples/library_bench.ax` workload from the usability report: construct a different JSON object each iteration, fully validate/parse it, read integer id and decoded UTF-8 name, count array elements and checksum the result. Rust still uses the unmodified optimized serde_json::Value implementation; Bun still uses the unmodified JSON.parse implementation. The previous Axon executable is preserved and rerun in this session. Every output is checked. This measures the complete JSON workflow, not an isolated parser instruction or every JSON input shape.

| Documents | Implementation | Median wall ms | Min–max ms | Median CPU ms | Max process peak RSS MiB |
|---:|---|---:|---:|---:|---:|
| 10,000 | Axon | 4.91 | 4.52–5.17 | 4.10 | 1.38 |
| 10,000 | Axon previous | 5.02 | 4.88–5.20 | 4.12 | 1.38 |
| 10,000 | Rust | 6.80 | 6.30–9.32 | 5.68 | 1.62 |
| 10,000 | Bun | 22.28 | 20.44–22.78 | 20.08 | 41.12 |
| 100,000 | Axon | 32.82 | 32.28–33.44 | 31.78 | 1.38 |
| 100,000 | Axon previous | 33.42 | 32.65–42.10 | 32.37 | 1.38 |
| 100,000 | Rust | 43.53 | 42.66–44.12 | 42.35 | 1.62 |
| 100,000 | Bun | 57.22 | 55.75–58.23 | 55.21 | 73.50 |
| 1,000,000 | Axon | 304.44 | 302.25–307.03 | 303.14 | 1.38 |
| 1,000,000 | Axon previous | 308.92 | 304.89–362.20 | 307.55 | 1.38 |
| 1,000,000 | Rust | 405.02 | 400.28–412.23 | 403.67 | 1.62 |
| 1,000,000 | Bun | 362.64 | 361.18–377.41 | 360.48 | 108.75 |

## What changed

- UTF-8 validation is integrated with string scanning; strict validation, Unicode scalar rules and the depth limit remain enforced.
- Object validation builds member offsets in the same pass. Lookups use that index, and reverse search preserves last-duplicate-key semantics. The index grows geometrically rather than with the byte size of string payloads.
- `sealed type` restricts construction/updates to the declaring module. Parsed JSON values retain their validation invariant; callers can read fields and copy bytes, but cannot forge raw/kind/index combinations.
- Pure internal record calls borrow live arguments. Escaping children acquire ownership before return; temporaries remain alive through calls. Empty arrays are canonical non-owning values, and static string fields stay immutable.
- Bounded nonrecursive functions called with literal strings receive an inlining hint. Allocator headers cache their size-class index instead of recomputing it on every release.

Axon remains source-slice/index based, while Rust constructs serde_json::Value and Bun constructs JavaScript values. Their representations and memory policies differ. Native x86 performance, other parser libraries, arbitrary schemas, and universal language-performance rankings are not established here. Local VM measurements share the physical host; inspect the complete run ranges. Peak RSS is GNU time accounting, not Docker working set or PSS.

Raw commands, outputs, tool versions, binary/source hashes, dependency audits and timings: `/axon/bench/json/results/2026-10-25-094345`.
