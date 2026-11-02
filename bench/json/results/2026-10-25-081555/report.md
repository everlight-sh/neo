# Dynamic JSON workload after optimization — 2026-10-24

Measured 2026-10-25T08:15:55.654342+00:00 on native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Each command is pinned to CPU 0; AXON_THREADS=1. No CPU emulation. 7 measured process runs after two warmups, with implementation order shuffled each round. GNU time/taskset startup, construction, parsing, field access, destruction and process shutdown are included.

This is the unchanged `examples/library_bench.ax` workload from the usability report: construct a different JSON object each iteration, fully validate/parse it, read integer id and decoded UTF-8 name, count array elements and checksum the result. Rust still uses the unmodified optimized serde_json::Value implementation; Bun still uses the unmodified JSON.parse implementation. The previous Axon executable is preserved and rerun in this session. Every output is checked. This measures the complete JSON workflow, not an isolated parser instruction or every JSON input shape.

| Documents | Implementation | Median wall ms | Min–max ms | Median CPU ms | Max process peak RSS MiB |
|---:|---|---:|---:|---:|---:|
| 10,000 | Axon | 5.78 | 5.15–6.98 | 4.55 | 1.38 |
| 10,000 | Axon previous | 5.53 | 5.41–6.84 | 4.47 | 1.38 |
| 10,000 | Rust | 7.42 | 6.67–18.94 | 6.22 | 1.62 |
| 10,000 | Bun | 23.76 | 22.14–33.36 | 21.49 | 41.12 |
| 100,000 | Axon | 34.82 | 32.84–38.50 | 33.68 | 1.38 |
| 100,000 | Axon previous | 35.70 | 33.68–153.90 | 33.97 | 1.38 |
| 100,000 | Rust | 45.36 | 44.44–48.54 | 43.67 | 1.62 |
| 100,000 | Bun | 63.03 | 60.64–68.95 | 59.36 | 73.50 |
| 1,000,000 | Axon | 401.60 | 306.11–677.94 | 399.69 | 1.38 |
| 1,000,000 | Axon previous | 319.70 | 310.44–443.98 | 318.22 | 1.38 |
| 1,000,000 | Rust | 434.27 | 407.37–594.64 | 432.64 | 1.62 |
| 1,000,000 | Bun | 371.60 | 363.91–398.99 | 367.30 | 108.75 |

## What changed

- UTF-8 validation is integrated with string scanning; strict validation, Unicode scalar rules and the depth limit remain enforced.
- Object validation builds member offsets in the same pass. Lookups use that index, and reverse search preserves last-duplicate-key semantics. The index grows geometrically rather than with the byte size of string payloads.
- `sealed type` restricts construction/updates to the declaring module. Parsed JSON values retain their validation invariant; callers can read fields and copy bytes, but cannot forge raw/kind/index combinations.
- Pure internal record calls borrow live arguments. Escaping children acquire ownership before return; temporaries remain alive through calls. Empty arrays are canonical non-owning values, and static string fields stay immutable.
- Bounded nonrecursive functions called with literal strings receive an inlining hint. Allocator headers cache their size-class index instead of recomputing it on every release.

Axon remains source-slice/index based, while Rust constructs serde_json::Value and Bun constructs JavaScript values. Their representations and memory policies differ. Native x86 performance, other parser libraries, arbitrary schemas, and universal language-performance rankings are not established here. Local VM measurements share the physical host; inspect the complete run ranges. Peak RSS is GNU time accounting, not Docker working set or PSS.

Raw commands, outputs, tool versions, binary/source hashes, dependency audits and timings: `/axon/bench/json/results/2026-10-25-081555`.
