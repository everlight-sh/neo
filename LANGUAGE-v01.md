# Neo language and standard-library v0.1 work

Scope: compiler, Neo runtime, standard library, packages, developer tools,
tests and benchmarks. Do not implement application/database features or change
examples. Linux application executables must retain no imported symbols,
interpreter, CRT or shared-library dependencies. Python/LLVM remain build tools;
macOS retains its existing mandatory loader-only libSystem caveat.

## Acceptance checklist

- [x] Generic record/function types, tagged alternatives, exhaustive matching,
  typed optional/result values and error propagation, with owned-data tests.
- [x] Efficient growable vectors, hash maps and sorting, with model tests and
  geometric-size/allocation benchmarks against the preserved implementation.
- [x] Scoped file/socket ownership, cleanup on error, checked resource moves and
  a defined bounded communication/cancellation model.
- [x] DNS, HTTP methods/streaming, monotonic deadlines and a separately tested
  C-free TLS/certificate-verification library; no dynamic runtime fallback.
- [x] Namespaces, deterministic local packages/lockfiles, editor completion and
  readable/structured diagnostics, formatter and versioned release tooling.
- [x] Language semantics and compatibility policy, continuous compiler/failure
  testing, native ARM64 audits, x86-64 static ELF audits with QEMU execution,
  native dual-architecture CI configuration and reproducible release artifacts.
- [x] Full regressions plus feature-specific correctness, failure, lifetime and
  performance coverage; raw timings, source snapshots and dependency audits.

Baseline sources are preserved in `.kernel-build/language-v01/baseline`.
Existing DB and example code is outside the implementation scope; unchanged
regression tests may exercise it to detect compiler/runtime regressions.

## Final evidence

See [the final report](RESULTS-language-core-linux-2026-10-24.md) for feature
coverage, raw logs, dependency audits and benchmark methodology. Final unit/native
checks pass 76 Python tests and 19 native/documentation cases on macOS ARM64,
native Linux ARM64 and emulated Linux x86-64. Native x86-64 performance and the
configured remote CI jobs were not run here. TLS is experimental and unaudited;
raw fork heap isolation and 1M-key map footprint remain documented limitations.

The two reproducible source bundles are byte-identical; all measured final Neo
benchmark executables were rebuilt and matched their measured SHA-256 hashes.
All 81 preserved baseline source hashes and 45 application/example source hashes
remain unchanged. No C runtime or Linux shared-library runtime fallback was added.

## N-body/map follow-up — 2026-10-25

The [follow-up report](RESULTS-nbody-map-linux-2026-10-25.md) records the worker,
disjoint-field ownership, large-buffer reuse and byte-map changes, with
80 unit tests and 22 native/documentation cases on each tested target. The
application/example source hashes remain unchanged. Historical results above
refer to their preserved source snapshots; the follow-up contains current data.
