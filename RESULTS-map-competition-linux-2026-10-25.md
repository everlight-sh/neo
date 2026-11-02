# Axon map memory and speed versus Rust/Go — 2026-10-25

Axon wins peak process memory and the combined timed map-operation sequence in all four tested nonempty cohorts (100k/1M entries, growing/preallocated). Rust remains faster for the initial lookup-only phase at 1M entries; this is not a claim that every map operation wins.

The target is the standard byte/string map (`std:bytesmap`, also used by `std:collections` StringMap). The generic `HashMap<K,V>` fallback is a different representation and still has higher footprint. No DB/application sources or existing competitor implementations were changed.

## Matched workload and controls

All maps own decimal-string keys `str(i)` and values `str(7*i)`. Each trial inserts N entries, validates/reads all entries, updates every value to `str(11*i)`, validates/reads all again, deletes every even key, then verifies both remaining values and deleted-key misses. Every phase checks count/checksum against the same independent model. Rust uses `std::collections::HashMap<String,String>` and Go uses built-in `map[string]string`. Rust reads borrowed strings; Go reads immutable string values; Axon returns owned byte values. These are concrete standard-container implementations with different layouts and hashing strategies, not identical internal data structures.

Both initially empty/growing and table-reserved constructors are measured. Axon’s unchanged original layout received only a reservation constructor adapter before the baseline was frozen. All original compiler/runtime/library sources are preserved, including hashes before that adapter. Keys/values are not pre-generated, interned or replaced with integer IDs. Formatting, hashing, validation and value parsing remain inside phase timers. The three workload sources are byte-identical between baseline and final runs.

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs/6 GiB; maps restricted to guest CPU 0. Rust 1.98.1 (`-O`, fat LTO, one codegen unit), Go 1.25.1 (`CGO_ENABLED=0`, `GOMAXPROCS=1`), Clang 18.1.3. Two warmups and nine measured trials, shuffled implementation order each round. The physical host is shared; raw ranges and paired trial data are retained. Performance on native x86 or other map libraries is not established.

“Timed sequence” sums insertion, three validated read passes, update and deletion. It excludes startup, checkpoint I/O/sampling, the explicit Go GC checkpoint, and final map destruction. Ordinary GC during timed Go operations is included. A checkpoint keeps the map live while `/proc/PID/status` VmHWM/RSS and smaps PSS are read. “Steady RSS” is after the first read pass; Go explicitly runs `runtime.GC()` first, while Rust/Axon have no GC. Both natural insert memory and post-GC steady memory are retained separately. RSS is whole-process residency, not a measurement of map payload alone.

## Aggregate results

Medians; peak is lifecycle VmHWM, including updates/deletion, not just insertion.

| Entries | Capacity mode | Implementation | Timed sequence ms | Trial range ms | Peak RSS MiB | Steady RSS MiB |
|---:|---|---|---:|---:|---:|---:|
| 100,000 | grow | Axon before | 80.81 | 67.54–88.27 | 10.96 | 9.03 |
| 100,000 | grow | Axon after | 50.55 | 46.83–57.20 | 6.62 | 6.50 |
| 100,000 | grow | Rust | 67.06 | 56.96–79.09 | 14.17 | 13.61 |
| 100,000 | grow | Go | 57.69 | 47.37–59.01 | 11.25 | 10.88 |
| 100,000 | reserved | Axon before | 79.04 | 71.32–86.72 | 9.12 | 9.00 |
| 100,000 | reserved | Axon after | 46.56 | 42.53–50.79 | 5.25 | 5.12 |
| 100,000 | reserved | Rust | 63.63 | 60.52–87.61 | 13.62 | 13.62 |
| 100,000 | reserved | Go | 52.34 | 45.96–59.05 | 11.00 | 8.75 |
| 1,000,000 | grow | Axon before | 1989.21 | 1874.91–2083.82 | 87.16 | 86.16 |
| 1,000,000 | grow | Axon after | 1164.20 | 1066.71–1211.52 | 64.66 | 49.66 |
| 1,000,000 | grow | Rust | 1383.52 | 1266.17–1405.88 | 204.48 | 160.48 |
| 1,000,000 | grow | Go | 1499.44 | 1386.51–1557.38 | 128.25 | 123.75 |
| 1,000,000 | reserved | Axon before | 1977.26 | 1947.55–2129.92 | 71.16 | 70.16 |
| 1,000,000 | reserved | Axon after | 1062.72 | 1020.05–1113.95 | 57.16 | 56.16 |
| 1,000,000 | reserved | Rust | 1176.41 | 1145.28–1237.24 | 160.50 | 160.50 |
| 1,000,000 | reserved | Go | 1337.84 | 1299.71–1372.33 | 125.12 | 98.25 |

