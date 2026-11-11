# Usable Neo implementation and verification

This tracks the complete usability roadmap requested on 2026-10-24. Runtime
code stays Neo over kernel syscalls. Clang/LLVM remain build tools. Existing
benchmark reports and binaries are preserved.

## Work and acceptance criteria

- [x] Modules/imports: transitive loading, relative and standard imports,
  missing/cyclic import diagnostics, dependency-aware cache invalidation.
- [x] Owned data: records containing byte strings, arrays and nested records;
  collection and structured error/optional-value APIs with lifetime tests.
- [x] Standard library: UTF-8, vectors/maps, JSON, files, environment and clocks.
  Invalid inputs and OS errors must be recoverable.
- [x] Effectful HTTP: opt-in handlers with explicit declared capabilities;
  existing pure renderers and HTTP tests remain supported.
- [x] JSON CLI: validate/filter/sort file input and write output; test Unicode,
  malformed data, missing files and diagnostics.
- [x] Durable notes: CRUD plus SSR, append-only storage, concurrent mutations,
  restart recovery and interrupted-tail handling.
- [x] Webhook worker: persistent jobs, outbound HTTP, retries, duplicate
  delivery, timeouts and shutdown/restart recovery.
- [x] Compiler confidence: independent reference evaluation, generated programs,
  optimizer differential tests, overflow boundaries and parser/runtime fuzzing.
- [x] Tooling: project manifest, run/test/format commands, executable examples,
  structured diagnostics and cold/warm build measurements.
- [x] Linux x86-64: syscall/entry/event ABI support and executable verification
  alongside ARM64; distinguish emulated correctness from native performance.
- [x] Tests/benchmarks: reproducible drivers and raw results for new APIs/apps,
  build performance, resource use and existing HTTP/render/compute workloads.
- [x] Runtime dependency audits: no undefined symbols, shared libraries, CRT or
  ELF interpreter; Linux empty-root execution; preserve macOS loader caveat.

## Current status

The initial implementation, platform correctness/audit suites, benchmarks and
fresh-image verification are complete. Baseline sources remain under
`.kernel-build/usability/baseline/`. See
[the validation report](RESULTS-usability-validation-2026-10-24.md) and
[the application guide](docs/getting-started.md) for exact scope, evidence and limits.
