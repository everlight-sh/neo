# Axon usability implementation and verification — 2026-10-24

The requested usability roadmap now has an initial implementation: source modules,
owned nested data, structured results/options, eight standard-library modules,
capability declarations, project commands, three persistent application examples,
Linux x86-64 support, and repeatable correctness/performance drivers. All runtime
implementation remains Axon over kernel syscalls. Python/LLVM remain build tools.

This is an application-building prototype with documented limits, rather than a
claim that every language/ecosystem feature is complete. See the
[application guide](docs/getting-started.md) for contracts and commands.

## Delivered examples and tooling

- [JSON CLI](examples/json-cli/main.ax): validates typed records, filters, stably
  sorts, handles Unicode and writes/fsyncs JSON. Invalid input leaves existing
  output untouched.
- [Notes CRUD/SSR](examples/notes/main.ax): HTTP routes, escaped HTML, locked
  append-only storage, concurrent mutations, fsync-before-ack and restart replay.
- [Webhook worker](examples/webhook/main.ax): durable jobs, idempotency keys,
  outbound HTTP, leases, retries, deadlines, terminal failures and restart recovery.
- `./axon init`, `run`, `test`, `fmt`, and `axon.toml`; executable documentation,
  structured diagnostics, import-aware verified caches and atomic publication.
- [Native Linux CI configuration](.github/workflows/verify.yml) for ARM64/x86-64.
  It is configured locally; no remote CI run or repository publication occurred.

## Correctness evidence

Final logs and build reports are under `.kernel-build/usability/`.

| Verification | macOS ARM64 | Linux ARM64 | Linux x86-64 |
|---|---|---|---|
| Compiler/module/capability/project/prover unit tests, 45 | pass | pass | pass |
| JSON CLI, notes and webhook behavior/failure/restart checks | pass | pass | pass, QEMU 8.2 |
| Strict JSON differential corpus, 627 byte inputs | pass | pass | pass, QEMU 8.2 |
| File errors, argv/environment, NUL rejection and clocks | pass | pass | pass, QEMU 8.2 |
| Independent evaluator: 80 programs × 5 inputs × 2 optimization modes | pass | pass | pass, QEMU 8.2 |
| Deterministic malformed-source parser corpus, 2,000 inputs | pass | pass | pass |
| Signed arithmetic, SIMD masks/tails, casts and overflow boundaries | pass | pass | pass, QEMU 8.2 |
| Existing compute and fork/runtime tests, 1/4 worker settings | pass | pass | pass, QEMU 8.2 |
| HTTP framing, concurrency, batching, backpressure and descriptor reuse | pass | pass | pass, QEMU 8.2 |
| Bounded-stencil differential corpus, 2,080 executions | pass | pass | pass, QEMU 8.2 |

The macOS complete `axon test` also passes six manifest/documentation cases,
31 TSX transformer tests, exact output parity against React for all 1,000 supported
prop values with one/four workers, pipelining and concurrent requests. The Docker
HTTP comparison independently validates every server against that same React
corpus before measuring it.

Crash tests include notes with 30 concurrent mutations, SIGKILL/restart, incomplete
journal tails, corrupt complete records and storage errors. Webhook checks cover
concurrent deduplication, retries/timeouts, terminal failure and restarting pending
work. Delivery is at least once; receiver idempotency supplies logical deduplication.
These are process-crash tests, not power-loss certification.

The VM's automatic x86 handler is QEMU 7.0 and intermittently SIGSEGVed during
repeated process launches. The explicit QEMU 8.2 runner passes the complete x86
corpus. This distinction is retained in the failed and successful logs; x86 results
establish emulated correctness, not native x86 speed or a completed native CI run.

Key final evidence: `final-macos-rerun.log`, `final-arm64-rerun.log`,
`unit-final.log`, `final-x86_64-rerun.log` (unit tests), and
`final-x86_64-all-qemu.log` (complete explicit-emulation integration).

The updated `Dockerfile.linux-test` also builds successfully from a clean context,
installs the pinned TSX dependencies, and passes the complete suite plus an
empty-root HTTP audit. This checks that verification does not depend on the local
compiler cache or previously installed example packages. Its logs are
`fresh-verification-build.log` and `fresh-verification-test.log`. The x86 project
manifest/documentation cases separately pass in `final-x86_64-project.log`.

## Runtime dependency and deployment checks

All six application executables (three apps × two Linux architectures) have zero
undefined symbols, no `DT_NEEDED`, and no ELF interpreter. Each runs in a scratch
image as UID 65532 with a read-only root, all capabilities dropped, no-new-privileges,
a 256 MiB limit, and only an application-data tmpfs writable. The CLI successfully
reads and writes; both servers accept and persist a request. Ordinary application
tests separately verify full output and restart semantics.

