# Axon core benchmarks and regression check — 2026-10-27

**The rerun is not regression-free.** The independent repeat confirms slower small string-map operations and million-key deletion. Generic `HashMap` peak RSS rises about 10%, while its workload runs faster. Compute and HTTP show no confirmed material timing regression against the interleaved frozen executable. JSON, append and sort improve.

This is the language compiler/runtime/standard library, with no Axon database or framework involved. Compiler/runtime/stdlib source remained unchanged throughout this request (85 files checked before and after). New code is benchmark tooling and Bun/Go counterparts.

Native ARM64 Linux on the Apple M1 Pro, ten-vCPU Linuxkit VM. Nine measured shuffled rounds plus two excluded warmups for the main process/map comparisons; a separate 15-round repeat after three warmups for suspect map cases. Current and frozen 2026-10-25 Axon executables run interleaved on the same VM. One-worker cases use CPU 0; four-worker compute uses CPUs 0–3. Timing and compilation/tests do not overlap. Binaries and timed inputs are VM-local.

Rust 1.98.1 optimized native executables from the prior run were verified against retained binary hashes and rerun unchanged. Go is rebuilt with 1.25.14; Bun is 1.3.13, matching the prior Bun version. Clang is 18.1.3. Axon remains statically linked with no interpreter, shared libraries or undefined imports.

## Current compute comparison

Median complete-process milliseconds, including launch/allocation/computation/destruction. Integer results agree exactly; N-body energies agree within relative tolerance 1e-9. Existing Axon/Rust/Go workload sources are unchanged. Layout, scheduling and implementations differ. Bun compute is a new standalone single-thread counterpart of the same equations; it is not reported as a four-worker implementation.

| Case | Workers | Previous Axon | Current Axon | Rust | Go | Bun |
|---|---:|---:|---:|---:|---:|---:|
| mandel-1200-1200-300 | 1 | 537.996 | 547.576 | 300.420 | 307.948 | 360.790 |
| stencil-1000000-20 | 1 | 95.410 | 92.250 | 35.047 | 36.215 | 303.276 |
| nbody-1024-3 | 1 | 17.859 | 17.780 | 17.793 | 8.464 | 73.052 |
| nbody-4096-10 | 1 | 838.632 | 816.967 | 810.981 | 296.341 | 672.375 |
| mandel-1200-1200-300 | 4 | 253.715 | 261.107 | 82.563 | 78.887 | — |
| stencil-1000000-20 | 4 | 37.096 | 37.343 | 16.528 | 21.958 | — |
| nbody-1024-3 | 4 | 5.926 | 5.988 | 7.097 | 4.012 | — |
| nbody-4096-10 | 4 | 211.905 | 210.988 | 213.872 | 79.261 | — |

Historical absolute rankings do not reproduce on this VM. For example, the exact frozen Mandelbrot executable now takes approximately 538 ms (one worker), versus 99.4 ms in the older Colima report; current Axon takes approximately 548 ms. That historical difference cannot be attributed to the new compiler code alone. The table above retains all current losses, and the paired old/current results isolate the incremental change in this environment.

## Dynamic JSON workflow

Whole-process milliseconds: construct varying JSON, fully parse it, read integer/UTF-8/array fields, checksum and release. This is not an isolated parser comparison. Rust uses serde_json::Value, Go uses encoding/json with map/slice values, Bun uses JSON.parse, and Axon uses its validated source/index representation. The Go counterpart is newly added; all outputs are checked against the same independent checksum.

| Documents | Previous Axon | Current Axon | Rust | Go | Bun |
|---:|---:|---:|---:|---:|---:|
| 10000 | 3.789 | 3.468 | 6.105 | 17.077 | 21.483 |
| 100000 | 27.008 | 23.752 | 49.539 | 163.684 | 59.621 |
| 1000000 | 259.936 | 229.303 | 484.275 | 1710.929 | 404.257 |

