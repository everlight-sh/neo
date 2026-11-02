# Axon vs Rust compute and axon-kv vs a Go document database — x86-64 Linux, 2026-10-30

Temporary Vultr `voc-c-8c-16gb-150s-amd` (8 dedicated AMD EPYC-Rome vCPUs, 16 GB), Ubuntu 24.04,
clang 18.1.3, rustc 1.99.1, Go 1.25.1. Instance created for this run and destroyed afterwards.
Median complete-process milliseconds, 7 interleaved rounds after a warmup; one worker pinned to
CPU 0, four workers to CPUs 0–3 (`AXON_THREADS`/`RAYON_NUM_THREADS`). Outputs agree across all
variants. "Before" is the compiler without this change set, built on the same machine.

## Compute

| Case | Workers | Axon before | Axon after | Rust | After vs Rust |
|---|---:|---:|---:|---:|---:|
| mandel-1200-1200-300 | 1 | 144.5 | 147.2 | 213.1 | 1.45× |
| stencil-1000000-20 | 1 | 39.3 | 39.6 | 56.0 | 1.41× |
| nbody-1024-3 | 1 | 12.0 | 12.0 | 19.2 | 1.60× |
| nbody-4096-10 | 1 | 399.5 | 398.0 | 729.9 | 1.83× |
| mandel-1200-1200-300 | 4 | 69.7 | 39.1 | 56.3 | 1.44× |
| stencil-1000000-20 | 4 | 20.6 | 19.6 | 20.5 | 1.05× |
| nbody-1024-3 | 4 | 4.5 | 4.3 | 6.8 | 1.58× |
| nbody-4096-10 | 4 | 104.7 | 103.4 | 187.9 | 1.82× |

Changes:

- Persistent worker pool for certified allocation-free regions on Linux
  (`axonc/kernel_workers.py`, `runtime/core.ax`): workers are started once as `CLONE_THREAD`
  threads, sleep on a futex, and claim chunks from a shared atomic counter. This replaces one
  `CLONE_VM` process per worker per region with fixed contiguous chunk ranges, which left
  Mandelbrot's expensive middle rows on one worker (69.7 → 39.1 ms with four workers).
- Masked `sum` loops use 8 lanes except on Darwin (`vectorize.sum_lanes`). On ARM64 Linux 16 lanes
  ran about 3× slower than 8 on the same IR; on x86-64 the two are within noise.
- ARM64 no longer uses the forced 4-lane array vectorizer for `i64` bodies (NEON has two i64
  lanes and no 64-bit vector multiply); LLVM's own loop vectorizer handles them. Measured 2.8×
  faster for the stencil body on ARM64 Linux under Docker.

The worker pool and both vectorizer rules were not re-verified on ARM64 Linux hardware; an
earlier Docker trial of the pool on ARM64 started no workers (sequential fallback).

## axon-kv vs the Go document database (bench/native/run.py, 7 rounds, one CPU)

| Rows | Phase | Axon ms | Go ms | Speedup |
|---:|---|---:|---:|---:|
| 1000 | create_collection | 0.327 | 0.542 | 1.65× |
| 1000 | define_fields | 0.177 | 0.866 | 4.90× |
| 1000 | ingest | 3.412 | 6.368 | 1.87× |
| 1000 | create_computed | 0.940 | 1.087 | 1.16× |
| 1000 | source_aggregate | 0.043 | 0.197 | 4.59× |
| 1000 | maintained_aggregate | 0.006 | 0.024 | 3.85× |
| 1000 | replace_10_percent | 1.021 | 1.266 | 1.24× |
| 1000 | updated_maintained_aggregate | 0.007 | 0.037 | 5.45× |
| 1000 | watch | 1.378 | 2.157 | 1.57× |
| 1000 | checkpoint | 0.965 | 1.693 | 1.75× |
| 1000 | whole_workflow | 13.893 | 29.001 | 2.09× |
| 1000 | reopen | 3.329 | 6.500 | 1.95× |
| 10000 | create_collection | 0.443 | 0.564 | 1.27× |
| 10000 | define_fields | 0.202 | 0.654 | 3.24× |
| 10000 | ingest | 28.941 | 53.295 | 1.84× |
| 10000 | create_computed | 3.590 | 5.820 | 1.62× |
| 10000 | source_aggregate | 0.058 | 1.400 | 24.16× |
| 10000 | maintained_aggregate | 0.006 | 0.017 | 2.70× |
| 10000 | replace_10_percent | 4.434 | 5.624 | 1.27× |
| 10000 | updated_maintained_aggregate | 0.008 | 0.029 | 3.47× |
| 10000 | watch | 11.319 | 16.662 | 1.47× |
| 10000 | checkpoint | 4.470 | 9.828 | 2.20× |
| 10000 | whole_workflow | 73.584 | 157.445 | 2.14× |
| 10000 | reopen | 4.264 | 8.372 | 1.96× |