At 1M growing entries, Axon’s insertion peak falls **86.16 → 64.66 MiB** and steady RSS falls **86.16 → 49.66 MiB**. Lifecycle peak falls **87.16 → 64.66 MiB**; the baseline reaches a slightly higher peak during later updates. Preallocation lowers final peak to **57.16 MiB**. Retained caches depend on allocation order, so preallocation does not guarantee lower steady RSS.

The growing 1M timed sequence improves **1,989.21 → 1,164.20 ms**. Relative to standard Rust and Go containers, final Axon is **1.19× / 1.29×** as fast on this complete timed sequence; preallocated Axon is **1.11× / 1.26×**. Paired-bootstrap 95% intervals over nine trials are about 1.16–1.19× versus Rust and 1.26–1.35× versus Go for the growing case; these describe this local sample, not production guarantees.

## Individual 1M phases

Medians in milliseconds; the read phases include number parsing and value validation. Aggregate medians above are computed per full trial, so they need not equal the sum of these individual medians.

| Capacity mode | Implementation | Insert | Initial lookup | Update | Updated lookup | Delete half | Remaining/miss lookup |
|---|---|---:|---:|---:|---:|---:|---:|
| grow | Axon before | 352.92 | 389.54 | 387.44 | 383.94 | 167.19 | 302.94 |
| grow | Axon after | 326.29 | 215.22 | 205.43 | 214.09 | 54.22 | 147.34 |
| grow | Rust | 420.16 | 166.58 | 288.12 | 170.92 | 143.95 | 147.94 |
| grow | Go | 414.18 | 275.48 | 268.83 | 269.54 | 109.18 | 155.95 |
| reserved | Axon before | 406.54 | 373.46 | 384.45 | 373.85 | 162.00 | 289.64 |
| reserved | Axon after | 266.77 | 202.59 | 198.89 | 204.76 | 52.25 | 136.77 |
| reserved | Rust | 297.21 | 159.70 | 275.14 | 162.64 | 141.61 | 141.64 |
| reserved | Go | 287.53 | 266.45 | 258.79 | 263.22 | 107.69 | 152.64 |

**Remaining speed gap:** initial lookup at 1M growing entries is **Axon 215.22 ms, Rust 166.58 ms, Go 275.48 ms**. Reserved lookup is **202.59 / 159.70 / 266.45 ms**. Rust’s lookup advantage remains. At 100k entries initial Axon/Rust lookups are effectively tied; Go also wins or ties some 100k update measurements. Axon’s wins here are overall timed sequence and memory, not universal per-operation superiority.

## Changes in Axon

- Compact bucket metadata: two adjacent packed offset words plus a control/fingerprint byte, **17 bytes per capacity slot** instead of 24. Keeping related offsets together avoids independent SoA metadata cache-line reads. Full SipHash-2-4 still selects buckets; fingerprints only filter comparisons, and full keys are checked. Rehashing hashes arena ranges without copying keys.
- Power-of-two bucket masking, tombstone-preserving probing, and 7/8 occupancy threshold. Existing empty/binary keys, replacement, deletion, explicit/automatic compaction and alias/value semantics remain covered. The preexisting checked **2-GiB byte-arena limit** remains.
- Pure scalar/unmanaged-result array consumers borrow without disabling a later final ownership transfer. Escaping-array results, effectful/external calls and explicit move parameters remain conservative. New alias/allocation checks exercise this through 100k elements.
- Small nonrecursive pure helpers inline before LLVM’s cost model so bounds, value lifetimes and cleanup can simplify. Checked arithmetic remains enabled.
- Linear-time decimal integer formatting, guarded wrapping inside integer parsing, and checked little-endian word loads. SipHash’s independent known-answer vectors and numeric oracles still pass.
- The large-buffer cache retains one block of at most **8 MiB**. Larger released buffers are unmapped, avoiding retention of old table generations. The representative 8-MiB stencil buffers still reuse the cache; repeated buffers larger than 8 MiB may incur extra mapping work. Smaller pools are separate, so this is not a total-RSS limit.

