# Dynamic JSON workload after optimization — 2026-10-24

Measured 2026-10-24T09:26:09.623716+00:00 on native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Each command is pinned to CPU 0; AXON_THREADS=1. No CPU emulation. 9 measured process runs after two warmups, with implementation order shuffled each round. GNU time/taskset startup, construction, parsing, field access, destruction and process shutdown are included.

This is the unchanged `examples/library_bench.ax` workload from the usability report: construct a different JSON object each iteration, fully validate/parse it, read integer id and decoded UTF-8 name, count array elements and checksum the result. Rust still uses the unmodified optimized serde_json::Value implementation; Bun still uses the unmodified JSON.parse implementation. The previous Axon executable is preserved and rerun in this session. Every output is checked. This measures the complete JSON workflow, not an isolated parser instruction or every JSON input shape.

| Documents | Implementation | Median wall ms | Min–max ms | Median CPU ms | Max process peak RSS MiB |
|---:|---|---:|---:|---:|---:|
| 10,000 | Axon | 5.66 | 4.94–8.02 | 4.50 | 1.38 |
| 10,000 | Axon previous | 24.35 | 23.51–44.08 | 23.25 | 1.38 |
| 10,000 | Rust | 7.25 | 6.64–23.39 | 5.94 | 1.62 |
| 10,000 | Bun | 23.44 | 21.19–32.59 | 20.92 | 41.12 |
| 100,000 | Axon | 33.47 | 32.91–35.61 | 32.42 | 1.38 |
| 100,000 | Axon previous | 215.58 | 214.13–244.18 | 214.40 | 1.38 |
| 100,000 | Rust | 43.34 | 41.97–60.91 | 42.31 | 1.62 |
| 100,000 | Bun | 57.11 | 55.89–80.96 | 55.01 | 73.50 |
| 1,000,000 | Axon | 313.37 | 302.44–326.29 | 311.09 | 1.38 |
| 1,000,000 | Axon previous | 2090.44 | 2076.15–4354.72 | 2089.10 | 1.38 |
| 1,000,000 | Rust | 400.80 | 395.33–422.51 | 399.66 | 1.62 |
| 1,000,000 | Bun | 367.33 | 353.25–1420.66 | 364.94 | 108.75 |

## What changed

- UTF-8 validation is integrated with string scanning; strict validation, Unicode scalar rules and the depth limit remain enforced.
- Object validation builds member offsets in the same pass. Lookups use that index, and reverse search preserves last-duplicate-key semantics. The index grows geometrically rather than with the byte size of string payloads.
- `sealed type` restricts construction/updates to the declaring module. Parsed JSON values retain their validation invariant; callers can read fields and copy bytes, but cannot forge raw/kind/index combinations.
- Pure internal record calls borrow live arguments. Escaping children acquire ownership before return; temporaries remain alive through calls. Empty arrays are canonical non-owning values, and static string fields stay immutable.
- Bounded nonrecursive functions called with literal strings receive an inlining hint. Allocator headers cache their size-class index instead of recomputing it on every release.

Axon remains source-slice/index based, while Rust constructs serde_json::Value and Bun constructs JavaScript values. Their representations and memory policies differ. Native x86 performance, other parser libraries, arbitrary schemas, and universal language-performance rankings are not established here. Local VM measurements share the physical host; inspect the complete run ranges. Peak RSS is GNU time accounting, not Docker working set or PSS.

Raw commands, outputs, tool versions, binary/source hashes, dependency audits and timings: `bench/json/results/2026-10-24-092609`.

## Correctness and dependency verification

The complete suites pass on macOS ARM64, native Linux ARM64 and emulated x86-64
(QEMU 8.2): 47 compiler/module/project tests, seven native/documentation cases,
800 independent-evaluator comparisons, 2,000 malformed-source parser cases,
2,080 bounded-stencil executions, and existing compute/fork/HTTP/application
regressions. TSX-to-Axon output still matches React on all 1,000 prop values
with one/four workers on macOS and ARM64 Linux. A fresh verification image passes
the complete suite and HTTP from an otherwise empty root.

Additional strict JSON checks pass 5,027 valid/malformed byte inputs against Python
with Axon optimizations both enabled and disabled. A 737-case accessor corpus
covers Unicode boundaries, escaped keys, duplicate keys, nested values, growing
wide-object indexes and ownership. Raw-byte and offset-array mutation checks verify
that modifying a copy cannot corrupt the original sealed value. These accessor
checks pass on all three targets; x86 performance was not measured.

Separate IR instrumentation counts 128,001 previous versus 12,001 optimized
allocator calls per 1,000 documents, including fixed run overhead. Instrumented
binaries are excluded from timing results. The standalone Axon executable grows
from 45,528 to 51,664 bytes; measured peak process RSS remains 1.38 MiB.
Both old/new Linux binaries have zero unresolved symbols, no ELF interpreter and
no shared-library dependency. Python/LLVM remain build tools. macOS retains its
system-loader requirement, with no imported runtime functions.

`Json` construction is now module-restricted. Applications create values through
`json_parse` and use `json_none().value` for the empty sentinel. Field reads remain
available; direct `Json { ... }` construction and `with` updates outside the
standard module are rejected. The file-CLI example is migrated. This invariant
permits indexed access without weakening validation of incoming JSON.

Validation logs, allocation profiles and the implementation snapshot are retained
under `.kernel-build/json-opt/`. The broader file-CLI/library/build/stateful-app
rerun is in [the updated usability report](RESULTS-usability-json-optimized-linux-2026-10-24.md).