Axon is faster on all 24 timed operations and at least 2× on 11. Peak RSS 5.6/19.5 MiB against
9.5/35.4 MiB; file bytes 524,288/4,194,304 against 342,767/2,599,511 (reserved journal capacity).

A `perf` profile of 20 runs of the 10k workload is flat: JSON command decoding and encoding
dominate, and kernel first-touch page faults take about 15%. Pre-populating anonymous mappings
(`MAP_POPULATE`) changed no phase by more than noise, so it was not kept.

## JSON standard-library pass (second temporary instance, same type)

`stdlib/json.ax` changes, each verified by the JSON differential suites:

- `json_plain_end` scans 8 bytes per step for the first quote, backslash or control byte;
  `json_text`, quoting and encoder sizing use it, so escape-free strings skip the byte loop.
- `json_skip` jumps between structural bytes (quote, brackets, braces) 8 bytes per step.
- Object encoders prepare each `,"name":` prefix once; a member name is one copy instead of a
  separator write, name copy and colon write.

| Workload | Before | After | Change |
|---|---:|---:|---:|
| `examples/library_bench.ax` JSON workflow, 1M documents, 1 worker | 304–318 ms | 277–290 ms | −9% |
| Rust `serde_json::Value` equivalent (`usability parse 1000000`) | 400 ms | — | Axon 1.38× |
| axon-kv watch, 10k rows | 11.25 ms | 10.70 ms | −5% |
| other axon-kv phases | — | — | within noise |

Remaining axon-kv cost is structural rather than in the generic JSON routines: per-field
records and slices while packing each document, a zero-filled pack buffer, and first-touch page
faults (about 16% of the 10k workload). The large-block cache already retains freed blocks, and
`MAP_POPULATE` did not help, so the next gains need a single-pass document packer in axon-kv.

## Single-pass document packer (third temporary instance, same type) — reverted

Measured and then reverted for its small gain; the code, its `json_object_member_span` accessor
and the differential test additions are not in the tree. Kept here as the measured result.

`axon-kv/src/document/computed.ax` and `packed.ax`: `doc_computed_pack_spans` reads each member's
key and scalar value in place from the validated row (new allocation-free stdlib accessor
`json_object_member_span`), applies computed fields over those spans, and writes the packed
document in one sized buffer. Escaped keys or strings, non-integer numbers and nested values
fall back to the record-based packer, so results are unchanged: `documents_scalar_pack.py` now
also requires the span packer to match the record packer byte for byte (408 of 1,168 cases take
the span path), command outputs are identical, and database files differ only in the per-file
header identity bytes (offsets ≤ 40), exactly as two runs of the old binary do.

| Phase (same compiler, 9 rounds) | Old packer | Span packer | Go database |
|---|---:|---:|---:|
| ingest, 10k rows | 25.65 ms | 24.66 ms (−4%) | 40.66 ms |
| ingest, 1k rows | 2.92 ms | 2.86 ms (−2%) | 5.06 ms |
| replace_10_percent, 10k rows | 3.87 ms | 3.76 ms (−3%) | 4.72 ms |
| whole workflow, 10k rows | 60.8 ms | 61.8 ms (noise) | 131.6 ms |

The packer removed per-field records and copies, but packing was a smaller share of ingest than
the inclusive profile suggested; command token decoding and first-touch memory remain.

## Remaining gaps versus Rust (fourth temporary instance, same type)

Tools: clang 18.1.3, rustc 1.99.1, wrk 4.1.0. All variants produce identical sums.

JSON decoding, one CPU, best / median of 9 interleaved runs (`examples/library_bench.ax`,
`bench/core/orders_json.ax`, `bench/rust/src/typed_json.rs`):

| Workload | Axon (dynamic) | Rust `serde_json::Value` | Rust typed structs |
|---|---:|---:|---:|
| small document, built and decoded ×1M | 196.7 / 200.9 ms | 323.9 / 333.2 ms | 156.4 / 158.9 ms |
| 1,000-order array, decoded ×1,000 | 783.9 / 812.2 ms | 347.7 / 354.1 ms | 94.5 / 96.8 ms |

