# Axon agent-core readiness — 2026-10-25

Axon now has typed function values, explicit capture closures, generational resource arenas, cooperative tasks, bounded queues, cancellation-aware socket I/O, data codecs, scoped subprocesses, atomic file replacement, and authenticated HTTP/SSE transport integration. These are compiler/runtime/standard-library changes. The broader request is **partially complete**: production networking, a complete task runtime, and optional media/UI libraries are still missing. This is not evidence that a complete production Go agent can yet be replaced safely.

The 381 snapshotted Go agent files and 45 existing Axon example sources are unchanged. No application-specific agent policy, DB implementation or altered competitor workload was introduced. Seventeen existing compiler/runtime/library files changed and seventeen standard-library modules were added; the exact list is in `.kernel-build/agent-core-readiness-2026-10-25/source-changes.json`.

## Implemented behavior

| Area | Added | Boundaries |
|---|---|---|
| Typed callbacks | `Fn(...)`, capability-checked `Effect<...>(...)`, named function references, generic `Closure<C,A,R>` | Explicit capture records; no automatic lambdas/trait objects. Owned/refined/external targets and erased dependent array constraints are rejected. |
| Long-lived resources | `Arena`, typed `Ref<Resource>`, adopt/borrow/release, reusable slots and generation checks | Stale access traps; full/closed adoption traps. Single-process ownership, not GC or a synchronized mutable heap. Finalizers close exactly once. |
| Tasks and communication | Bounded admission, explicit resumable state, timers, cancellation/shutdown ticks, bounded generic FIFO | Cooperative steps must return and use nonblocking I/O. No preemption, M:N scheduler, multi-FD reactor or automatic async lowering. |
| Socket I/O | Nonblocking try-read/try-write and cancellation-aware deadline wrappers | Readiness waits are capped at 10 ms. Scheduling can add latency; not every DNS/TLS operation is cancellable. |
| JSON and codecs | Typed constructors, serialization, bool/float accessors, ordered duplicate-preserving object keys, strict Base64/Base64url and URL percent codecs | Existing JSON depth/validation limits remain. Exact float parser prioritizes correctness over optimized parsing throughput. |
| Numbers, text and time | Exact decimal-to-binary64 ties-to-even parsing, signed-zero round trips, finite math, RFC3339, Unicode 16 case folding/categories/whitespace | Formatter emits 17 significant digits rather than shortest decimal. Math is approximate and incomplete; no normalization, locale mapping, timezone database or leap seconds. |
| Processes | Absolute-path execution, explicit argv/env, nonblocking stdin/stdout and separate stderr, exit/signal status, scoped kill/reap | Exec errors become exit 127. No PATH search, process groups, working-directory options, stdin half-close or high-level communicate API. |
| Persistence | Remove/mkdir/rename and exclusive 0600 temporary write → file sync → rename → directory sync | Directory-sync failure can follow committed rename. No complete filesystem API, path sandbox or cross-file transaction. |
| HTTP/SSE | Typed transport callbacks, validated custom/auth headers, bounded chunked reading and incremental SSE over TCP and experimental TLS 1.3 | Connection: close; no HTTP/2 or reusable pool. Server callback API still has no streaming flush interface. TLS remains experimental. |

Process launch arguments use private mappings: the child cannot lose its argument storage when the parent cleans up. Axon-created files and sockets are close-on-exec. Tests also caught and fixed first-read preservation in cancellation wrappers, effect-capability ordering, stale arena-slot reuse and invalid reference diagnostics.

The full API contract and runnable closure example are in `docs/language-v01.md`.

## Validation

- **macOS ARM64:** 86 Python unit tests; 27 native/documentation cases; full existing integration suite; new independent codec, Unicode/date/math, persistence and TCP/TLS/SSE oracles.
- **Linux ARM64:** the same 86 unit tests and 27 native/documentation cases, full integration suite, and new oracles. Full integration includes compiler/optimizer differential checks, protocol/crypto/TLS tests, existing application regressions and React-rendering comparisons.
- **Linux x86-64 under QEMU:** 86 unit tests and 27 compiled cases, plus the new independent codec/utilities/network oracles. This is emulated execution, not native x86 performance evidence.
- **Empty Linux root:** callbacks, JSON/SSE/task libraries, 10,000 managed resource reuse cycles, Unicode, atomic persistence and Axon-to-Axon process I/O ran with only the copied static executables and the state file they wrote. No shell, libraries or device files were present.
- **Dependency audit:** all six new Linux test executables have no undefined imports, ELF interpreter or shared-library dependency. The TLS transport executable is included in the import audit and tested separately against an independent TLS peer.
- **Source integrity:** all 381 Go agent hashes and 45 existing example hashes still match. The preserved 62-file compiler baseline is retained.
- **Reproducible source bundle:** two independently generated 83-file bundles match SHA-256 `d709a040b0e4426c5cab1d641e10d937db6333d29b6b8db5d08f7d821ee7f9c2`.

Linux executables use the OS kernel directly and import no runtime libraries. Python/LLVM remain build tools. macOS imports no library functions but its mandatory libSystem loader command remains; macOS is therefore not literally dependency-free.

Earlier interrupted logs are retained: an overlapping older Mac invocation hit a test-port collision, and the first broad Linux run lost its VM connection. The dedicated VM was restarted; successful final logs supersede those attempts. No interrupted run contributes benchmark timings.

Evidence is under `.kernel-build/agent-core-readiness-2026-10-25/`: `mac-final-tests.log`, `mac-verified-native.log`, `mac-verified-readiness.log`, `linux-final-tests.log`, `linux-verified-native.log`, `linux-verified-readiness.log`, `linux-verified-empty-root.log`, `x86-emulated-native.log`, and `x86-verified-readiness.log`. The Unicode oracle on older Python versions skips code points that its older Unicode database marks unassigned; the macOS oracle uses Unicode 16.0.0.

