# Compile times: Neo, Rust, Go, Zig

How long it takes to build equivalent programs, from nothing, unchanged and
after a one-line edit. The report is `RESULTS-compile-time-x86-linux-2026-11-03.md`.

| Program | Neo | Rust | Go | Zig |
|---|---|---|---|---|
| hello | `examples/hello.neo` | `rust/hello` | `go/hello` | `zig/hello.zig` |
| HTTP server | `examples/http.neo` | `bench/rust/src/http_hyper.rs` (hyper, tokio) | `bench/go/http` | `bench/zig/http_std.zig` |
| JSON | `examples/library_bench.neo` | `bench/rust/src/usability.rs` (serde_json) | `bench/core/json.go` | `bench/zig/json.zig` |
| N-body | `examples/nbody.neo` | `bench/rust/src/nbody.rs` (rayon) | `bench/go/nbody` | `bench/zig/nbody.zig` |
| HTTPS client | `bench/fetch/fetch.neo` | `bench/fetch/rust` (reqwest, rustls) | `bench/fetch/go/client` | `zig/fetch.zig` (std.http) |
| TLS fixture | `tests/fixtures/language_tls.neo` | – | – | – |
| large | `compiler/src/main.neo` (Neo's self-hosted front end) | – | – | – |

`rust/` is a Cargo workspace with one package per program, so a cold build
compiles exactly that program's dependencies, with the release profile every
Rust row of the runtime benchmarks uses (opt-level 3, one codegen unit, fat
LTO). `Cargo.lock` pins every dependency; `cargo fetch` downloads them before
timing, and builds run `--offline`.

## Running

On a fresh Ubuntu x86-64 box, as root, `sh bench/compile/setup.sh` installs
the toolchains. The native runner measures the Neo rows: every program cold
(an empty library cache), unchanged, and after appending one comment line to a
scratch copy of its source. Wall time, CPU time and peak RSS come from GNU
time, and each row keeps `--report`'s stage split.

```sh
./neo run --dev bench/run.neo -- compile 3
```

The report's Rust, Go and Zig rows, its clang `-ftime-report` breakdown, the
run-time check and the IR snapshots came from Python drivers: `run.py`,
`breakdown.py`, `runtime_check.py`, `noop.py`, `ir_snapshot.py` and
`summarize.py`. They were removed with the rest of the repository's Python
and are still in the `v0.2.3` tag, for example
`git show v0.2.3:bench/compile/run.py`.

`zig/build.zig` exists because `zig build-exe` never caches its output, so an
unchanged rebuild with it compiles everything again. `zig build NAME
-Doptimize=ReleaseFast` measures the cached case.

Run nothing else on the box while measuring.
