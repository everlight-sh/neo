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

On a fresh Ubuntu x86-64 box, as root, with this checkout at `/root/new` and
the checkout to compare against at `/root/base`:

```sh
sh bench/compile/setup.sh
(cd bench/compile/rust && ~/.cargo/bin/cargo fetch --locked)
export PATH=$HOME/.cargo/bin:$PATH
NEO_TREES=before=/root/base,after=/root/new NEO_DEV=after python3 bench/compile/run.py results.json 3
NEO_TREES=before=/root/base,after=/root/new NEO_DEV=after python3 bench/compile/breakdown.py breakdown.json
NEO_TREES=before=/root/base,after=/root/new python3 bench/compile/runtime_check.py runtime.json 7
python3 bench/compile/summarize.py results.json
```

- `run.py`: every (program, build) pair cold (all toolchain build caches
  emptied; downloaded sources kept), unchanged, and after appending one comment
  line to the main source file, in shuffled order each round. Wall time, CPU
  time and peak RSS come from GNU time; Neo rows also keep `--report`'s stage
  split. `LARGE_ROUNDS` (default 1) limits the large program's rounds.
- `breakdown.py`: one cold Neo build per program with `--report`, then the same
  IR through clang with `-ftime-report` to split its compile into the LLVM
  optimizer and code generation.
- `runtime_check.py`: run time, before and after, of the programs whose
  generated code the inline expansion cap changes.
- `zig/build.zig`: `zig build-exe` never caches its output, so `run.py`'s
  unchanged Zig rebuild compiles everything again. `zig build NAME
  -Doptimize=ReleaseFast` measures the cached case.

Run nothing else on the box while measuring.
