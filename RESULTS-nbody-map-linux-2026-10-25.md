# Axon N-body and map-memory improvements — 2026-10-25

Changes are in Axon’s compiler, runtime and standard library. The N-body example, existing collection workload and all Rust/Go/Bun competitor sources are unchanged. The final implementation remains C-free; Linux binaries have no CRT, imported functions, ELF interpreter or shared runtime libraries.

## What changed

- **General worker certification:** allocation-free scalar/record bodies, borrowed-array reads and nested numeric reductions can use the existing joined Linux shared-address workers. Allocating/managed/owned/effectful/recursive/unknown paths remain excluded. A conservative work estimate keeps cheap record loops sequential when worker startup would cost more. There is no N-body-name special case and no force/precision/step-count change.
- **Disjoint record-field moves:** independently consumed managed fields can transfer without copying both buffers. The remaining owner has each transferred field cleared; borrowed records and later alias/whole-record uses retain copies as needed. This improves ordinary multiple-buffer records, including the byte map.
- **Compact standard byte map:** `std:bytesmap` stores a 64-bit SipHash and four i32 offsets per 24-byte slot, with owned key/value bytes packed into one arena. `std:collections` retains the `map_empty/get/put` call API using this representation. Lookup returns independently owned bytes. The generic `HashMap<K,V>` remains available for arbitrary supported key/value types; its state plane is now u8.
- **Large-buffer retention:** allocations larger than 1 MiB share one reusable buffer, evicted on a different large request or another large release. This avoids retaining old table generations across size classes while preserving same-size repeated computation buffers. Smaller free lists and 1 MiB worker stacks remain reusable. The bound is one block, not a fixed byte/RSS cap.

Byte-map keys/values may contain NULs or be empty. Growing updates/deletion track discarded bytes; compaction is automatic above the documented thresholds and is also explicit. The checked byte-arena limit is 2,147,483,647 bytes per map. Value/alias semantics are preserved. See [the language contract](docs/language-v01.md) for APIs and limits.

## N-body: focused before/after and cross-language matrix

Native ARM64 Linux, Apple M1 Pro/Colima, 8 vCPUs and 6 GiB. Two warmups, then **11 measured runs per row**, with seeded shuffled implementation order. One worker is pinned to guest CPU 0; four workers to guest CPUs 0–3. AXON_THREADS/RAYON_NUM_THREADS/GOMAXPROCS match that budget. CPU affinity inside the VM does not pin physical host cores; the shared host and startup overhead produce variation, especially at 1,024 bodies.

Timing includes process startup, initialization, every simulation step, final energy computation and shutdown. All energies agree within relative tolerance 1e-9. Softening, time step, body count, interactions, sqrt/division precision and algorithms in the application sources are unchanged. Axon and Rust/Go still use their existing different data layouts and runtimes. These are implementation comparisons, not a universal language ranking.

| Bodies | Steps | Workers | Previous Axon ms | Final Axon ms | Rust ms | Go ms |
|---:|---:|---:|---:|---:|---:|---:|
| 1,024 | 3 | 1 | 8.06 | 7.40 | 9.61 | 13.00 |
| 1,024 | 3 | 4 | 7.65 | 5.21 | 6.92 | 9.46 |
| 2,048 | 10 | 1 | 49.36 | 50.76 | 69.72 | 82.30 |
| 2,048 | 10 | 4 | 24.30 | 22.21 | 23.04 | 31.84 |
| 4,096 | 10 | 1 | 189.20 | 189.54 | 268.07 | 309.90 |
| 4,096 | 10 | 4 | 65.65 | 60.22 | 78.16 | 96.86 |

Axon beats Rust’s median in all six tested N-body configurations. Some single-worker timings versus the previous Axon build are slightly slower, so this is not a claim that every Axon configuration improved.

Four-worker run ranges and aggregate process/descendant CPU time:

| Bodies × steps | Implementation | Wall median ms | Wall min–max ms | Median CPU ms |
|---|---|---:|---:|---:|
| 1,024 × 3 | before | 7.65 | 3.80–10.13 | 10.37 |
| 1,024 × 3 | after | 5.21 | 3.57–8.63 | 7.69 |
| 1,024 × 3 | Rust | 6.92 | 5.65–9.84 | 10.42 |
| 1,024 × 3 | Go | 9.46 | 7.19–15.86 | 11.97 |
| 2,048 × 10 | before | 24.30 | 20.04–38.92 | 62.92 |
| 2,048 × 10 | after | 22.21 | 18.69–41.17 | 58.00 |
| 2,048 × 10 | Rust | 23.04 | 20.29–49.62 | 75.86 |
| 2,048 × 10 | Go | 31.84 | 26.32–53.19 | 89.77 |
| 4,096 × 10 | before | 65.65 | 56.77–71.86 | 213.05 |
| 4,096 × 10 | after | 60.22 | 54.78–73.32 | 201.59 |
| 4,096 × 10 | Rust | 78.16 | 73.13–86.41 | 286.73 |
| 4,096 × 10 | Go | 96.86 | 90.32–111.99 | 325.48 |

