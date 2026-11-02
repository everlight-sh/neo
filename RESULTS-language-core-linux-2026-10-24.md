# Axon language-core validation — 2026-10-24

Implemented in the compiler, Axon runtime, standard library and development tools. Database and application/example source files were not changed. This is version `0.1.0-dev.1`, a development release with the limitations below.

## Implemented surface

| Area | Result |
|---|---|
| Types and errors | Specialized generic functions/records, tagged alternatives, exhaustive matches, Option/Result and scoped `?` propagation; owned, unit and empty-record payloads |
| Collections | Generic Vec and HashMap, SipHash-2-4, kernel-randomized seeds, bounded probing/tombstones, geometric growth, heapsort, efficient borrowed reads |
| Lifetimes | Affine scoped resources, borrowed and moved parameters, cleanup on normal/error results, conditional transfer and exactly-once custom destructors; private generational file/socket handles |
| Coordination | Bounded SPSC process channels, deadlines, cancellation and direct Linux futex waits; joined pure-computation workers |
| Networking | DNS A resolution with bounded compressed names and TCP fallback; seven HTTP methods, incremental bounded HTTP/1.1 body reads, strict framing and monotonic deadlines |
| Cryptography | Axon SHA-256/HMAC/HKDF, ChaCha20-Poly1305, X25519 and RSA verification; bounded DER/X.509 and experimental TLS 1.3 client |
| Packages and tooling | Namespaces/import aliases/privacy, deterministic local package locks and offline vendoring, structured/human diagnostics, formatter, stdio LSP completion/hover/definitions/symbols/formatting, reproducible source bundles |
| Language definition | [Development contract](docs/language-v01.md), migration/compatibility limits, executable documentation cases and native Linux CI configuration |

The detailed API, semantics and restrictions are defined in `docs/language-v01.md`. The release archive contains the compiler, runtime, standard library and documentation; application examples are excluded.

## Correctness and failure coverage

Final unit/native runs pass **76 Python tests and 19 native/documentation cases** on macOS ARM64, native Linux ARM64 and Linux x86-64 under QEMU. Full native ARM64 regression suites cover the existing applications as unchanged clients of the compiler, as well as the new language functionality.

Additional integration coverage includes:

- Independent Python map model across sizes through 100,000, all 64 official SipHash vectors in native code, binary/empty keys, tombstones, aliases and owned values.
- Allocation-complexity assertions at 1k/10k/100k: geometric append, one sort buffer and linear map traffic.
- Resource moves, use-after-move rejection, borrow/escape rejection, exactly-once custom destructors, repeated open/close, failed opens, scoped Result errors, cross-fork descriptor isolation, cancellation, deadlines and 10,000 ordered cross-process messages.
- DNS compression/CNAMEs, mismatched transactions/questions, pointer cycles, fragmented TCP fallback, truncation and timeouts; HTTP framing ambiguity, fragmented responses, all supported methods, chunk/trailer handling, bounded streaming and error paths.
- SHA/HMAC boundary cases through 1 MiB, HKDF, 16 independent AEAD cases and tag corruption, 16 independent X25519 exchanges, RSA signatures at actual key sizes 2048/2050/4096 and malformed signatures. OpenSSL is an independent test oracle only.
- X.509 malformed/truncated inputs, SAN/wildcard/time/critical-extension/EKU rules, intermediate chains, path length and CA key usage. TLS interoperability with an independent encrypted peer, one-byte fragmentation, tickets, close-notify, bad hostname/chain/signature, corrupt handshake/application tags, truncation, deadlines and authenticated KeyUpdate.
- Package tamper/cycle/version/source-hash checks, privacy/alias collisions, formatter literal/comment preservation, UTF-16 and unsaved-buffer LSP behavior, deterministic builds after relocation and cache/concurrent-build tests.
- Existing compiler differential/failure confidence runs, JSON accessors, compute/worker/vector/stencil checks, HTTP/SSR, and unchanged application/database regression clients. The SSR transformer suite has 31 tests and the renderer checks 1,000 inputs with one and four workers.

Native x86-64 performance has **not** been measured. The x86 correctness suite and static ELF audits run under QEMU; the native x86-64/ARM64 GitHub Actions workflow is configured but was not executed remotely in this session.

## Runtime dependency evidence

For final Linux ARM64 and x86-64 core, crypto, TLS and custom-resource executables, `nm -u` is empty and ELF inspection finds neither `INTERP` nor `NEEDED`. Linux programs contain no C source runtime, CRT, libc/libSystem function imports or shared runtime libraries. Compiler-emitted helpers such as memory copying are implemented in Axon. ARM64 atomics are emitted inline rather than linking compiler-rt helpers.

Empty-root checks execute core/RNG/futex and SHA-256 with only the executable present; TLS has only the executable and explicit certificate trust data. The measured HTTP server also runs from an otherwise empty filesystem. OpenSSL, Python, LLVM, Rust, Go and Bun are build/test/benchmark tools, not services or libraries loaded by Axon executables.