## Other library regression cases

Internal append/sort/map-and-checksum phase milliseconds; process launch and output are excluded.

| Case | Previous Axon | Current Axon | Previous peak RSS MiB | Current peak RSS MiB |
|---|---:|---:|---:|---:|
| append-1000000 | 8.119 | 5.020 | 13.656 | 13.871 |
| sort-1000000 | 125.733 | 114.434 | 7.625 | 7.977 |
| string-map-100000 | 16.945 | 15.503 | 4.000 | 4.000 |
| string-map-1000000 | 309.083 | 328.221 | 52.031 | 52.016 |
| generic-map-1000000 | 964.541 | 646.526 | 285.656 | 313.922 |

The initial nine-round complete 1M string-map case looked 6.2% slower, with broad overlapping ranges. The independent 15-round repeat instead measured 302.285 → 255.095 ms. Both datasets remain retained; a consistent slowdown direction is not established for that aggregate case. Its individual small-map and deletion regressions below are confirmed separately.

Generic `HashMap` is distinct from the compact byte/string map below. Generic-map peak RSS is 285.656 → 313.922 MiB (+9.9%). Its allocation requests drop from 10,549,982 to 3,000,019, while cumulative requested bytes increase from 336,491,465 to 358,357,023. Fewer requests do not imply lower peak memory.

## String-map comparison

Each phase includes decimal key construction and the ordinary public API. Reads validate every expected value and sum it; the final read has 50% misses after deleting even keys. Insert/update/delete and procfs memory pauses are outside read timers. Axon returns owned bytes; Rust/Go/Bun use their ordinary string APIs. Bun Map has no reserve API and is measured only in growing mode.

| Entries | Allocation | Implementation | Insert ms | Lookup ms | Update ms | Delete ms | Updated lookup ms | Mixed hit/miss lookup ms |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 100000 | growing | previous | 9.230 | 4.415 | 5.264 | 1.986 | 4.268 | 4.625 |
| 100000 | growing | Axon | 10.292 | 4.763 | 6.690 | 2.426 | 4.869 | 4.995 |
| 100000 | growing | Rust | 15.602 | 12.074 | 10.857 | 6.055 | 10.383 | 9.187 |
| 100000 | growing | Go | 13.444 | 7.151 | 7.120 | 3.918 | 8.075 | 7.495 |
| 100000 | growing | Bun | 24.282 | 24.270 | 18.958 | 8.772 | 21.408 | 19.231 |
| 100000 | reserved | previous | 6.457 | 4.335 | 6.083 | 2.081 | 4.739 | 5.211 |
| 100000 | reserved | Axon | 7.575 | 5.262 | 7.238 | 2.019 | 4.861 | 5.232 |
| 100000 | reserved | Rust | 13.481 | 10.919 | 11.239 | 6.593 | 11.409 | 10.387 |
| 100000 | reserved | Go | 9.323 | 9.933 | 8.432 | 3.798 | 8.780 | 7.735 |
| 1000000 | growing | previous | 202.956 | 99.455 | 178.755 | 41.757 | 105.063 | 116.227 |
| 1000000 | growing | Axon | 186.842 | 95.254 | 177.946 | 48.337 | 98.101 | 98.226 |
| 1000000 | growing | Rust | 416.193 | 254.579 | 266.988 | 127.835 | 254.890 | 164.250 |
| 1000000 | growing | Go | 362.670 | 255.839 | 229.508 | 116.502 | 246.675 | 217.936 |
| 1000000 | growing | Bun | 602.078 | 409.594 | 375.684 | 194.974 | 421.289 | 420.874 |
| 1000000 | reserved | previous | 252.679 | 97.176 | 175.942 | 41.360 | 108.062 | 117.607 |
| 1000000 | reserved | Axon | 214.499 | 87.668 | 171.723 | 49.140 | 95.289 | 96.140 |
| 1000000 | reserved | Rust | 318.070 | 257.547 | 245.164 | 128.485 | 255.266 | 168.965 |
| 1000000 | reserved | Go | 231.368 | 234.858 | 222.273 | 112.745 | 232.099 | 213.190 |