Axon's cost per order is flat from 250 to 16,000 rows (about 590 ns; no superlinear copying).
`bench/core/orders_stages.ax` splits it cumulatively: validation 63 ns, element splitting
+208 ns, four `json_get` lookups +297 ns, integer/text reads +21 ns. Each element and each
looked-up value becomes a separately allocated `Json` slice, with a member index rebuilt for
objects; validation itself is not the bottleneck.

HTTP hello (`examples/http.ax` vs `http_hyper`, `HYPER_PIPELINE_FLUSH=1`), server pinned to the
listed CPUs, `wrk -t4 -c64 --latency` on CPUs 4–7, 3 × 10 s after 2 s warm-up, medians:

| Workers | Server | req/s | p50 µs | p90 µs | p99 µs |
|---:|---|---:|---:|---:|---:|
| 1 | Axon | 96,197 | 638 | 690 | 1,250 |
| 1 | Rust | 89,480 | 715 | 782 | 870 |
| 4 | Axon | 309,911 | 103 | 198 | 247 |
| 4 | Rust | 273,402 | 221 | 319 | 415 |

One worker serves every ready connection of an `epoll_wait` sweep before waiting again, so with
64 busy connections the last one waits for the other 63; this fits the p50/p99 shape but has
not been traced.

## Closing the gaps (fifth temporary instance, same type)

Changes, all kept and verified (130 unit tests, 56/56 language scripts including the new
`tests/json_field_decoder.py` 1,212-case differential, 27/27 axon-kv scripts):

- `runtime/core.ax`: `rt_threads()` read and parsed `AXON_THREADS` from the environment on every
  call, and every parallel construct calls it, including small array comprehensions. It is now
  cached in runtime state (cleared for forked children). A 60-byte array allocation fell from
  about 155 ns to 15 ns; `int_text` from 153 to 14 ns.
- `axonc/llvm.py`: comprehensions over constant ranges of at most 64 elements, and constant
  fills (`arr(i in 0..n) -1`, `u8(0)`, booleans), compile to plain loops instead of outlined
  parallel regions. The decoder's hot function dropped from about 38 KB with 14 dispatch sites
  to 11,400 instructions with none.
- `runtime/http_linux.ax`: `epoll_wait` returns at most 32 ready connections (was 1,026).
  Unserved connections stay ready under level triggering and new requests interleave.
- `stdlib/json.ax`: prepared field decoder (`json_field_decoder`, `json_decode_object`,
  `json_decode_array`/`json_decode_next`, `json_field_int/text/bool/view/has`) that validates each
  object in one pass, records only wanted members, reads integers of up to 18 digits during the
  walk and keeps plain strings as shared slices; `json_get` borrows its arguments;
  `json_array_values` indexes object elements in the pass that finds their end; integer atoms
  of up to 18 digits skip the per-digit overflow division; `true`/`false`/`null` compare words.

HTTP hello, final code, 5 × 10 s, medians:

| Workers | Server | req/s | p50 µs | p90 µs | p99 µs |
|---:|---|---:|---:|---:|---:|
| 1 | Axon | 93,889 | 673 | 732 | 880 |
| 1 | Rust | 80,417 | 792 | 850 | 1,010 |
| 4 | Axon | 292,575 | 108 | 204 | 326 |
| 4 | Rust | 252,812 | 224 | 339 | 508 |

JSON, one CPU, interleaved medians (ms):

| Workload | Axon dynamic | Rust `Value` | Axon field decoder | Rust typed structs |
|---|---:|---:|---:|---:|
| small document ×1M | 290.7 | 405.8 | 234.0 | 200.6 |
| 1,000-order array ×1,000 | 232.9 | 415.6 | 123.5 | 117.0 |

Before this round the order array took 812 ms dynamically (Rust `Value` 354 ms) and had no
typed equivalent. Axon now beats `serde_json::Value` on both workloads; the prepared decoder is
5.5% (orders) and 15% (small document) behind serde's derived typed decoding. Profiles of the
decoder are flat: the remaining cost is code quality in byte scanning (38 unproven runtime
checks in the hot function, overflow-checked arithmetic, bounds-checked byte reads), not one
algorithmic step.