**macOS qualification:** no functions are imported, but Apple Silicon executables retain the mandatory libSystem load command. Thus the zero-loader-dependency result applies to Linux. All targets require their OS kernel. Python/LLVM remain compiler build dependencies as agreed.

## Collection benchmarks

Native ARM64 Linux on Apple M1 Pro/Colima, 8 vCPUs/6 GiB. Collections use CPU 0 and one Axon worker, two warmups, then seven measured runs, with seeded shuffled before/after order. The original implementation is preserved in the baseline source snapshot. The same unchanged call-level workload runs against both builds; outputs/checksums are verified.

“Phase” includes the collection operation, checksum and cleanup; it excludes CLI startup and printing. Whole-process wall includes launcher/time/taskset overhead and is shown separately. Sub-millisecond phase gains must not be confused with whole-process gains. Requested allocation bytes are cumulative traffic, not peak resident memory.

| Workload | N | Before phase ms | After phase ms | Before process ms | After process ms | After max RSS MiB |
|---|---:|---:|---:|---:|---:|---:|
| Append | 1,000 | 0.4937 | 0.0150 | 2.068 | 1.627 | 1.38 |
| Append | 10,000 | 44.8770 | 0.0962 | 46.882 | 1.917 | 1.38 |
| Append | 50,000 | 1161.5059 | 0.4181 | 1163.670 | 2.321 | 1.38 |
| Sort | 100 | 0.0264 | 0.0158 | 1.518 | 1.531 | 1.38 |
| Sort | 1,000 | 1.4029 | 0.0627 | 3.183 | 1.729 | 1.38 |
| Sort | 10,000 | 114.5445 | 0.7128 | 116.859 | 2.688 | 1.38 |
| String map insert + lookup | 100 | 0.2318 | 0.0493 | 1.812 | 1.761 | 1.38 |
| String map insert + lookup | 1,000 | 19.9413 | 0.3668 | 21.947 | 2.162 | 1.38 |
| String map insert + lookup | 5,000 | 515.8576 | 1.6421 | 518.456 | 3.438 | 1.50 |

Current-build scaling, also seven measured runs:

| Workload | N | Median phase ms | Median process ms | Max RSS MiB |
|---|---:|---:|---:|---:|
| Append | 100,000 | 0.735 | 3.400 | 1.75 |
| Append | 1,000,000 | 6.458 | 11.118 | 15.62 |
| Sort | 100,000 | 9.373 | 12.576 | 1.38 |
| Sort | 1,000,000 | 106.965 | 110.399 | 7.62 |
| String map insert + lookup | 100,000 | 93.309 | 100.125 | 47.25 |
| String map insert + lookup | 1,000,000 | 1287.774 | 1316.095 | 377.62 |

**The 1M-key string map still uses 377.62 MiB peak RSS.** Its current layout, owned byte keys/values and allocator retention remain substantial. These results do not establish a compact map representation.

Separate instrumented builds count allocations; the original baseline remains unchanged, and the baseline profiling copy adds only the same two counters. Default builds optimize those counters away.

| Workload | N | Before requests | After requests | Before requested bytes | After requested bytes |
|---|---:|---:|---:|---:|---:|
| Append | 50,000 | 150,001 | 16 | 50,000,600,000 | 524,400 |
| Sort | 10,000 | 20,003 | 1 | 1,600,240,000 | 80,000 |
| String map insert + lookup | 5,000 | 75,035,000 | 61,070 | 901,868,871 | 1,410,300 |

## Cross-language performance checks

All measurements below are native ARM64 Linux. Each matrix has its own timing boundary; do not compare an internal collection phase with a whole-process compute or JSON time. Competitor implementations and application source were unchanged. These compare particular complete implementations, including different layouts and algorithms.

| Workload | Axon | Rust | Go | Bun |
|---|---:|---:|---:|---:|
| Stencil, 1M elements ×20, 1 worker, median process ms | 20.71 | 35.23 | 39.81 | — |
| Stencil, same input, 4 workers, ms | 10.61 | 13.31 | 16.19 | — |
| Mandelbrot, 1200² ×300, 4 workers, ms | 47.36 | 69.69 | 72.34 | — |
| N-body, 1024 bodies ×3, 4 workers, ms | 4.23 | **3.70** | 5.31 | — |
| JSON workflow, 1M documents, 1 worker, ms | 305.15 | 400.80 | — | 359.53 |
| HTTP hello, 64 connections, requests/s | 568,158 | 285,289 | 298,828 | 95,567 |
| HTTP pipeline depth 16, requests/s | 6,077,457 | 3,324,262 | 441,679 | 27,653 |
| HTTP hello, one worker, requests/s | 218,465 | 217,477 | 91,179 | 104,538 |