## Map memory and collection regressions

The existing string-map workload inserts decimal byte keys/values, validates every lookup and checksums the parsed values. Before/after run the exact same source. The additional generic-map workload performs the same operations through `HashMap<bytes,bytes>` directly. This distinguishes the compact byte-specific representation from improvements to the general map.

Two warmups and 11 measured runs, shuffled before/after order; one worker on guest CPU 0. “Phase” includes the collection computation/checksum and scope cleanup, excluding CLI printing/startup. “Process” also includes GNU time/taskset startup and shutdown. Peak RSS is the maximum GNU-time process high-water mark across measured runs; it is not Docker working set or PSS. Map runs have one process worker.

| Workload | Rows | Build | Median phase ms | Median process ms | Maximum peak RSS MiB |
|---|---:|---|---:|---:|---:|
| string-map | 10,000 | before | 3.548 | 5.964 | 2.88 |
| string-map | 10,000 | after | 1.866 | 4.026 | 1.38 |
| string-map | 100,000 | before | 106.200 | 113.704 | 47.25 |
| string-map | 100,000 | after | 40.048 | 43.098 | 10.96 |
| string-map | 1,000,000 | before | 1447.624 | 1565.129 | 377.62 |
| string-map | 1,000,000 | after | 814.750 | 819.022 | 86.16 |
| generic-map | 1,000,000 | before | 1290.274 | 1317.932 | 377.62 |
| generic-map | 1,000,000 | after | 1300.500 | 1318.418 | 285.61 |
| append | 1,000,000 | before | 6.513 | 9.788 | 15.62 |
| append | 1,000,000 | after | 5.864 | 8.685 | 13.66 |
| sort | 1,000,000 | before | 118.634 | 121.404 | 7.62 |
| sort | 1,000,000 | after | 119.968 | 122.813 | 7.62 |

**string-map, 1M rows: peak RSS falls 77.2% (377.62 → 86.16 MiB).**

**generic-map, 1M rows: peak RSS falls 24.4% (377.62 → 285.61 MiB).**

The compact byte map also reduces operation time. Generic-map and sort throughput are roughly unchanged in this run; no generic-map speedup is claimed. Maps retaining arbitrary owned generic values still have substantially higher footprint than the byte arena.

Separate instrumented executables count requested allocation traffic; counters are optimized out of the timing builds. Requested bytes accumulate over the whole run and are not live memory.

| 1M-row map | Build | Allocation requests | Cumulative requested bytes |
|---|---|---:|---:|
| string-map | before | 13,017,992 | 379,970,431 |
| string-map | after | 4,000,040 | 142,900,693 |
| generic-map | before | 13,017,992 | 379,970,431 |
| generic-map | after | 13,017,992 | 350,610,359 |

## Other benchmarks rerun

The unchanged mixed-compute harness separately reruns Mandelbrot, stencil and N-body with 11 measured runs after one warmup. This is a different measurement block from the focused matrix above; inspect both rather than comparing absolute times between blocks.

[Compute report](RESULTS-nbody-map-compute-linux-2026-10-25.md) · [JSON report](RESULTS-nbody-map-json-linux-2026-10-25.md) · [HTTP report](RESULTS-nbody-map-http-linux-2026-10-25.md)

Separate mixed-compute rerun (median process ms):

| Workload | Workers | Axon | Rust | Go |
|---|---:|---:|---:|---:|
| stencil | 1 | 22.10 | 37.13 | 41.26 |
| stencil | 4 | 12.10 | 14.71 | 17.20 |
| nbody | 4 | 3.73 | 4.49 | 6.11 |
| mandel | 4 | 50.33 | 74.49 | 77.67 |

The focused and mixed N-body reruns use byte-identical final Axon executables; absolute timings differ between blocks on this shared host.

The first allocator attempt immediately unmapped large blocks. It reduced footprint but regressed stencil, so it was replaced before accepting final results. Initial measurements/reports and the exact old runtime source are retained under this task’s evidence directory and listed in `superseded-attempts.json`. The final cache restores repeated-buffer reuse; final compute results cover stencil as a regression check.

The first final-code JSON matrix used seven runs and showed large timing variation at 1M documents. It is retained as `json-seven-run-report.md`/`json-final.log`. One predeclared 15-run diagnostic rerun uses the same implementation and comparators; its report is linked above. Neither run is discarded and no JSON implementation change or new JSON speedup is claimed. HTTP uses three 3-second runs after one-second warmups, with the existing protocol/worker-budget limits documented in its report.