### Million-entry map memory

Steady RSS is sampled with the complete original map live; peak is median process high-water after the workflow. Go/Bun explicitly collect before the steady sample, outside timing. Empty-map cases are retained as correctness checks, not sub-microsecond performance claims. The Axon byte-map 2-GiB arena limit is unchanged.

| Allocation | Implementation | Steady RSS MiB | Peak RSS MiB |
|---|---|---:|---:|
| growing | previous | 36.137 | 52.031 |
| growing | Axon | 36.121 | 52.008 |
| growing | Rust | 160.613 | 204.426 |
| growing | Go | 133.660 | 134.156 |
| growing | Bun | 326.051 | 411.758 |
| reserved | previous | 34.109 | 35.824 |
| reserved | Axon | 34.098 | 35.812 |
| reserved | Rust | 160.609 | 160.609 |
| reserved | Go | 107.336 | 133.980 |

## Independent regression confirmation

Fifteen fresh measured shuffled pairs after three warmups. All full workflows and value/count checks still run. Slowdown is current/previous time. Intervals are paired-round bootstrap ratios of medians (20,000 resamples, 95%). Initial screening spans many cases; these unadjusted intervals describe this local sample, not a universal guarantee. A confirmed material screen requires >5% median slowdown and an interval wholly above 1.

| Case | Previous ms | Current ms | Change | Ratio interval | Result |
|---|---:|---:|---:|---|---|
| 100000-growing-insert | 9.236 | 10.509 | +13.8% | 1.058–1.216 | regression screen |
| 100000-growing-lookup | 4.650 | 5.019 | +8.0% | 0.976–1.153 | possible slowdown |
| 100000-growing-update | 5.984 | 6.990 | +16.8% | 1.078–1.414 | regression screen |
| 100000-growing-lookup_updated | 4.250 | 4.964 | +16.8% | 1.039–1.250 | regression screen |
| 100000-growing-delete | 1.774 | 2.369 | +33.5% | 1.127–1.553 | regression screen |
| 100000-growing-lookup_remaining | 4.737 | 5.208 | +9.9% | 1.052–1.154 | regression screen |
| 100000-reserved-insert | 5.665 | 6.820 | +20.4% | 1.061–1.320 | regression screen |
| 100000-reserved-lookup | 4.203 | 4.898 | +16.5% | 1.106–1.212 | regression screen |
| 100000-reserved-update | 5.457 | 6.474 | +18.7% | 1.021–1.536 | regression screen |
| 100000-reserved-lookup_updated | 4.221 | 4.678 | +10.8% | 1.050–1.145 | regression screen |
| 100000-reserved-delete | 1.781 | 2.040 | +14.5% | 1.075–1.255 | regression screen |
| 100000-reserved-lookup_remaining | 4.662 | 5.098 | +9.3% | 1.055–1.139 | regression screen |
| 1000000-growing-insert | 181.200 | 182.781 | +0.9% | 0.897–1.065 | no material change established |
| 1000000-growing-lookup | 92.725 | 85.803 | -7.5% | 0.857–0.962 | improvement |
| 1000000-growing-update | 170.233 | 171.045 | +0.5% | 0.947–1.046 | no material change established |
| 1000000-growing-lookup_updated | 101.623 | 93.391 | -8.1% | 0.830–0.947 | improvement |
| 1000000-growing-delete | 41.909 | 48.253 | +15.1% | 1.079–1.218 | regression screen |
| 1000000-growing-lookup_remaining | 109.873 | 96.724 | -12.0% | 0.796–0.944 | improvement |
| 1000000-reserved-insert | 235.299 | 216.580 | -8.0% | 0.778–1.016 | no material change established |
| 1000000-reserved-lookup | 97.462 | 92.370 | -5.2% | 0.865–0.984 | improvement |
| 1000000-reserved-update | 176.039 | 174.097 | -1.1% | 0.875–1.035 | no material change established |
| 1000000-reserved-lookup_updated | 109.101 | 98.126 | -10.1% | 0.843–0.954 | improvement |
| 1000000-reserved-delete | 41.621 | 47.745 | +14.7% | 1.057–1.236 | regression screen |
| 1000000-reserved-lookup_remaining | 114.414 | 98.308 | -14.1% | 0.810–0.953 | improvement |
| string-map-1000000 | 302.285 | 255.095 | -15.6% | 0.780–0.885 | improvement |

