# Axon lookup and memory benchmark — 2026-10-25

The measured map programs and Rust/Go sources are unchanged. Native ARM64 Linux on the local Apple M1 Pro/Colima VM (8 vCPUs, 6 GiB), one worker pinned to CPU 0. Fifteen measured trials after two warmups for each size and allocation mode; implementation order is shuffled each round. Tests and builds ran before the accepted timing run. This is a shared physical host, so results describe these workloads and this machine.

Each read phase performs one million probes and validates the values. Lookup includes decimal key construction, the normal public map API, integer parsing, presence checks, expected-value checks and accumulation. Insert/update/delete, startup, destruction, checkpoints and memory sampling are outside the lookup timer. The final read phase contains 50% misses after deleting even keys. Axon still returns independently owned bytes; Rust and Go read their usual string values.

## Lookup phases at one million entries

| Allocation | Phase | Axon before ms | Axon after ms | Rust ms | Go ms | Rust / Axon speedup |
|---|---|---:|---:|---:|---:|---:|
| Growing | lookup | 204.72 | 99.94 | 161.93 | 268.29 | 1.62× |
| Growing | lookup_updated | 206.30 | 107.59 | 161.11 | 260.78 | 1.50× |
| Growing | lookup_remaining | 137.69 | 111.09 | 143.77 | 154.57 | 1.29× |
| Reserved | lookup | 203.81 | 99.34 | 162.78 | 262.04 | 1.64× |
| Reserved | lookup_updated | 204.10 | 102.92 | 162.80 | 261.74 | 1.58× |
| Reserved | lookup_remaining | 139.12 | 108.52 | 147.03 | 154.63 | 1.35× |

Ratios below use Rust elapsed time divided by Axon elapsed time; values above 1 favour Axon. The intervals are a paired-round bootstrap of the ratio of medians (20,000 resamples), not a claim about other hardware.

| Allocation | Phase | Speedup | Bootstrap 95% interval | Axon wins / 15 rounds |
|---|---|---:|---:|---:|
| Growing | lookup | 1.62× | 1.59–1.69× | 15 |
| Growing | lookup_updated | 1.50× | 1.46–1.58× | 15 |
| Growing | lookup_remaining | 1.29× | 1.25–1.35× | 15 |
| Reserved | lookup | 1.64× | 1.60–1.68× | 15 |
| Reserved | lookup_updated | 1.58× | 1.51–1.63× | 15 |
| Reserved | lookup_remaining | 1.35× | 1.31–1.41× | 15 |

## Memory at one million entries

All values are MiB. Steady RSS is sampled with the full original map alive; peak RSS is the process high-water mark after all phases. Go explicitly collects at its steady checkpoint, outside the timer. Axon byte/string maps retain their existing 2 GiB arena limit and value/alias semantics; the separate generic HashMap implementation is not the subject of the memory claim.

| Allocation | Implementation | Steady RSS | Peak RSS |
|---|---|---:|---:|
| Growing | Axon before | 49.66 | 64.66 |
| Growing | Axon after | 36.04 | 52.03 |
| Growing | Rust | 160.48 | 204.48 |
| Growing | Go | 128.25 | 129.25 |
| Reserved | Axon before | 56.16 | 57.16 |
| Reserved | Axon after | 34.00 | 35.62 |
| Reserved | Rust | 160.50 | 160.50 |
| Reserved | Go | 98.25 | 125.12 |

## Complete map cases

Medians of the sum of timed phases per trial; sampling, GC checkpoint, startup and destruction remain excluded. Empty-map correctness cases are in the raw data.

| Entries | Allocation | Implementation | Insert ms | Lookup ms | Update ms | Delete ms | Whole workflow ms |
|---:|---|---|---:|---:|---:|---:|---:|
| 100,000 | Growing | Axon before | 13.78 | 9.47 | 9.68 | 3.07 | 53.59 |
| 100,000 | Growing | Axon after | 9.24 | 5.05 | 7.23 | 2.30 | 34.76 |
| 100,000 | Growing | Rust | 17.65 | 9.98 | 16.52 | 8.94 | 72.30 |
| 100,000 | Growing | Go | 16.70 | 12.02 | 10.92 | 4.69 | 63.21 |
| 100,000 | Reserved | Axon before | 12.38 | 10.31 | 10.14 | 3.24 | 53.97 |
| 100,000 | Reserved | Axon after | 7.14 | 5.02 | 7.19 | 2.16 | 34.11 |
| 100,000 | Reserved | Rust | 18.23 | 10.62 | 17.79 | 9.37 | 79.91 |
| 100,000 | Reserved | Go | 14.42 | 14.00 | 12.43 | 5.64 | 72.94 |
| 1,000,000 | Growing | Axon before | 298.77 | 204.72 | 201.49 | 53.08 | 1100.98 |
| 1,000,000 | Growing | Axon after | 197.43 | 99.94 | 175.37 | 42.92 | 730.77 |
| 1,000,000 | Growing | Rust | 414.30 | 161.93 | 283.36 | 139.91 | 1304.75 |
| 1,000,000 | Growing | Go | 406.95 | 268.29 | 258.60 | 109.52 | 1469.97 |
| 1,000,000 | Reserved | Axon before | 268.94 | 203.81 | 200.91 | 53.23 | 1075.06 |
| 1,000,000 | Reserved | Axon after | 233.99 | 99.34 | 172.88 | 43.09 | 760.19 |
| 1,000,000 | Reserved | Rust | 315.60 | 162.78 | 284.05 | 141.76 | 1226.42 |
| 1,000,000 | Reserved | Go | 302.97 | 262.04 | 265.43 | 112.90 | 1357.75 |