JSON 1M-document process times (all binaries have identical SHA-256 hashes across these two matrices):

| Implementation | First 7-run median ms | Follow-up 15-run median ms | Follow-up min–max ms |
|---|---:|---:|---:|
| Axon | 401.60 | 307.15 | 305.33–349.61 |
| Axon previous | 319.70 | 307.16 | 306.17–324.32 |
| Rust | 434.27 | 404.35 | 398.13–432.55 |
| Bun | 371.60 | 357.71 | 348.88–394.42 |

The follow-up puts Axon and the preserved prior JSON implementation at essentially the same median. Both sets of raw values remain available; this is evidence of measurement variability rather than a claimed JSON optimization.

## Tests and dependency audits

Final results: **80 Python unit tests and 22 native/documentation cases pass** on native macOS ARM64, native Linux ARM64 and Linux x86-64 under QEMU. The complete native Linux suite also passes, including the unchanged application/database clients, 31 TSX transformer tests and 1,000 SSR inputs with one/four workers.

New checks cover:

- Byte-map dictionary model through 100,000 operations, empty/binary keys, aliases, repeated growth, larger/smaller overwrites, deletion/tombstones and automatic/explicit compaction.
- Two independently growing owned record fields, aliases, later whole-record reuse, conditional transfers, nested managed records and geometric allocation traffic.
- Worker certification accepts numeric records/borrowed reads and rejects nested allocation, mutation, managed projections, owned parameters, effects and recursion/unknown calls.
- N-body versus an independent Python model with one/four workers, odd sizes and the 1,024-element dispatch boundary, plus genuine Linux clone EAGAIN injection and sequential fallback.
- Large-cache exact-size reuse, replacement, mismatched-size eviction, survival across small allocations and reset in forked children.
- Existing allocation complexity, compiler arithmetic/fuzz, SIMD/tail/overflow/fallback, file/socket/resource, DNS/HTTP/TLS/crypto, cache/package/formatter/LSP, storage/aggregation and SSR regressions.

The final ARM64/x86-64 kernel/crypto/TLS binaries pass `nm -u` and ELF audits. Native empty-root checks run N-body with four workers and the 1M-key byte map with only the executable; the HTTP executable also passes its empty-root suite. Core/RNG/futex/SHA need only the executable, and TLS needs only executable plus explicit trust-anchor data. No libc/libSystem functions or shared runtime libraries are imported on Linux. Python/LLVM remain agreed build dependencies.

**macOS retains the mandatory libSystem load command with zero function imports.** TLS remains experimental/unaudited and raw fork still has its documented unsafe inherited-heap boundary; this task does not change those limitations. Native x86-64 performance and remote CI execution are not established by emulated correctness tests.

## Reproduction and artifacts

Run from the Axon repository in the native ARM64 Linux benchmark environment:

```sh
./axon test
python3 tests/bytesmap_smoke.py
python3 tests/nbody_worker_smoke.py
python3 bench/core/nbody_map.py --baseline .kernel-build/nbody-map-2026-10-25/baseline --output .kernel-build/nbody-map-rerun --repeats 11
python3 bench/usability/compute.py --repeats 11 --report RESULTS-compute-rerun.md
python3 bench/json/run.py --repeats 15 --baseline .kernel-build/language-v01/baseline-library --report RESULTS-json-rerun.md
python3 bench/http/compare.py --duration 3s --warmup 1s --repeats 3 --threads 4 --scenarios hello-64 pipeline-16 hello-one-worker --report RESULTS-http-rerun.md
```

Evidence is under `.kernel-build/nbody-map-2026-10-25/`:

- `baseline/sources.json`: 61 preserved previous-build files, verified unchanged.
- `final-core-sources.json`: SHA-256 of 60 final compiler/runtime/standard-library sources.
- `bench-final/measurements.json`: every focused timing/checksum/CPU/RSS sample, source/binary hash, allocation profile, commands, tool versions and ELF audit.
- `compute-final.log`, `json-final.log`, `json-diagnostic.log`, `http-final.log`: additional benchmark directories and per-matrix evidence.
- `linux-release-final.log`, `macos-release-final.log`, `x86-release-final.log`, `x86-bytesmap-final.log`, `x86-nbody-final.log`: final test logs.
- `audit-final/manifest.json` and `audit-final.log`: final static/empty-root dependency evidence.
- `release-verification.json`: reproducible source bundles, full manifest verification and extracted-bundle build/run.

All 45 previously recorded application/example source hashes remain unchanged. `/axon/...` paths in raw data refer to this repository’s Linux container mount. The release bundle is `axon-0.1.0-dev.1-a.tar.gz` inside this evidence directory; it contains compiler/runtime/stdlib/docs and excludes application examples.
