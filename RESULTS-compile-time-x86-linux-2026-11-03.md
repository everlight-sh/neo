# Compile times: Neo against Rust, Go and Zig — x86-64 Linux, 2026-11-03

## Setup

- **Box:** a temporary Vultr `voc-c-2c-4gb-50s-amd`. Its two vCPUs are one AMD EPYC-Milan core with two SMT threads; it has 4 GB of RAM.
- **Software:** Ubuntu 24.04.5 (kernel 6.8.0-146), clang 18.1.3, Python 3.12.3, rustc and cargo 1.99.1, Go 1.25.14, Zig 0.17.0.
- **Second box:** the stage breakdown of the six smaller programs and the CI run used a second box of the same plan, with an EPYC-Genoa CPU. Both boxes were created for this work and destroyed afterwards.
- **Trees:** "Neo before" is `6e18e65` (Neo 0.1.1). "Neo after" is this branch (`9fb0f9a`, `6eb88d2`, `f8d464e`). Both were run from source checkouts on the same box.

## Summary

| Target | Before | After | Met? |
|---|---:|---:|---|
| hello, cold build under 1 s | 1.08 s | 0.70 s | yes |
| TLS fixture, ≥ 3× faster | 44.67 s | release 28.45 s (1.57×); `--dev` 11.57 s (3.86×) | **no** in the default release profile; yes only with `--dev` |
| large program, ≥ 3× faster | 640.4 s | release 153.0 s (4.19×); `--dev` 47.8 s (13.4×) | yes |

Other programs:

- The HTTPS client went from 53.0 s to 37.5 s (1.41×), or 16.5 s with `--dev`.
- The HTTP server, JSON and N-body programs are 1.25–1.40× faster.

Generated code:

- 99 of 114 corpus programs compile to byte-identical IR.
- The 15 that change, plus `examples/json-cli`, are the programs where the new inline-expansion bound applies.
- Their measured run time is unchanged: no case is more than 0.1% slower.

The TLS fixture missed the target in release because most of its build is still clang -O3 on a few very large functions (23.5 of 28.5 s). The bound shortened them; it did not remove them.

Against the other toolchains, using release profiles and cold builds:

- **Neo builds fastest** for hello (0.70 s), the HTTP server (1.72 s) and N-body (0.89 s):
  - Rust: 1.99, 14.41 and 5.25 s.
  - Go: 4.10, 11.91 and 4.75 s.
  - Zig: 16.35, 18.65 and 17.18 s.
  - Rust spends its time on dependencies (hyper, tokio, rayon) and on fat LTO. Go spends it recompiling its runtime and standard-library packages from an empty cache. Neo also compiles its runtime and standard library from source in every build, but there is less of it.
- **JSON** is a tie: Neo 5.27 s, Rust 5.14 s, Go 5.21 s. Zig takes 18.5 s.
- **HTTPS client:** Neo ties Rust (37.5 s against 37.6 s) and beats Zig (40.5 s), but Go is 3.2× faster (11.6 s). Go also compiles its TLS stack from source here, because its cache is empty, but its compiler optimises much less than LLVM -O3.
- **Debug and dev profiles:**
  - Against Zig Debug, Neo `--dev` wins on hello, the HTTP server, JSON and N-body (0.69–3.56 s against 4.09–4.23 s), and loses on the HTTPS client (16.45 s against 5.38 s).
  - Against Rust debug, it wins on the HTTP server (1.41 s against 8.54 s), N-body (0.81 s against 2.38 s) and the HTTPS client (16.45 s against 18.51 s), and loses on hello (0.69 s against 0.15 s) and JSON (3.56 s against 2.27 s).
- **Unchanged rebuilds:** Neo loses. A cache hit costs 0.26–1.23 s, against 0.04–0.08 s for Cargo and Go, because computing Neo's cache key parses every source file. Zig's `build-exe` keeps no output cache, so its rebuild compiles the program again: 12.6–36.7 s in ReleaseFast.
- **Edits:** Neo loses clearly. It has no incremental compilation, so an edit is a full build. Go and Rust debug rebuild in 0.11–0.40 s. Against Rust release (fat LTO), Neo is faster after an edit for hello, the HTTP server and N-body, and slower for JSON (5.27 s against 2.70 s) and the HTTPS client (37.4 s against 11.6 s).