## Implementation and correctness

The core byte/string map packs keys and values up to seven arbitrary bytes into its existing two-word bucket. Longer byte strings keep their owned arena path. Inline key matching reads that word directly and uses disjoint empty/tombstone sentinels; compaction preserves probe chains. Full seeded SipHash-2-4 is retained, including the published 64-vector suite.

The LLVM backend recognises a short little-endian word-to-byte comprehension and emits one unaligned store into its fresh allocation, guarded to lengths 1–8. Empty and longer arrays retain the ordinary path; physical allocations already have at least 16 bytes. The resulting arrays remain owned. Integer formatting packs two digits per division before allocating, and short decimal parsing validates ASCII lanes together. Signed, long and malformed numbers keep the checked general path and the same error positions.

The allocator and runtime sources are unchanged by this task. Experimental allocator attributes were removed after a raw pointer-reuse test failed. No allocation-family/noalias assumptions from that experiment remain. No benchmark-specific key type, weaker hash, changed competitor workload or borrowed-return API was introduced.

## Validation and standalone runtime

`./axon test`: 90 Python unit tests, 30 native/document cases and the full integration suite passed on native ARM64 macOS and Linux. The suite includes HTTP 1/4 workers, TSX/React equivalence, JSON fuzzing, DNS, crypto/TLS, ownership, compiler cache confidence, compute, persistence, crash recovery and aggregation. Linux x86-64 under QEMU passed the 90-unit/30-native suite plus the new byte-array, map and integer model checks.

New checks cover 12,433 binary/sign/overflow/error-position integer vectors, 519 integer-formatting vectors, short-array lengths 0–17 and larger fallbacks, signed words, arbitrary binary inline keys/values, empty values, overwrite transitions, retained aliases, long keys and compacted collision/tombstone chains. Two generated compiler-source bundles have identical SHA-256 hashes.

The actual measured Linux executable also ran both one-million-entry modes in a chroot containing only that executable. Its ELF has no interpreter, shared-library dependency or undefined symbol. Python/LLVM remain build tools. macOS retains its existing loader-only libSystem dependency and has no imported functions.

## Evidence

- Measured runs, phase checksums, checkpoint RSS/PSS, source hashes and binary hashes: [.kernel-build/map-lookup-2026-10-25/final/measurements.json](.kernel-build/map-lookup-2026-10-25/final/measurements.json).
- Commands and exit statuses: [.kernel-build/map-lookup-2026-10-25/final-commands.json](.kernel-build/map-lookup-2026-10-25/final-commands.json).
- Passed full suites: [macOS ARM64](.kernel-build/map-lookup-2026-10-25/final-tests-mac-retry.log), [Linux ARM64](.kernel-build/map-lookup-2026-10-25/final-tests-linux-arm64-retry.log), [x86-64 target](.kernel-build/map-lookup-2026-10-25/final-tests-linux-x86_64.log).
- Full test logs and bootstrap analysis: `.kernel-build/map-lookup-2026-10-25/`.
- Frozen before/after compiler sources: `.kernel-build/map-lookup-2026-10-25/baseline/` and `source/`.
- Representative compute and JSON reruns: [compute](RESULTS-map-lookup-compute-linux-2026-10-25.md), [JSON](RESULTS-map-lookup-json-linux-2026-10-25.md); broader N-body/string/generic-map/append/sort before/after data: `.kernel-build/map-lookup-2026-10-25/core-regressions/measurements.json`.

All 45 example-source hashes, all four matched map workload/harness hashes and all 381 Go agent source hashes are unchanged.

## Regression results and retained trade-offs

The seven-trial core rerun gives 1M string-map insert/read work 546.25 → 301.67 ms and generic-map work 1018.70 → 830.79 ms. Generic-map peak RSS remains 285.61 MiB. Sort is 110.37 → 109.88 ms. The larger single-worker N-body case is 183.03 → 182.40 ms, with matching energies. The separate representative run retains Axon wins over Rust on Mandelbrot and stencil; the small four-worker N-body medians tie at 3.70 ms.

Two regressions remain visible. A focused 30-trial repeat (five warmups, shuffled before/after order, CPU 0, identical binaries and checksums) confirms the 1M-element append microbenchmark rising from 5.84 to 6.91 ms, about 18%. Its peak RSS stays 13.66 MiB. The complete 1M-document JSON workflow rises from 267.45 to 277.18 ms, about 3.6%; it remains ahead of Rust at 401.66 ms and Bun at 363.44 ms. These performance costs are not hidden by the lookup and memory wins. All correctness checks pass. Raw append repeats: `.kernel-build/map-lookup-2026-10-25/append-confirmation.json`.

## Binary footprints

| Implementation | Executable KiB |
|---|---:|
| Axon before | 70.76 |
| Axon after | 82.19 |
| Rust | 2153.34 |
| Go | 2255.22 |

Toolchain versions: rustc 1.98.1 (48a229cea 2026-09-01); go version go1.25.1 linux/arm64; Ubuntu clang version 18.1.3 (1ubuntu1).