Compute and JSON use seven measured runs with shuffled implementation order and CPU affinity. Compute has one warmup; JSON has two. The earlier JSON attempt overlapped host validation and is explicitly excluded in `.kernel-build/language-v01/excluded-attempts.json`; its raw data is retained. The final JSON matrix ran without other validation jobs. Current JSON versus preserved previous Axon is essentially unchanged (305.15 vs 304.84 ms at 1M). This language work did not create a new JSON-parser speedup.

HTTP uses three 3-second runs after 1-second warmups, four wrk client threads and the available 8-CPU server budget; client and servers share the VM. Axon uses eight worker processes, Rust/Go their default multicore execution, and Bun one event loop. The separate one-worker Axon/Rust result is effectively tied. Protocol support differs and Axon omits Date; pipelined latency percentiles are excluded because the harness previously observed invalid values. These are short local saturation checks, not long-duration or production latency claims.

At HTTP hello saturation, Axon sampled aggregate RSS/PSS is 1.30/0.92 MiB and CPU is 5.64 µs/request; Rust 5.61/4.55 MiB and 7.43 µs; Go 15.29/14.41 MiB and 14.71 µs; Bun 55.09/53.90 MiB and 11.32 µs. RSS/PSS are sampled across processes; startup and executable sizes are in the HTTP report.

Detailed reports include run ranges, CPU, RSS, methods and raw evidence:

- [Compute](RESULTS-language-core-compute-linux-2026-10-24.md)
- [JSON](RESULTS-language-core-json-linux-2026-10-24.md)
- [HTTP](RESULTS-language-core-http-linux-2026-10-24.md)

## Remaining boundaries

- TLS/crypto are **experimental and unaudited**. The client supports the documented TLS 1.3 X25519/ChaCha20-Poly1305/RSA profile and limited ordered RSA certificate chains with explicit trust anchors; it is not a general PKIX implementation. No revocation/AIA/ECDSA, HTTP/2, IPv6 DNS or general thread scheduler is supplied. No TLS/DNS/LSP throughput superiority is claimed.
- Raw `process_fork` retains legacy unsafe heap semantics: preexisting ordinary allocator mappings may be shared. Registered file/socket/TLS handles are process-bound, and channels/cancellation explicitly shared; raw fork does not imply isolated ordinary heap values. General isolated process spawning remains future work.
- Generic specializations are bounded; recursive value types are rejected. Enums use initialized storage for all alternatives, not a compact maximum-payload union. Resources cannot escape in containers/Result. Scoped `?` is not a general exception unwinder.
- Local exact-version package locking/vendoring is implemented; a public registry, remote resolution, compiler self-hosting, advanced incremental editor analysis and a stabilized ABI are outside this development release.
- Rust wins the four-worker N-body median in this run. Other wins are workload-specific and do not prove universal language superiority.

## Reproduction and evidence

Run from the Axon repository:

```sh
./axon test
python3 tests/language_perf_checks.py
python3 bench/language/run.py --output .kernel-build/language-v01/bench-collections-rerun --repeats 7
python3 bench/usability/compute.py --repeats 7 --report RESULTS-compute-rerun.md
python3 bench/json/run.py --repeats 7 --baseline .kernel-build/language-v01/baseline-library --report RESULTS-json-rerun.md
python3 bench/http/compare.py --duration 3s --warmup 1s --repeats 3 --threads 4 --scenarios hello-64 pipeline-16 hello-one-worker --report RESULTS-http-rerun.md
./axon release -o axon-0.1.0-dev.1.tar.gz
```

Benchmark prerequisites are independent toolchains, GNU time/taskset and wrk. The preserved-baseline path is required for this specific before/after collection comparison. Reproduction on another machine will change timing values.

Evidence under `.kernel-build/language-v01/`:

- `baseline/sources.json`: 81 preserved source-file hashes.
- `application-sources.json`: 45 unchanged example/application source-file hashes.
- `linux-release-full.log`, `macos-release-unit.log`, `x86/release-unit.log`: final regression logs.
- `x86/summary.json`: additional cross-architecture new-core/compute/network regression matrix.
- `release-audit/`: final native ARM64/x86 ELF and dependency evidence; `release-audit.log` includes empty-root execution.
- `bench-collections-linux/measurements.json`: every collection timing/command/checksum, scaling and allocation profile.
- `final-revalidation/manifest.json` and `release-audit/manifest.json`: final rebuilds of measured collection/profile/compute/JSON/HTTP executables. Every final executable is byte-identical to its measured binary after the unit-value and resource-lifetime fixes; final-source hashes are recorded. Timings therefore remain attributable to final machine code.
- `release-verification.json`: two identical 65-file source bundles, manifest verification and an extracted-bundle generic unit-result build/run.

The release is `.kernel-build/language-v01/axon-0.1.0-dev.1-a.tar.gz`. Raw benchmark directories reported as `/axon/...` are the Linux container mount of this repository. Existing database benchmark reports are separate and were not rerun as application-development work.
