# Axon append and JSON regression fixes — 2026-10-25

Both target regressions are fixed at the measured workload level. Append returns to its pre-lookup-optimisation performance range, JSON surpasses that earlier version, all six one-million-key read cases retain their lead over Rust, and the winning byte/string-map memory figures are unchanged.

Native ARM64 Linux on Apple M1 Pro/Colima, 8 vCPUs and 6 GiB, with timed programs pinned to CPU 0 and one worker. No test/build processes overlap the accepted timing runs. The physical host is shared. Every output, map count and checksum is checked. Benchmark/application and competitor sources are unchanged.

“Original” is the frozen compiler/stdlib from before the preceding lookup task. “Lookup” is the frozen version with the lookup/memory wins and the reported append/JSON regressions. “Fixed” is this implementation. All three are rebuilt and interleaved in one comparison.

## Append and JSON

Append measures the existing fixture’s internal append-and-sum timer, excluding startup and output. JSON measures the unchanged complete process workflow: varying document construction, full validation/parse, typed field access, Unicode string decoding, array counting and destruction. It includes process/tool startup. JSON is not an isolated parser comparison.

| Workload | Entries/documents | Implementation | Median ms | Range ms | Max peak RSS MiB |
|---|---:|---|---:|---:|---:|
| append | 1,000,000 | Axon original | 5.692 | 5.210–7.227 | 13.66 |
| append | 1,000,000 | Axon lookup | 6.790 | 6.158–7.539 | 13.66 |
| append | 1,000,000 | Axon fixed | 5.726 | 5.059–6.567 | 13.66 |
| json | 10,000 | Axon original | 5.073 | 4.500–6.029 | 1.38 |
| json | 10,000 | Axon lookup | 4.987 | 4.516–8.310 | 1.38 |
| json | 10,000 | Axon fixed | 5.077 | 4.467–6.601 | 1.38 |
| json | 10,000 | Rust | 6.879 | 6.386–8.735 | 1.62 |
| json | 10,000 | Bun | 23.291 | 21.540–26.625 | 40.25 |
| json | 100,000 | Axon original | 29.503 | 28.804–31.035 | 1.38 |
| json | 100,000 | Axon lookup | 30.246 | 29.583–31.632 | 1.38 |
| json | 100,000 | Axon fixed | 28.637 | 27.680–30.153 | 1.38 |
| json | 100,000 | Rust | 43.578 | 42.939–47.521 | 1.62 |
| json | 100,000 | Bun | 57.870 | 56.139–62.424 | 72.62 |
| json | 1,000,000 | Axon original | 270.939 | 267.604–278.805 | 1.38 |
| json | 1,000,000 | Axon lookup | 281.651 | 277.042–287.433 | 1.38 |
| json | 1,000,000 | Axon fixed | 263.503 | 259.894–268.693 | 1.38 |
| json | 1,000,000 | Rust | 410.677 | 401.220–450.915 | 1.62 |
| json | 1,000,000 | Bun | 366.829 | 357.314–393.816 | 107.88 |

Append: 31 measured trials after three warmups. JSON: 15 measured trials after three warmups at each size. Order is shuffled per round. The fixed append median is 0.6% above the original median; its interval includes parity, while the slowdown relative to the lookup build is removed. The fixed 1M-document JSON median is 6.4% lower than the lookup build and 2.7% lower than the original.

Paired-round bootstrap of the ratio of medians, 20,000 resamples; ratios above 1 favour the fixed build.

| Workload | Compared with | Speedup | Bootstrap 95% interval |
|---|---|---:|---:|
| append | Axon original | 0.994× | 0.966–1.040× |
| append | Axon lookup | 1.186× | 1.158–1.230× |
| json | Axon original | 1.028× | 1.024–1.041× |
| json | Axon lookup | 1.069× | 1.057–1.080× |

Separate instrumented builds of all three versions each perform exactly **20 allocation requests / 8,388,752 requested bytes** for 1M appends. Their peak RSS is **13.66 MiB**. The allocation policy and array descriptor size are unchanged; this improvement does not come from reserving extra memory or excluding work. Instrumented binaries are not used for timings.

## Lookup and memory wins preserved

The existing map harness is unchanged: 15 measured trials after two warmups per allocation mode and size (0, 100k, 1M), shuffled implementation order. Each lookup phase constructs decimal keys, calls the public owned-value API, parses/checks the values and accumulates a checksum. Insert/update/delete and memory checkpoints are outside read timers. The final phase contains 50% missing keys.

| Allocation | Phase | Axon lookup ms | Axon fixed ms | Rust ms | Go ms |
|---|---|---:|---:|---:|---:|
| Growing | lookup | 98.58 | 95.31 | 156.99 | 260.39 |
| Growing | lookup_updated | 104.79 | 104.47 | 154.91 | 258.36 |
| Growing | lookup_remaining | 108.58 | 106.54 | 138.43 | 149.70 |
| Reserved | lookup | 97.44 | 96.80 | 159.70 | 266.01 |
| Reserved | lookup_updated | 101.45 | 102.59 | 157.62 | 265.27 |
| Reserved | lookup_remaining | 106.72 | 106.23 | 143.78 | 149.11 |