The compact map remains specialized for owned byte keys/values. The generic 1M-key owned-byte `HashMap<K,V>` regression still peaks at **285.61 MiB**; that fallback is not now a compact representation. Default compatibility seeds remain deterministic; use the existing kernel-random constructor for untrusted keys. No weakened hash or benchmark-specific integer-key shortcut was introduced.

## Tests, portability and regressions

- **macOS ARM64 and Linux ARM64:** full `axon test` passed, each with **88 Python unit tests and 28 native/documentation cases**, plus the complete integration suite. This includes independent map models, numeric/Unicode/codec oracles, network/crypto/TLS checks, compiler/optimizer differential cases and existing application regressions.
- Added scalar-result borrow safety/allocation checks, escaped-array alias isolation, explicit move/effect exclusions, empty/NUL/long byte keys, every word-tail alignment, missing keys, deletion, aliases and compaction.
- **x86-64 Linux under QEMU:** unit/native cases and new map models plus language/SipHash checks pass. This is emulated correctness evidence, not native x86 performance evidence.
- **Freestanding:** the actual measured final map executable passes import/ELF audits and runs both 1M-entry modes with all seven checkpoints in a root containing only that executable. No libraries, shell, devices or data files are present. Linux remains static, C-free, with no CRT, ELF interpreter, undefined symbols or shared-runtime dependencies. Python/LLVM remain build tools. macOS retains its mandatory libSystem loader command while importing no functions.
- Example/competitor workload hashes are preserved. Reproducible compiler-source archives and final source hashes are retained with this report.

Fresh four-worker compute regressions: **N-body Axon 3.58 ms / Rust 4.48 / Go 5.72; stencil 11.32 / 14.18 / 16.95**. Append/sort behavior remains close to the preserved compiler. The unchanged legacy 1M string-map workload improves to **511.27 ms, 64.66 MiB peak RSS**. The separate million-document JSON workflow measures **Axon 267.98 ms, previous Axon 303.88, Rust 406.73, Bun 363.12**. These separate workloads have different timing boundaries and should not be substituted for the matched map table.

## Evidence and reproduction

All evidence: `.kernel-build/map-competition-2026-10-25/`.

- `baseline-original-sources.json`, `baseline/sources.json`: preserved source hashes, before and after the reservation adapter.
- `baseline-measured/`: first five-run Axon/Rust/Go measurement before optimization.
- `final/measurements.json`: all nine-run phase/memory samples, compiler versions, exact commands, workload and binary hashes.
- `analysis.json`, `analyze.py`: aggregate statistics and reproducible paired bootstrap calculation.
- `mac-tests.log`, `linux-tests.log`, `x86-native.log`, `x86-model.log`, `x86-language.log`, `empty-root.log`: validation evidence.
- `core-regressions/`, `final-runs.json`, compute/JSON reports: preserved-compiler and cross-language regressions.
- Diagnostic candidates and an abandoned layout that caused excess copying are retained separately; they do not contribute final measurements.

```sh
python3 bench/maps/run.py --baseline .kernel-build/map-competition-2026-10-25/baseline --output /tmp/axon-map-rerun --include-after --sizes 0 100000 1000000 --repeats 9
./axon test
python3 tests/map_freestanding.py --binary /tmp/axon-map-rerun/Axon-after
```

The benchmark command requires native Linux. The empty-root command additionally requires root; x86 emulation is tested separately. This establishes wins for these standard containers and workloads, not every possible map/key type, alternative Rust/Go map implementation, concurrent workload or production service.
