# Dynamic JSON workload after optimization — 2026-10-25

Measured 2026-10-25T08:19:02.582045+00:00 on native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Each command is pinned to CPU 0; AXON_THREADS=1. No CPU emulation. 15 measured process runs after two warmups, with implementation order shuffled each round. GNU time/taskset startup, construction, parsing, field access, destruction and process shutdown are included.

This is the unchanged `examples/library_bench.ax` workload from the usability report: construct a different JSON object each iteration, fully validate/parse it, read integer id and decoded UTF-8 name, count array elements and checksum the result. Rust still uses the unmodified optimized serde_json::Value implementation; Bun still uses the unmodified JSON.parse implementation. The previous Axon executable is preserved and rerun in this session. Every output is checked. This measures the complete JSON workflow, not an isolated parser instruction or every JSON input shape.

| Documents | Implementation | Median wall ms | Min–max ms | Median CPU ms | Max process peak RSS MiB |
|---:|---|---:|---:|---:|---:|
| 10,000 | Axon | 5.40 | 5.09–6.10 | 4.38 | 1.38 |
| 10,000 | Axon previous | 5.36 | 4.97–5.78 | 4.31 | 1.38 |
| 10,000 | Rust | 6.99 | 6.37–7.93 | 5.89 | 1.62 |
| 10,000 | Bun | 22.89 | 22.11–40.56 | 20.40 | 41.12 |
| 100,000 | Axon | 33.31 | 32.53–35.80 | 32.29 | 1.38 |
| 100,000 | Axon previous | 33.55 | 32.52–35.87 | 32.38 | 1.38 |
| 100,000 | Rust | 43.46 | 42.78–45.65 | 41.99 | 1.62 |
| 100,000 | Bun | 57.53 | 55.83–63.36 | 55.35 | 73.50 |
| 1,000,000 | Axon | 307.15 | 305.33–349.61 | 306.12 | 1.38 |
| 1,000,000 | Axon previous | 307.16 | 306.17–324.32 | 305.92 | 1.38 |
| 1,000,000 | Rust | 404.35 | 398.13–432.55 | 403.14 | 1.62 |
| 1,000,000 | Bun | 357.71 | 348.88–394.42 | 355.90 | 108.75 |

## Existing JSON implementation (unchanged by this task)

- UTF-8 validation is integrated with string scanning; strict validation, Unicode scalar rules and the depth limit remain enforced.
- Object validation builds member offsets in the same pass. Lookups use that index, and reverse search preserves last-duplicate-key semantics. The index grows geometrically rather than with the byte size of string payloads.
- `sealed type` restricts construction/updates to the declaring module. Parsed JSON values retain their validation invariant; callers can read fields and copy bytes, but cannot forge raw/kind/index combinations.
- Pure internal record calls borrow live arguments. Escaping children acquire ownership before return; temporaries remain alive through calls. Empty arrays are canonical non-owning values, and static string fields stay immutable.
- Bounded nonrecursive functions called with literal strings receive an inlining hint. Allocator headers cache their size-class index instead of recomputing it on every release.

Axon remains source-slice/index based, while Rust constructs serde_json::Value and Bun constructs JavaScript values. Their representations and memory policies differ. Native x86 performance, other parser libraries, arbitrary schemas, and universal language-performance rankings are not established here. Local VM measurements share the physical host; inspect the complete run ranges. Peak RSS is GNU time accounting, not Docker working set or PSS.

Raw commands, outputs, tool versions, binary/source hashes, dependency audits and timings: `/axon/bench/json/results/2026-10-25-081902`.