HTTP passes from a chroot containing only its executable on both Linux targets,
with no `/lib`, `/usr`, `/proc` or runtime assets. ARM64 execution is native; x86
execution uses the VM emulator. Audit results are in `empty-root-audit.log`,
`standalone-audit.log`, `standalone/*/results.json` and `images/manifest.json`.

| Linux app | ARM64 executable bytes | x86-64 executable bytes |
|---|---:|---:|
| JSON CLI | 60,000 | 67,240 |
| Notes CRUD/SSR | 90,376 | 103,128 |
| Webhook worker | 135,560 | 157,656 |

Linux applications have no libc/CRT/shared-library dependency. The OS kernel is
still required. macOS requires its libSystem loader command, with zero function
imports. The build and benchmark tool containers contain dependencies; the Axon
application images do not include those tools.

## Benchmarks

- [Library, JSON CLI, builds and persistent apps](RESULTS-usability-linux-2026-10-24.md).
- [Axon/Rust/Go compute comparisons](RESULTS-usability-compute-linux-2026-10-24.md).
- [Axon/Rust/Bun/React HTTP container comparison](RESULTS-usability-http-linux-2026-10-24.md).
- [Reproduction instructions](bench/usability/README.md).

Selected medians from this local run:

| Workload | Axon | Rust | Go / Bun |
|---|---:|---:|---:|
| HTTP SSR, four CPU budget, requests/s | 450,859 | 231,815, glibc | 126,211 Bun direct; 124,164 Bun/React |
| HTTP SSR, four CPU budget, peak measured working set | 2.11 MiB | 3.94 MiB, glibc | 64.57 MiB Bun direct; 225.55 MiB Bun/React |
| Mandelbrot 1,200², four CPU budget, wall time | 55.00 ms | 80.09 ms | 83.52 ms Go |
| Stencil 1M × 20, four CPU budget, wall time | 26.69 ms | 20.84 ms | 20.95 ms Go |
| N-body 1,024 × 3, four CPU budget, wall time | 4.31 ms | 6.12 ms | 6.73 ms Go |
| Construct/parse/access 10,000 JSON documents, wall time | 31.46 ms | 8.46 ms | 34.83 ms Bun |

Axon does not win every workload: Rust remains faster for JSON parsing and this
stencil case. The checked-arithmetic implementation also changes the semantics
relative to historical unchecked runs. HTTP throughput favors Axon here, while its
one-CPU p99 latency (7.44 ms) is higher than Rust/glibc (3.37 ms). The report retains
the unusually variable Rust/musl result and the prior Axon executable rather than
omitting them. Small timing differences and changes versus the old Axon executable
should not be treated as causal evidence on this shared host.

Cold builds range from about 2.1 seconds for hello to 5.1 seconds for the webhook
example; verified warm builds are about 0.21–0.31 seconds. The JSON process cases
use about 1.4–1.5 MiB peak RSS in Axon versus roughly 37–40 MiB in Bun. Notes reaches
about 1,078 durable creates/s and 2,819 lists/s with four HTTP workers on the small
25-note fixture. The webhook example completes about 253 acknowledged deliveries/s
for a 20-event batch, including persistence and the local Python receiver.

The reports include repeated-run ranges, correctness checks and raw artifact
locations. Process RSS and Docker working set are different metrics and are
labeled separately. Stateful application figures include storage/client overhead;
they are not isolated server-capacity measurements. The local VM shares its host
with other applications, so short measurements and small gaps are noisy. Historical
reports remain available; intermediate and failed attempts are retained.

## Semantic changes and remaining limits

Safe application/library i64 arithmetic now traps on overflow, including reductions
and invalid float-to-i64 conversions. Use explicit wrapping builtins when wraparound
is intended. Proven lexical bounds/conservative intervals can remove redundant
checks; inactive SIMD branches and tail lanes cannot trigger false traps. Trusted
runtime word arithmetic retains its existing wrapping policy.

The prover now returns unknown when its branch/resource limit is reached instead
of silently truncating alternatives. Loop bindings receive distinct proof symbols
when shadowing outer names. Cache hits verify artifact hashes; imported edits and
tampering invalidate them, and concurrent builds publish atomically.

Modules currently share global declarations. Results/options and collections are
concrete types, not generic ADTs; the string map is linear. Formatting is conservative
whitespace normalization. Owned-element comprehensions execute sequentially;
numeric arrays remain parallel. Outbound HTTP supports numeric IPv4/localhost with
bounded responses/deadlines; DNS, TLS and HTTP/2 are not implemented. Clocks use
Unix wall time. Notes/journal storage is bounded and replays records per operation.
Capabilities are a compile-time contract, not an OS sandbox. Compiler self-hosting,
a remote package registry and a full language-server/editor ecosystem remain
separate projects.