All six read-case bootstrap intervals favour Axon over Rust; raw intervals and round wins are in `analysis.json`.

| Allocation | Implementation | Steady RSS MiB | Peak RSS MiB |
|---|---|---:|---:|
| Growing | Axon lookup | 36.04 | 52.03 |
| Growing | Axon fixed | 36.04 | 52.03 |
| Growing | Rust | 160.48 | 204.48 |
| Growing | Go | 124.50 | 128.38 |
| Reserved | Axon lookup | 34.00 | 35.62 |
| Reserved | Axon fixed | 34.00 | 35.62 |
| Reserved | Rust | 160.50 | 160.50 |
| Reserved | Go | 98.12 | 125.12 |

Steady RSS keeps the complete original 1M-entry byte/string map alive; peak RSS is the process high-water mark after the full workflow. Go explicitly collects at its steady checkpoint, outside timing. The separate generic HashMap representation remains 285.61 MiB at 1M entries. Axon retains its 2 GiB map arena limit, owned returns, aliases and full SipHash-2-4.

## Core changes

- Compiler: for power-of-two-sized array elements up to 16 bytes, test whether a one-element push crosses a capacity boundary instead of recomputing a rounded capacity on every push. Size checks, ownership checks, growth allocations and copy-on-write remain. Record arrays keep their required SoA reallocation; non-power-of-two element sizes retain the original byte-capacity calculation.
- Strings: use checked direct paths for one-to-three-digit parsing and formatting, retaining the existing packed longer-integer path and signed/overflow/error fallbacks.
- JSON: compare unescaped key spans using safe 8/4/2/1-byte loads. A lane-wise backslash check prevents matching a raw escape spelling to its decoded key. Escaped-key decoding, duplicate-key semantics, complete JSON/UTF-8 validation and depth limits remain.

Only compiler/stdlib code and tests/tooling change. No application, DB or Go agent source changes. No runtime source file changes, allocator attributes, new runtime dependency or weakened hash is introduced.

## Tests and standalone execution

`./axon test` passed on native ARM64 macOS and Linux: **94 Python unit tests, 32 native/document cases, and the complete integration suite**. The suite covers ownership, compiler cache/relocation and optimization flags, HTTP 1/4 workers, TSX/React equivalence, JSON fuzz, DNS, crypto/TLS, process/channel behavior, compute, persistence/crash recovery and aggregation.

The x86-64 target passed the compiler/native suite under the QEMU runner, plus the new allocation, JSON-key and integer model tests. New coverage includes exact allocation/byte models through 1M elements for i64/i32/u8/bool, nested arrays, SoA records and retained aliases; capacity-boundary equivalence up to the maximum allocation; **13,172** binary/tail/alignment/Unicode/escaped/duplicate/missing-key cases; **12,433** integer parsing cases and **1,519** formatting cases (including every integer 0–999).

Actual measured Linux executables run without libraries: the map executable completed both 1M-entry modes in an empty root, and the append/JSON executables each completed their 1M-element workload in roots containing only themselves. ELF audits show no interpreter, shared-library dependency or undefined symbol. Python/LLVM remain build tools. macOS retains its existing loader-only libSystem load command, with no imported functions.

## Other reruns

The seven-trial core rerun also covers N-body, string/generic maps, append and sort, with matching outputs and unchanged allocation traffic/peak memory. The initial generic-map medians were 786.80 → 823.62 ms; a focused 15-trial shuffled repeat gives 830.04 → 820.69 ms with broad overlapping ranges, so it does not show a consistent slowdown direction. Both datasets are retained.

N-body and stencil Axon binaries are byte-identical to the lookup-winning version. Representative Mandelbrot/stencil/N-body measurements against Rust/Go are retained separately. In this run, four-worker stencil favours Rust (18.23 ms versus Axon 20.26 ms); other workload/worker combinations vary. These shared-host measurements do not establish a universal language ranking.

## Evidence

- [Append/JSON data and all three builds](.kernel-build/append-json-2026-10-25/regressions/measurements.json)
- [Map timing/checkpoint memory data](.kernel-build/append-json-2026-10-25/maps/measurements.json)
- [Bootstrap analysis](.kernel-build/append-json-2026-10-25/analysis.json)
- [Core before/after data](.kernel-build/append-json-2026-10-25/core/measurements.json), [generic-map confirmation](.kernel-build/append-json-2026-10-25/generic-confirmation.json), [representative compute](RESULTS-append-json-compute-linux-2026-10-25.md)
- Passed full suites: [macOS](.kernel-build/append-json-2026-10-25/tests-mac.log), [Linux ARM64](.kernel-build/append-json-2026-10-25/tests-linux-arm64.log), [x86-64 target](.kernel-build/append-json-2026-10-25/tests-linux-x86_64.log)
- [Commands and exit statuses](.kernel-build/append-json-2026-10-25/commands.json), [source/audit manifest](.kernel-build/append-json-2026-10-25/final-audit.json)

Frozen source snapshots and build outputs are retained under `.kernel-build/append-json-2026-10-25/`; the original pre-lookup snapshot remains under `.kernel-build/map-lookup-2026-10-25/baseline/`.