Compute (x86, final compiler) still beats Rust in all eight cases (1.06–1.83×), and axon-kv
remains faster than the Go database on all 24 phases (whole workflow 2.14× at 10k rows).

## Verification on this machine

- Compiler unit tests: 130 pass. Language integration scripts: 55/55 pass (before and after).
- `axon test`: `bounded-large-buffer-reuse` (`tests/fixtures/allocator_cache.ax`) fails
  identically with the compiler before this change; pre-existing on x86-64.
- axon-kv integration: 27/27 pass. `documents_faults.py` and `documents_reserved_journal.py`
  injected `rename`/directory-`fsync` failures into `checkpoint`, which since the reference
  checkpoint writes in place; those cases now use `compact` (temporary file, rename, directory
  sync), and a new case fails the in-place checkpoint's `fdatasync`.

## Compiler round: proving checks, cold paths, unique loop states (sixth temporary instance)

Temporary Vultr `voc-c-2c-4gb-50s-amd` (2 dedicated AMD vCPUs, 4 GB; a quarter of the earlier
box's price, enough for one pinned CPU), Ubuntu 24.04, clang 18.1.3, rustc 1.99.1. Destroyed
afterwards. This CPU runs the earlier code at a different ratio to Rust than the 8-vCPU box did
(the last round's decoder was already within 1–3% of typed serde here), so every comparison
below is base vs final vs Rust on this machine. Timings are `perf stat` user cycles and
task-clock, interleaved medians, one worker pinned to CPU 1. Outputs agree for every variant.
"Base" is the previous round's compiler and standard library.

JSON, one pinned CPU, medians of 15 (field decoder) or 11 (dynamic) interleaved runs:

| Workload | Base | Final | Rust | Final vs Rust |
|---|---:|---:|---:|---:|
| 1,000-order array ×1,000, field decoder vs typed structs | 98.0 ms | 87.5 ms | 96.5 ms | 1.10× faster |
| same, user cycles | 397.7M | 355.2M | 389.1M | |
| small document ×1M, field decoder vs typed structs | 164.9 ms | 122.1 ms | 169.2 ms | 1.39× faster |
| same, user cycles | 671.4M | 496.6M | 685.8M | |
| 1,000-order array ×1,000, dynamic vs `serde_json::Value` | 177.5 ms | 175.2 ms | 349.9 ms | 2.00× faster |
| small document ×1M, dynamic vs `Value` | 210.2 ms | 175.5 ms | 331.5 ms | 1.89× faster |

Instructions per order: base 2,263, final 1,976, Rust 1,730. Rust retires fewer instructions;
Axon's retire at higher IPC (5.6 vs 4.5). Branch and cache misses are negligible for both.

Compute regression check (the compiler changes apply to all code; this box has two vCPUs, so
two workers instead of four), medians of 7 rounds, stencil at two workers 30 rounds:

| Case | Workers | Base | Final | Rust | Final vs Rust |
|---|---:|---:|---:|---:|---:|
| mandel-1200-1200-300 | 1 | 131.7 | 131.8 | 185.9 | 1.41× |
| stencil-1000000-20 | 1 | 33.6 | 33.6 | 46.5 | 1.38× |
| nbody-1024-3 | 1 | 10.0 | 10.0 | 16.2 | 1.62× |
| nbody-4096-10 | 1 | 344.8 | 345.3 | 633.0 | 1.83× |
| mandel-1200-1200-300 | 2 | 67.5 | 67.9 | 95.1 | 1.40× |
| stencil-1000000-20 | 2 | 24.4 | 23.6 | 25.9 | 1.10× |
| nbody-1024-3 | 2 | 5.9 | 5.9 | 9.4 | 1.59× |
| nbody-4096-10 | 2 | 182.3 | 178.3 | 324.2 | 1.82× |

A first 7-round stencil run at two workers read 29.0 vs 26.8 ms; with 30 rounds and the same
binaries it is 23.6 vs 25.9 (CPU 0 also serves the system on this box).

HTTP hello, re-checked on a seventh temporary instance (`voc-c-8c-16gb-150s-amd`, AMD EPYC-Genoa;
8 vCPUs because four server workers need four more CPUs for `wrk`; destroyed afterwards).
Server pinned to CPU 0 or CPUs 0–3, `wrk -t4 -c64` on CPUs 4–7, 5 interleaved 10 s runs, medians:

| Workers | Server | req/s | p50 µs | p90 µs | p99 µs |
|---:|---|---:|---:|---:|---:|
| 1 | Rust (hyper) | 86,129 | 745 | 860 | 980 |
| 1 | Axon base | 96,851 | 647 | 751 | 860 |
| 1 | Axon final | 98,443 | 633 | 714 | 839 |
| 4 | Rust (hyper) | 256,157 | 227 | 338 | 454 |
| 4 | Axon base | 299,978 | 107 | 205 | 265 |
| 4 | Axon final | 292,038 | 111 | 211 | 281 |

Final beats Rust by 1.14× in throughput at both worker counts, with lower latency at every
percentile. Base and final are within run-to-run variation (+1.6% at one worker, −2.6% at four).
The first two four-worker runs had about 3 ms p99 for all three servers alike, so the table uses medians.

### Compiler

- **Arithmetic proofs with operand intervals** (`axonc/check.py`, `axonc/llvm.py`). The checker
  keeps the lexical facts of every `+`/`-`/constant `*` it cannot prove alone; code generation
  retries with the whole-program interval of each operand node. `i + count_trailing_zeros(m)/8`
  under `i <= n - 8` now proves (the quotient is in [0, 8]). Interval analysis learned
  `count_trailing_zeros`, `bit_and` with a non-negative operand, constant shifts and narrow
  `byte_read_le` (`axonc/ranges.py`).
- **`nsw` on proven arithmetic** and on counted-loop increments, so LLVM can reason across
  `i <= n - 8` and the reads it guards.
- **Byte reads, slices proven statically**: a constant-width `byte_read_le` or a `byte_slice`
  whose bounds the lexical facts entail emits no runtime width or bounds test. Unproven reads use
  the guard's own shape (`0 <= offset <= length - width`, non-wrapping), which LLVM matches
  against source loop conditions.
- **`check` predicates the facts already entail are discharged** at compile time (call-free
  predicates with proven arithmetic only, so no trap or effect is skipped); the obligation is
  reported as proven.
- **Boolean `let`s keep their condition**: `let room = i >= 0 && i <= n - 4 in if room then …`
  refines like the comparison itself.
- **`cold fn`** (contextual modifier; `cold` stays a valid identifier): never inlined and marked
  `cold`, so LLVM treats calls as unlikely and callers keep their registers. The small-helper
  `alwaysinline` policy had been pulling every escape, `\u` and UTF-8 path into the per-member
  hot function (11,400 instructions, 216-byte frame, six saved registers per member).
- **Set-only loop states are made unique once**: a scalar-array loop state that is only read
  (`len`, indexing) and replaced by `set(state, …)` is copied at loop entry if shared, after
  all initializers ran; its sets then store in place with no ownership or refcount test. Before,
  every `set` re-tested ownership, the refcount and the buffer address (about 20 instructions);
  clearing a 16-slot span array cost about 320 instructions per decoded object. States used any
  other way keep the per-set test.

### Standard library (`stdlib/json.ax`, `stdlib/strings.ax`)

- Word scanners read through `byte_read_le` under their loop guards, so the reads are proven.
- Escapes, `\u` decoding and non-ASCII key matching are `cold`; a string the word scan cannot
  finish continues in one cold call and, without escapes, is still recorded as a direct slice
  (no second scan in `json_field_text`).
- Member values: `true`/`false`/`null` compare one word; arrays are validated in one flat loop
  (nested containers still use the general scanner) and record their element count.
- New `json_field_json(fields, i)`: the member as a `Json` value; arrays carry the walk's count
  instead of rescanning. `bench/core/document_decoder.ax` uses it in place of
  `json_view_json(json_field_view(…))`.

### Verification

- Compiler unit tests: 130 pass, plus 6 new in `tests/test_proved_checks.py` (guarded word reads,
  interval-assisted overflow proofs with an unprovable control, discharged vs kept `check`,
  boolean `let` facts, `cold` codegen with `cold` as an identifier, set-only loop uniqueness and
  its shared-state fallback).
- Language integration: 56/56, plus the new `tests/set_only_loops.py` (registered in
  `tests/integration.py`): shared, borrowed, moved, two-state-aliased, zero-iteration and string
  literal sources stay intact under in-place set-only loops, 1 and 4 workers.
- `tests/json_field_decoder.py`: 1,212 differential cases pass, now also comparing
  `json_field_json` (kind, raw bytes, element count) with `json_parse`/`json_get`.
- axon-kv integration: 27/27.