## Method

`bench/compile/run.py` builds every (program, build) pair three ways per round:

- **cold:** every build cache the toolchain keeps is emptied first. That is Neo's `.neo-build`, Cargo's target directory, `GOCACHE`, and Zig's local and global caches. Downloaded dependency sources stay.
- **noop:** the same build again, with nothing changed.
- **edit:** one comment line is appended to the program's main source file.

Rounds visit the pairs in a shuffled order (fixed seed), so drift on the box spreads over every implementation. Wall time, CPU time and peak RSS come from GNU time. Neo rows also record `--report`'s stage split. Three rounds were run; the large program ran in the first round only, since one build of it took more than ten minutes before this work. Tables show medians of wall seconds. For 30 of the 43 (program, build) pairs with three rounds, the cold builds' range is within 3% of its minimum. The widest are sub-second builds (hello before: 1.07–1.22 s) and Go's first-round builds (JSON: 8.0 s against 5.1–5.2 s). No Neo before range overlaps its after range. Every round's numbers are in `results.json`.

Builds:

| Build | Command |
|---|---|
| Neo release | `./neo build P -o OUT --report` (LLVM -O3, the default) |
| Neo dev | the same with `--dev` (-O1, no policy inlining) |
| Rust release | `cargo build --release --offline -p P`: opt-level 3, one codegen unit, fat LTO, the profile every Rust row of the runtime benchmarks uses |
| Rust debug | `cargo build --offline -p P` (Cargo's dev profile) |
| Go | `go build` with `CGO_ENABLED=0 GOFLAGS=-trimpath` |
| Zig ReleaseFast / Debug | `zig build-exe -OReleaseFast` / `-ODebug` |

Neo has no incremental compilation: an edit rebuilds the whole program. Rust recompiles only the edited crate, though fat LTO re-optimises everything. Go recompiles one package. Zig 0.17's `zig build-exe` never caches its output, so its noop and edit rows are full rebuilds. Through the build system (`bench/compile/zig/build.zig`), an unchanged hello rebuild takes 0.02 s, but the first cold `zig build` also compiles the build runner (94 s for hello, against 16 s with `build-exe`).

## Results

The tables show median wall seconds on the EPYC-Milan box. Cold builds start with every build cache emptied. Noop builds rebuild with nothing changed. Edit builds follow one comment line appended to the main source file.

### Cold

| Program | Neo before | Neo after | Neo dev | Rust release | Rust debug | Go | Zig ReleaseFast | Zig Debug |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| hello | 1.08 | 0.70 | 0.69 | 1.99 | 0.15 | 4.10 | 16.35 | 4.12 |
| HTTP server | 2.24 | 1.72 | 1.41 | 14.41 | 8.54 | 11.91 | 18.65 | 4.23 |
| JSON | 6.59 | 5.27 | 3.56 | 5.14 | 2.27 | 5.21 | 18.51 | 4.19 |
| N-body | 1.25 | 0.89 | 0.81 | 5.25 | 2.38 | 4.75 | 17.18 | 4.09 |
| HTTPS client | 53.02 | 37.47 | 16.45 | 37.55 | 18.51 | 11.55 | 40.54 | 5.38 |
| TLS fixture | 44.67 | 28.45 | 11.57 | – | – | – | – | – |
| large | 640.44 | 153.01 | 47.81 | – | – | – | – | – |

### Noop

| Program | Neo before | Neo after | Neo dev | Rust release | Rust debug | Go | Zig ReleaseFast | Zig Debug |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| hello | 0.27 | 0.26 | 0.27 | 0.04 | 0.04 | 0.04 | 12.59 | 0.54 |
| HTTP server | 0.29 | 0.29 | 0.29 | 0.05 | 0.05 | 0.08 | 15.08 | 0.63 |
| JSON | 0.60 | 0.59 | 0.58 | 0.04 | 0.04 | 0.06 | 14.54 | 0.61 |
| N-body | 0.28 | 0.27 | 0.27 | 0.04 | 0.04 | 0.05 | 13.33 | 0.56 |
| HTTPS client | 1.24 | 1.23 | 1.22 | 0.08 | 0.08 | 0.08 | 36.65 | 1.83 |
| TLS fixture | 1.09 | 1.06 | 1.06 | – | – | – | – | – |
| large | 0.87 | 0.89 | 0.93 | – | – | – | – | – |

### Edit

| Program | Neo before | Neo after | Neo dev | Rust release | Rust debug | Go | Zig ReleaseFast | Zig Debug |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| hello | 1.09 | 0.69 | 0.68 | 1.92 | 0.11 | 0.14 | 12.62 | 0.54 |
| HTTP server | 2.22 | 1.72 | 1.39 | 6.08 | 0.29 | 0.36 | 15.05 | 0.64 |
| JSON | 6.64 | 5.27 | 3.58 | 2.70 | 0.15 | 0.16 | 14.57 | 0.61 |
| N-body | 1.28 | 0.89 | 0.83 | 2.90 | 0.17 | 0.15 | 13.43 | 0.57 |
| HTTPS client | 53.32 | 37.39 | 16.54 | 11.57 | 0.40 | 0.34 | 36.88 | 1.85 |
| TLS fixture | 44.50 | 28.50 | 11.55 | – | – | – | – | – |
| large | 637.50 | 151.67 | 48.32 | – | – | – | – | – |

The full table, with CPU seconds, peak RSS and binary size, is in `bench/compile/results/2026-11-03/summary.md`. Some points from it:

- Peak RSS of the large program's cold build went from 2.07 GB to 0.91 GB.
- For the TLS fixture it went from 423 MB to 298 MB.
- Neo's binaries are the smallest for every program: hello is 10 KB, against 353 KB for Rust, 1.9 MB for Go and 4.0 MB for Zig ReleaseFast.

## Where a cold Neo build spends its time

Each row is one cold build with `--report`. The IR then goes through clang once more with `-ftime-report`, to split clang's compile into the LLVM optimizer and the code generator. Those timers come from a separate run and add their own overhead, so read the split as a proportion.

- The six smaller programs ran on the EPYC-Genoa box.
- The large program (\*) ran on the EPYC-Milan box. Its "before" row is the benchmark's own cold build there, without the `-ftime-report` run.
- "Before" builds compile and link in one clang invocation, so their clang column includes the link.

| Program | Build | Wall | Parse | Check (prove) | AST opt | Lower | Clang compile | Optimizer / codegen | Link | IR lines | Cuts |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| hello | before | 1.03 | 0.15 | 0.48 | 0.01 | 0.11 | 0.15 | 0.1 / 0.1 | incl. | 3,241 | 0 |
| hello | after | 0.66 | 0.15 | 0.17 (0.09) | 0.01 | 0.05 | 0.12 | 0.1 / 0.1 | 0.02 | 3,241 | 0 |
| hello | `--dev` | 0.64 | 0.15 | 0.17 (0.09) | 0.01 | 0.05 | 0.11 | 0.1 / 0.1 | 0.02 | 3,241 | 0 |
| HTTP server | before | 2.10 | 0.17 | 0.59 | 0.02 | 0.20 | 0.98 | 0.5 / 0.6 | incl. | 24,295 | 0 |
| HTTP server | after | 1.63 | 0.17 | 0.20 (0.11) | 0.02 | 0.11 | 0.97 | 0.5 / 0.6 | 0.03 | 24,295 | 0 |
| HTTP server | `--dev` | 1.31 | 0.16 | 0.20 (0.11) | 0.02 | 0.10 | 0.66 | 0.4 / 0.4 | 0.03 | 24,295 | 0 |
| JSON | before | 6.26 | 0.44 | 1.72 | 0.05 | 1.17 | 2.67 | 1.4 / 1.4 | incl. | 45,429 | 0 |
| JSON | after | 4.98 | 0.43 | 0.86 (0.57) | 0.06 | 0.74 | 2.65 | 1.4 / 1.4 | 0.02 | 45,429 | 0 |
| JSON | `--dev` | 3.33 | 0.43 | 0.85 (0.57) | 0.05 | 0.69 | 1.07 | 0.6 / 0.7 | 0.03 | 45,429 | 0 |
| N-body | before | 1.18 | 0.15 | 0.47 | 0.01 | 0.13 | 0.29 | 0.2 / 0.1 | incl. | 7,306 | 0 |
| N-body | after | 0.83 | 0.16 | 0.18 (0.10) | 0.01 | 0.07 | 0.26 | 0.1 / 0.2 | 0.02 | 7,306 | 0 |
| N-body | `--dev` | 0.78 | 0.16 | 0.17 (0.10) | 0.01 | 0.06 | 0.21 | 0.1 / 0.1 | 0.02 | 7,306 | 0 |
| HTTPS client | before | 50.31 | 1.04 | 2.57 | 0.40 | 4.04 | 41.95 | 21.6 / 24.5 | incl. | 336,582 | 0 |
| HTTPS client | after | 35.62 | 0.99 | 1.54 (0.98) | 0.17 | 2.23 | 30.31 | 15.9 / 17.7 | 0.04 | 336,582 | 3 |
| HTTPS client | `--dev` | 15.52 | 1.01 | 1.57 (1.00) | 0.17 | 2.14 | 10.24 | 4.7 / 7.2 | 0.04 | 336,582 | 0 |
| TLS fixture | before | 42.47 | 0.87 | 2.45 | 0.38 | 3.55 | 34.93 | 18.2 / 20.3 | incl. | 214,681 | 0 |
| TLS fixture | after | 27.09 | 0.82 | 1.41 (0.86) | 0.15 | 1.87 | 22.49 | 12.1 / 12.9 | 0.03 | 214,681 | 3 |
| TLS fixture | `--dev` | 10.86 | 0.82 | 1.41 (0.85) | 0.15 | 1.85 | 6.28 | 2.8 / 4.4 | 0.03 | 214,681 | 0 |
| large* | before | 640.44 | 0.67 | 1.65 | 0.08 | 5.26 | 632.46 | – | incl. | – | – |
| large* | after | 153.29 | 0.69 | 0.89 (0.44) | 0.07 | 3.37 | 147.86 | 79.2 / 77.2 | 0.05 | 1,012,106 | 11 |
| large* | `--dev` | 47.74 | 0.68 | 0.89 (0.45) | 0.07 | 3.29 | 42.41 | 17.4 / 28.5 | 0.04 | 1,012,106 | 0 |

What the table shows:

- **Front end.** In hello and N-body, check (which includes proving) was the largest stage. It is now about a third of what it was: hello went from 0.48 s to 0.17 s. In the TLS fixture, the whole front end (parse, check, AST optimisation, lowering) went from 7.3 s to 4.3 s.
- **Clang.** Clang is more than 80% of the build for the three large programs, and at -O3 its time splits roughly evenly between optimizer and code generator. The expansion bound cut it by 28–36% for the TLS fixture and the HTTPS client, which each have 3 cut callees. For the large program it cut it by a factor of 4.3. There the bound keeps 11 callees, mostly parser helpers, as calls, instead of copying them into functions hundreds of thousands of lines long.
- **`--dev`.** It removes policy inlining and runs `-O1`. That takes another factor of 3.0–3.6 off clang for the big programs, and little for the small ones, whose clang time was small already.
- **IR lines.** The IR line counts are the same for every build of a program. Policy inlining is carried out inside clang, through `alwaysinline` on the callee definitions, so it never shows in the emitted module.

## What changed

Three compiler commits.

### 1. Front end, byte-identical output (`9fb0f9a`)

Profiling the Python front end found no single hot spot. Several passes repeated work they had already done:

- **Fourier-Motzkin proving** is the largest front-end cost, about 1.1 s of the TLS fixture's 1.5 s check on an M-series Mac. Each constraint's integer form and dedup key are now computed once per `Lin` and kept on it. Answers are memoised by constraint set. That is exact: FM's answer, its blow-up limit included, depends neither on constraint order nor on duplicates. All 29,449 queries of six programs gave the same answers as before. TLS proving went from 1.09 s to 0.64 s.
- **Counterexamples** were searched for every first attempt, even though most of them are then proven with ambient facts. They are now searched only for goals that stay unproven.
- **The effects fixpoint** walked every body again each round. It now summarises each body once (fixed capabilities plus callee names).
- **Range analysis** re-evaluated every function each round. A function whose inputs and read callee outputs are unchanged now replays its recorded intervals: the same joins in the same order. TLS: 0.62 s to 0.18 s.
- **Inlining policy** asked each function's size and recursion once per call site. It now asks once per function.
- **Lowering:** `lty`/`managed` are memoised by type identity, and `children` caches each node class's fields. Runtime/stdlib path checks resolve each path once (`neoc/trust.py`) instead of about 20,000 `Path.resolve()` calls per TLS build.

Across the 342 corpus builds (114 programs × x86-64 Linux, ARM64 Linux, ARM64 macOS), IR and reports are byte-identical before and after this commit. With all three commits, the front-end total for those builds went from 1,561 s to 1,052 s. That was measured on a shared development Mac, so it is indicative only.

### 2. Bounding policy-inlining growth (`6eb88d2`)

Neo forces inlining of small pure helpers (≤160 AST nodes) and of calls with constant bool or string arguments. The policy is transitive: a helper is inlined together with everything inlined into it. For the TLS fixture, 211K IR lines of function bodies become 1.93M lines once expanded, and one handshake function alone grows to 604K. Clang -O3 is superlinear in function size, and `alwaysinline` applies at every optimisation level. So, on the EPYC-Genoa box, the TLS fixture spent 32 s in clang at -O3 and still 13 s at -O0, and the large program spent 580 s.

`NEO_INLINE_EXPANSION` (default 262,144 IR lines; 0 turns it off) bounds this growth. Working bottom-up over the emitted IR, a function that would grow past the bound keeps its largest small-pure callees as ordinary calls until it fits; LLVM's own cost model then decides about those calls. Three kinds of callee are never cut:

- constant-argument specialisations, whose constants fold away code the line count includes;
- explicit `inline fn`;
- callees that expand to less than 1/16 of the bound, which are the hot-loop helpers inlining exists for.

A function that those callees alone keep over the bound is cut from its own callers instead. `--report` lists the cuts in `inline_expansion_cuts`.

A first version could also cut constant-key `json_get`. That made `bench/core/orders_stages` 12% slower (0.183 → 0.206 s), which is why specialisations are now exempt.

### 3. Build reports and the dev profile (`f8d464e`)

`--report` now splits the build into parse, check (with `prove_seconds`), AST optimisation, lowering, clang compile and link. To do that, clang compiles to an object and links in a second invocation. The binaries are byte-identical to the single invocation's: on x86-64 Linux, all 69 programs with unchanged IR that were compared produce the same binary.

`neo build --dev` / `neo run --dev` build at -O1 with no policy inlining (`inline fn` is still honoured). The profile is part of the cache key, and checking is the same as in release builds.

## Generated code

The front-end commit changes no output. The expansion bound changes 15 programs. The compile/link split changes no binary.

- **IR snapshots.** Snapshots cover 114 corpus programs × 3 targets (x86-64 Linux, ARM64 Linux, ARM64 macOS), comparing the parent commit with this branch:
  - 99 programs have byte-identical IR on every target.
  - 15 differ on all three targets: orders_stages, the HTTPS client, the large program, and the TLS, TLS 1.2, TLS web, X.509, X.509 web, P-384, agent transport, HTTP keep-alive and four JSON fixtures.
  - `examples/json-cli` is outside the snapshot corpus and changes too.
  - All of them are programs where the bound cuts at least one callee.
- **Binaries.** On x86-64 Linux, 83 programs were built with the parent commit and with this branch, using the same clang, and their binaries were compared:
  - 69 binaries are byte-identical.
  - 2 programs are rejected identically by both trees. `examples/unproven.neo` is a deliberate proof failure; `examples/jsx-ssr/server.neo` needs the JSX functions that its `build.ts` generates.
  - The other 9 are programs from the changed-IR set above.
  - This job ran with the compile/link split already in place but with an earlier version of the bound, so it shows nothing about those 9 beyond their changed code. The run-time check below used the final tree; its binaries are byte-identical to the final tree's builds.
  - The job stopped after `language_p256`, before the last fixtures. Their IR comparison is above.
- **Run time** (`bench/compile/runtime_check.py`; 7 interleaved rounds; medians on the EPYC-Milan box; release builds, parent commit against this branch). The programs measured are the ones whose code changed:

| Case | Before | After | Change |
|---|---:|---:|---:|
| orders_stages mode 2 (s) | 0.1738 | 0.1741 | +0.1% |
| orders_stages mode 3 (s) | 0.1882 | 0.1866 | -0.9% |
| json-cli 200k records (s) | 0.3684 | 0.3608 | -2.1% |
| https new connection (us/request) | 1274.3 | 1263.3 | -0.9% |
| https keep-alive 1 MiB (us/request) | 3639.8 | 3645.0 | +0.1% |
| p384 verify x200 (s) | 0.4338 | 0.4306 | -0.7% |

No case is slower by more than 0.1%. json-cli is 2.1% faster, which is inside its spread of samples (0.35–0.39 s before, 0.35–0.40 s after).

- **CI.** These all pass on the x86-64 box with the final tree:
  - `./neo test`: 37 native cases and all 59 integration scripts, 0 failures.
  - The `verify.yml` steps: `bun install`, freestanding smoke, reproducible release (two archives with the same SHA-256) and language-freestanding.
  - The log is in `bench/compile/results/2026-11-03/ci.log`.

## The dev profile

`--dev` trades run time for build time. This measurement compares release builds against `--dev` builds of the same tree, on the same EPYC-Milan box, over 5 interleaved rounds, and reports medians. Outputs are identical between the two builds.

| Case | Release | `--dev` | `--dev` / release |
|---|---:|---:|---:|
| orders_stages mode 2 (s) | 0.1745 | 0.3578 | 2.05× |
| orders_stages mode 3 (s) | 0.1843 | 0.4001 | 2.17× |
| json-cli 200k records (s) | 0.3550 | 0.5922 | 1.67× |
| https new connection (us/request) | 1290.0 | 1472.5 | 1.14× |
| https keep-alive 1 MiB (us/request) | 3665.4 | 4409.0 | 1.20× |
| p384 verify x200 (s) | 0.4403 | 0.4634 | 1.05× |

- Code that depends on inlined helpers runs about twice as slow: the `json_get` lookups in orders_stages, and the JSON filtering in json-cli at 1.67×.
- I/O- and bignum-heavy code loses 5–20%.
- Use `--dev` for edit-build-run loops, not for measurement or deployment. The README already says that its binaries run slower.

`--dev --opt-level 0` removes LLVM optimisation as well. Measured on the EPYC-Milan box (one build each; the `--dev` column is the benchmark median):

| Program | `--dev` (-O1) wall | `--dev --opt-level 0` wall | of which clang compile | link |
|---|---:|---:|---:|---:|
| hello | 0.69 | 0.57 | 0.04 | 0.02 |
| HTTP server | 1.41 | 0.80 | 0.14 | 0.03 |
| JSON | 3.56 | 2.67 | 0.27 | 0.03 |
| N-body | 0.81 | 0.63 | 0.06 | 0.03 |
| HTTPS client | 16.45 | 8.20 | 2.64 | 0.05 |
| TLS fixture | 11.57 | 6.65 | 1.74 | 0.04 |
| large | 47.81 | 15.81 | 10.51 | 0.08 |

Here everything outside clang is most of the remaining time: about 5.5 s of the HTTPS client's 8.2 s, and 4.9 s of the TLS fixture's 6.65 s. Without policy inlining, the TLS fixture's clang at -O0 takes 1.7 s. With policy inlining, -O0 took 13.3 s on the EPYC-Genoa box.

## Notes on the other toolchains

- **Rust.**
  - The release rows use the profile every Rust row of the runtime benchmarks uses: opt-level 3, one codegen unit, fat LTO. Cargo's default release profile (16 codegen units, thin local LTO) builds faster, but it is not what was measured at run time.
  - Cold builds compile every dependency from source: hyper, tokio, serde, reqwest, rustls and ring. That is most of the HTTP and HTTPS times.
  - An edit recompiles one crate, but fat LTO still re-optimises the whole program.
- **Go.**
  - `GOCACHE` is emptied for cold builds, so they include the runtime and the standard library packages the program imports. With a warm cache, a Go build of a changed main package is well under a second (the edit column).
- **Zig.**
  - Emptying Zig's global cache means a cold build compiles compiler_rt and the parts of std the program uses.
  - `zig build-exe` never caches its output, so its noop and edit rows compile the program again (ReleaseFast: 12.6 s for hello). Only what the global cache holds, such as compiler_rt, is reused.
  - Through `zig build` with `bench/compile/zig/build.zig`, an unchanged hello is 0.02 s. But that build's first run compiles the build runner as well: 94 s cold for hello, against 16 s with `build-exe`.
- **Neo.**
  - Neo has no incremental compilation. A noop build is a cache hit keyed on the program's whole source graph, compiler and flags: it still parses every module and hashes it.
  - An edit, even a comment, rebuilds everything. The IR embeds source line numbers for runtime error messages ("integer overflow at fn:24"), so even a comment-only edit that shifts lines changes the binary.

## Not done, and follow-ups

- **A lower expansion bound.** Under the first version of the rule, 131,072 lines brought TLS clang from 32 s to 18 s, and the large program's clang from 128 s to 90 s (EPYC-Genoa). It would change more programs, including JSON code paths that `orders_json` measures, so it needs its own run-time study before becoming the default.
- **Comment-only edits.** Rebuilding could be skipped when an edit changes no token and no line number. Doing that needs the line table moved out of the IR, or a token-level hash.
- **Clang over several translation units.** The box has one core with two SMT threads, and most of the remaining time is in a few 100K–200K-line functions, so splitting the module would gain little here. It is worth measuring on machines with more cores.
- **Per-function object caches.** These would give real incremental builds, but they stop LLVM from inlining across cache units, so the generated code would change.
- **Lowering of record-heavy code.** Lowering takes 1.9 s of the TLS fixture's front end and is the largest front-end stage left.

## Raw data

`bench/compile/results/2026-11-03/`:

| File | Contents |
|---|---|
| `results.json` | every `run.py` measurement (EPYC-Milan) |
| `summary.md` | `summarize.py`'s tables, including CPU seconds, peak RSS and binary sizes |
| `breakdown.json` | `breakdown.py` rows for the six smaller programs (EPYC-Genoa) |
| `breakdown-large.json` | the same for the large program, after and `--dev` (EPYC-Milan) |
| `runtime.json` | release run time, parent commit against this branch |
| `devruntime.json` | release against `--dev` |
| `o0dev.log` | the `--dev --opt-level 0` builds: wall, clang compile and link seconds |
| `identity.log` | the binary comparison: exit codes, binary SHA-256 prefixes and build seconds for both trees |
| `snapshot.md` | the IR snapshot comparison |
| `probe.log` | parent-commit cold builds and the same IR through clang alone (EPYC-Genoa) |
| `expansion-tls.log`, `expansion-large.log` | clang time of the TLS fixture and the large program under several bounds and -O levels, with the first version of the cut rule (EPYC-Genoa) |
| `ci.log` | the CI run |