## Performance regression checks

Native ARM64 Linux, 8-vCPU/6-GiB Colima VM, Clang 18, Rust 1.98.1, Go 1.25.1 and Bun 1.3.13. Suites ran sequentially after validation. The physical host was shared with other work, so these are local workload measurements with retained trial ranges, not isolated production capacity or universal language rankings. Existing workload and competitor sources were preserved.

Seven measured process runs, checksummed, with shuffled order and matching one/four-worker budgets:

| Representative workload, four workers | Axon | Rust | Go |
|---|---:|---:|---:|
| N-body, 1024 bodies × 3 steps | 3.43 ms | 3.91 ms | 5.84 ms |
| Stencil, 1M elements × 20 passes | 11.30 ms | 12.90 ms | 16.21 ms |
| Mandelbrot, 1200×1200 × 300 iterations | 47.54 ms | 69.41 ms | 72.24 ms |

The separate interleaved preserved-compiler comparison found no material regression: the 1M-key string map measured **781.82 → 779.65 ms**, with peak RSS **86.16 → 86.16 MiB**. The generic 1M-key map remained **285.61 MiB**. The controlled N-body sample measured **4.47 → 4.35 ms**; it is a separate run from the mixed-compute table above. Small differences should be treated as run variation, not an optimization claim.

For the unchanged million-document JSON workflow: **Axon 304.44 ms**, preserved Axon 308.92 ms, Rust 405.02 ms, Bun 362.64 ms. Axon keeps its existing indexed source-slice representation; Rust and Bun build their own value representations. This is not a comparison of arbitrary JSON schemas or an isolated decimal parser.

Three 3-second measured HTTP runs after warmup, validated routes, client and server sharing the VM:

| HTTP scenario | Axon req/s | Rust req/s | Go req/s | Bun req/s |
|---|---:|---:|---:|---:|
| Hello, 64 connections, default workers | 570,432 | 261,397 | 284,734 | 97,967 |
| Pipeline depth 16 | 5,841,856 | 3,043,917 | 337,063 | 23,615 |
| Hello, one worker | 211,361 | 190,524 | 85,644 | 87,716 |

Default-worker hello used **5.56 µs CPU/request and 0.92 MiB sampled PSS** in Axon, versus Rust **8.36 µs and 3.90 MiB**, Go **15.53 µs and 14.66 MiB**, and Bun **10.66 µs and 53.13 MiB**. Worker models and supported protocol breadth differ; HTTP/SSE/TLS client additions are not benchmarks of production TLS server throughput.

New API microbenchmarks, seven runs after two warmups: optimized function-value loop **0.34 ns/iteration**, one-element FIFO push/pop **2.26 ns/pair**, managed resource adopt/borrow/release **761 ns/cycle**, one cooperative task tick **52.85 ns/tick**. All recorded peak RSS values were 1.38 MiB. LLVM can inline/devirtualize these callbacks and scalar-replace this simple queue; these figures do not establish general indirect-call, contended queue, scheduler or I/O throughput. There is no Rust/Go/Bun comparison for these new microbenchmarks.

Detailed reports: `RESULTS-agent-readiness-compute-linux-2026-10-25.md`, `RESULTS-agent-readiness-json-linux-2026-10-25.md`, `RESULTS-agent-readiness-http-linux-2026-10-25.md`. Raw before/after and API measurements: `.kernel-build/agent-core-readiness-2026-10-25/bench-core/measurements.json`, `bench-runtime/measurements.json`, and `benchmark-runs.json`.

## What still blocks replacing a production Go agent

1. **Production transport:** ECDSA/AES interoperability, broader certificate-chain/PKIX handling, security/constant-time review and sustained TLS fuzzing; HTTP/2/HPACK/flow control, pooling/reuse, IPv6, complete cancellation and server-side streaming/backpressure. Passing the experimental RSA/X25519/ChaCha TLS tests does not close these gaps.
2. **A stronger task model:** scalable readiness multiplexing, structured parent/child cancellation and result delivery, enforceable shutdown behavior for slow work, bounded worker pools, and a clearly specified shared-state/thread-safety model. Cooperative callbacks cannot preempt a blocking or infinite step.
3. **Host and data API completeness:** child process groups/tree shutdown, stdin EOF and bounded communicate helpers; stat/directory/permission/watch APIs; a full URL parser/resolver, broader numeric/math coverage, Unicode normalization/graphemes and time-zone support. Arena admission should gain recoverable errors instead of traps.
4. **Language ergonomics and production evidence:** automatic closures and interface/trait-style abstractions where they simplify provider/tool dispatch; clearer mutable-state patterns, debugger/source maps/backtraces, longer memory/concurrency stress and fuzz campaigns, more stable diagnostics/APIs, packaging/versioning and an ecosystem. A self-hosted compiler is a separate project; Python/LLVM build tools remain accepted here.
5. **Optional libraries:** WebSockets, WebRTC/ICE/DTLS/SRTP/SCTP, a pure-Axon Opus codec, terminal UI and provider SDKs. These remain unimplemented and belong in libraries rather than the language core. Replacing the Go agent's current native Opus loading while preserving the C-free requirement needs substantial codec work.
6. **The actual migration proof:** an Axon text-agent slice behind persistent stdio, shadowed against Go with recorded provider/tool transcripts, cancellation/deadline/no-late-side-effect checks, crash recovery, long-running memory tests and a rollout/fallback plan. This task deliberately left the Go agent unchanged; those end-to-end migration tests have not been performed.

The next usable boundary is a bounded text-agent helper or shadowed agent slice, while Go continues to own production transport and lifecycle until the remaining checks are satisfied.