## HTTP runtime

Five fresh shuffled paired runs per scenario. Servers use CPU 0 or CPUs 0–3; load clients and sampler use CPUs 4–7. Each trial has a one-second warmup and two-second measurement. A validation-first Go client checks status, Content-Length and every complete Hello World body, and drains outstanding pipeline batches. All reported trials have zero I/O/response errors. Route validation also checks missing, stencil and N-body endpoints before load.

The first wrk attempt reported 39 timeout samples and was stopped. Its raw traces and partial measurements are preserved separately; none of its rates enter these tables. The accepted client protocol differs from historical wrk throughput, so compare versions within this run. These are closed-loop client-observed rates, potentially load-generator limited; latency percentiles are not measured. Bun retains one JavaScript handler loop in the four-CPU budget.

| Case | Previous Axon req/s | Current Axon req/s | Rust req/s | Go req/s | Bun req/s |
|---|---:|---:|---:|---:|---:|
| hello-1 | 261,558 | 261,509 | 196,814 | 87,434 | 113,025 |
| hello-4 | 576,606 | 561,581 | 485,714 | 233,903 | 118,982 |
| pipeline-1 | 1,863,480 | 2,023,817 | 726,309 | 112,263 | 24,597 |

| Case | Implementation | Server CPU µs/request | Peak aggregate PSS MiB |
|---|---|---:|---:|
| hello-1 | previous | 3.765 | 0.793 |
| hello-1 | Axon | 3.785 | 0.789 |
| hello-1 | Rust | 5.054 | 2.433 |
| hello-1 | Go | 11.370 | 12.109 |
| hello-1 | Bun | 8.801 | 53.299 |
| hello-4 | previous | 5.504 | 2.363 |
| hello-4 | Axon | 5.595 | 2.371 |
| hello-4 | Rust | 7.613 | 7.046 |
| hello-4 | Go | 14.477 | 18.551 |
| hello-4 | Bun | 8.518 | 54.521 |
| pipeline-1 | previous | 0.536 | 0.793 |
| pipeline-1 | Axon | 0.496 | 0.789 |
| pipeline-1 | Rust | 1.376 | 2.550 |
| pipeline-1 | Go | 8.906 | 12.121 |
| pipeline-1 | Bun | 40.631 | 52.998 |

## Validation and evidence

- 123 compiler unit tests pass in the native preparation workspace.
- Every compute/JSON/map run checks its output; every map phase checks complete counts and expected values.
- Actual measured current map, append and JSON executables pass execution in empty Linux roots containing only the executable.
- All current Axon executables pass undefined-symbol, ELF interpreter and shared-library audits. Python/LLVM remain build tools.
- Full source snapshots, exact binaries, build logs, tool versions, unfiltered samples, failed HTTP traces, bootstrap analysis and independent repeat are retained. No compiler/runtime/stdlib files were changed to obtain this rerun.

Artifacts: `.kernel-build/core-regression-2026-10-27/results/`. Main files: `measurements.json`, `analysis.json`, `confirmation/measurements.json`, `inventory.json`, `unit-tests.log`, `current-source/`, `baseline-source/`, `control-sources/` and `bin/`. Historical reports and artifacts remain unchanged.
