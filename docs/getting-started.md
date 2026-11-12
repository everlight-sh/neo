# Building applications with Neo

The native compiler needs Clang and a linker. Linux targets include ARM64 and
x86-64; macOS supports ARM64. Linux executables are static, with no libc, CRT,
loader or shared-library dependency. macOS still requires its system loader
and libSystem load command, with no imported functions.

Install it, then check the machine:

```sh
curl -fsSL https://neolang.dev/install.sh | sh
neo doctor
```

The installer puts the platform's native bundle in `~/.neo` and links
`~/.neo/bin/neo`. `neo doctor` checks Clang and the linker by building and
running a small program. Neo does not need Python to install, build or run.

From a checkout, build the compiler with a native release as the seed (any
native `neo` or `neoc` works):

```sh
sh install.sh --version 0.2.4
./compiler/bootstrap.sh --seed ~/.neo/bin/neo
./compiler/bootstrap.sh
```

The script writes `.neo-build/bin/neoc`, which `./neo` uses. Without `--seed`
it builds with that `.neo-build/bin/neoc`, so the third line rebuilds the
compiler with itself to reach a fixed point.
The Python reference compiler and its test suite are in the `v0.2.4` tag.

For an offline install, create an archive with `./neo release -o neo-native.tar.gz`
and run `./install.sh --archive neo-native.tar.gz` on the matching platform.
`neo release` uses the system `gzip` and accepts `--native /path/to/neoc` to
package a different executable.

```sh
neo init hello-app
cd hello-app
neo run
```

`neo init PATH` creates `neo.toml` and a starter `src/main.neo` in a new or
empty directory.

`neo.toml` selects the entry file. `neo build` and `neo run` use it when no
file is supplied. Pass application arguments after `--`: `neo run -- 8080`.
`neo run --dev` and `neo build --dev` make a development build: faster to
build, slower to run, checked exactly like a release build.
Scalar main parameters retain checked numeric argv parsing. A zero-argument
effectful main can read arbitrary string arguments using `cli_arg`,
`cli_count` and `cli_args`.

Configure your editor to launch `neo lsp` over stdio. It checks unsaved buffers
and provides completion, hover, definitions, symbols, and formatting.
`neo graph FILE --full` emits the content-addressed graph as JSON.
Use `neo check FILE --library` to check code without a `main` function.
Add `--diagnostic-format json` or `--diagnostic-format human` for structured or
human-readable diagnostics.

These complete documentation examples are also native test fixtures.

```neo
import "std:strings"
fn main () -> Arr u8 _ = concat("answer: ", int_text(42), "\n")
```

```text
answer: 42
```

```neo
import "std:json"
fn main () -> i64
  = let document = json_parse("{\"answer\":42}") in
    let field = json_get(document.value, "answer") in
    let answer = json_int(field.value) in
    check document.ok && field.present && answer.ok in answer.value
```

```text
42
```

## Modules and data

`import "helpers.neo"` loads a relative file. `import "std:json"` loads the
shipped library. Imports are transitive and deduplicated. Cycles, missing
files, duplicate declarations and imported main functions are errors. This
module system supports `import "helpers.neo" as helpers` and qualified names
such as `helpers::answer()`. Declarations are public by default; `private` hides
them. Exact local packages, lockfiles and offline vendoring are available; there
is no remote registry or version-range solver. Run `neo pkg lock` after changing
dependencies, `neo pkg verify` to check the lock against disk, and
`neo pkg vendor` to copy locked dependencies into `.neo/vendor` for offline use.
Each command accepts a project path and defaults to the current directory.
Import a locked dependency with `import "pkg:math" as math` or select a module
with `import "pkg:math/sub"`. Native builds verify the lock and can use the
vendor tree after the original dependency directories are removed. If a
generated entry file lives outside the project, pass `--package-root PATH`
when building it so imports of project modules can use the project's lock.
See the [language contract](language-v01.md).

Records may contain strings, arrays, other records and nested arrays. Recursive
value types are rejected. Array fields use existential length `_`, for example
`type User = { name: Arr u8 _, scores: Arr i64 _ }`. Access, copying, replacement
and return values preserve ownership. Unique values move; other uses copy owned
children. Managed-element comprehensions currently execute sequentially because
allocations made after fork cannot be returned as parent-process pointers.
Numeric arrays retain parallel workers and the existing scalar-record SoA layout.

`sealed type` permits field reads while restricting record construction and `with`
updates to the declaring source module. The JSON library uses this to preserve
validated values and cached offsets. Use `json_parse` to create a JSON value and
`json_none().value` for its empty sentinel; direct `Json { ... }` construction from
application modules is rejected. Safe array updates to a copy of `.raw` or
`.offsets` preserve the original value.

Pure internal functions borrow record arguments where the caller keeps storage
alive. Returned children acquire ownership before escaping; temporary arguments
live through the call. This is automatic and preserves value semantics. Empty
arrays use a canonical non-owning representation, and static string fields remain
immutable; mutation still uses copying when necessary.

## Errors, effects and arithmetic

`BytesResult` and `IntResult` contain `ok`, `value` and an `Error` with code,
message and position. `OptionInt` and `OptionBytes` contain `present` and value.
These compatibility records coexist with generic `Option<T>` and `Result<T,E>`.
Generic records/functions, enums, exhaustive matching and scoped Result binds are
available. Collections provide geometric vectors, heapsort and SipHash maps,
including owned generic values. Scoped File/Socket owners use `using` and checked
resource moves. See the language contract for complete syntax and limitations.

Use declarations such as `effect(fs,env) fn` to state required capabilities.
Calls check capabilities transitively; raw pointers/syscalls require `unsafe` in
explicitly restricted application functions. `fs`, `net`, `time`, `env`, `process`
and `unsafe` are supported. Existing unrestricted `effect fn` remains compatible.
The runtime and shipped standard modules are the audited trusted boundary.
Capabilities are compile-time declarations, not an OS security sandbox.

`serve(port, pure_handler)` remains pure. `serve_effect(port, handler)` permits
effectful request handlers; callers must declare the handler's capabilities.
Effects are still rejected inside refinements and parallel comprehensions.
Filesystem/network calls in a handler are synchronous and may occupy that worker.

**Arithmetic change:** safe application/library i64 addition, subtraction,
multiplication, negation, division and reduction trap on overflow instead of
silently wrapping. Explicit `wrapping_add`, `wrapping_sub`, and `wrapping_mul`
provide intentional wraparound and do not create mathematical refinement facts.
The compiler removes checks when conservative intervals or lexical bounds prove safety. SIMD masks
exclude inactive branches/lanes from traps. Invalid float-to-i64 casts trap.
The trusted runtime retains wrapping word operations for allocator/memory policy.

`bit_and`, `bit_or` and `bit_xor` take two i64 operands and preserve their exact
64-bit patterns. `byte_swap64` reverses the eight bytes of an i64. `mul_high(a,b)`
is the high 64 bits of the unsigned 128-bit product of the two bit patterns. Results use
the signed i64 interpretation; these operations do not imply arithmetic bounds.
The constant folder, independent interpreter and native backend agree on these
operations, including negative values and the sign bit.

zetaDB, a separate project written in Neo, demonstrates persistent document
collections, computed fields, atomic batches, snapshots and HTTP/SSE watches
with explicit systems resource ownership. Its sources use `.neo` and build
with the current `neoc` compiler.

## Standard library

| Module | APIs |
|---|---|
| `std:strings` | Byte slicing/comparison/search/trim, i64 parsing/formatting including MIN/MAX, UTF-8 validation/encoding |
| `std:errors` | Concrete typed results and optional values |
| `std:collections` | Integer vectors, sorting, string-to-string map |
| `std:json` | Strict UTF-8 JSON parsing, accessors, decoded strings, number lexemes, compaction and escaping |
| `std:toml` | TOML 1.0 documents parsed into `std:json` values |
| `std:deflate` | Bounded gzip, zlib and raw DEFLATE decoding; deterministic encoding at levels 0-9 |
| `std:io` | Bounded file reads, writes/appends, locking, fsync, seek/truncate, argv/environment, clocks and process helpers |
| `std:http` | Request helpers, response construction, HTML escaping, bounded response framing/chunk decoding |
| `std:net` | HTTP/1.1 POST to IPv4/localhost, nonblocking sockets, deadlines and recoverable errors |
| `std:journal` | Locked, fsynced JSON-line transactions and incomplete-tail recovery |
| `std:option`, `std:result` | Generic alternatives and scoped error propagation |
| `std:vec`, `std:hashmap` | Generic owned collections and kernel-seeded maps |
| `std:file`, `std:socket` | Scoped resources with guarded handles |
| `std:channel`, `std:cancel` | Bounded SPSC process messages, deadlines and cancellation |
| `std:time`, `std:random` | Monotonic clocks and direct kernel randomness |
| `std:dns`, `std:http_client` | DNS with TCP fallback and bounded streaming HTTP |
| `std:https_client`, `std:http2`, `std:hpack` | Keep-alive HTTP client for one origin; HTTP/2 over TLS when ALPN selects h2 |
| `std:tls` | Experimental TLS 1.3 with explicit RSA/P-256 trust anchors; see contract |
| `std:reactor`, `std:datagram` | Kernel poll over generational interests and scoped IPv4 UDP |
| `std:buffer` | Scoped private mutable bytes/words with checked access and copied snapshots |
| `std:aes`, `std:p256`, `std:sha1` | Experimental Neo crypto and legacy protocol compatibility |

JSON values own source slices and object-member indexes. Parsing validates strict
syntax and UTF-8 together; accessors reuse that invariant instead of revalidating
the source. Object indexes grow geometrically, and arrays cache their element count.
Numbers preserve their source lexeme; `json_int` accepts only i64 integers.
Unpaired surrogate escapes, invalid UTF-8 and nesting deeper than 128 are rejected.
Object access uses the last duplicate key. Typed finite float access and construction are available through the JSON and
number modules. The compatibility POST helper retains a 1 MiB response
limit. New streaming HTTP uses bounded buffers and an explicit configurable body
limit. DNS and a separate experimental TLS library are available; the HTTPS
client speaks HTTP/2 when the server selects it with ALPN.
Unix timestamps and monotonic deadlines now have separate APIs.

## Application examples

```sh
./neo run examples/json-cli/main.neo -- input.json output.json 10
NEO_NOTES_FILE=/tmp/notes.axlog ./neo run examples/notes/main.neo -- 8080
NEO_WEBHOOK_FILE=/tmp/jobs.axlog NEO_WEBHOOK_PORT=8099 ./neo run examples/webhook/main.neo -- 8081
```

The JSON CLI validates records containing integer `id`/`score` and string `name`,
filters by minimum score, stably sorts and fsyncs output. Invalid input does not
replace an existing output file. Reads are bounded to 16 MiB.

Notes exposes GET/POST `/api/notes`, GET/PUT/DELETE `/api/notes/N`, and an escaped
SSR list at `/`. Mutations take an exclusive file lock, replay the journal,
append and fsync before responding. It prioritizes transparent persistence over
an indexed/cached storage engine. The default journal size limit is 16 MiB.

The webhook example accepts POST `/events` with `{ "id": "unique-key", "payload": ... }`
and lists GET `/jobs`. IDs are visible ASCII, 1–128 bytes. Incoming IDs are
deduplicated even after completion. A consumer claims persisted jobs, sends
`Idempotency-Key`, retries with bounded exponential delay and records done/failed.
`NEO_WEBHOOK_HOST`, `PORT`, `PATH`, `TIMEOUT_MS`, `RETRY_MS`, and `MAX_ATTEMPTS`
configure delivery (each variable is prefixed `NEO_WEBHOOK_`). A lease protects
in-flight claims across restarts. Delivery is **at least once**: a crash after
receiver success but before recording completion can resend; receivers must honor
the idempotency key for exactly-once logical effects.

Terminate a whole process group, as the test harness does. HTTP children detect
parent death; the consumer checks after its bounded current operation. Pending
work survives termination rather than requiring an in-memory shutdown drain.
Tests cover process crashes/torn writes; this is not a claim about power-loss
durability of newly created directory entries or arbitrary storage hardware.

## Tests, formatting and cross-target verification

`neo test [PROJECT]` runs the project's Neo tests. It reads `[[test]]`
cases, paired Markdown examples from `doc-tests`, and zero-argument boolean
`test_*` functions from `test-globs` or the default `tests/*_test.neo` and
`tests/*_test.ax` patterns. A case builds `file` and runs it with `args`,
`env.NAME` variables, `stdin` (or `stdin-hex`, or `stdin-file` for a file of
input bytes) and a `timeout` in seconds. It then checks:

- `exit`, the expected exit status (0 by default);
- `stdout` exactly, `stdout-hex` or `stdout-file` byte for byte, or numeric
  output within `stdout-tolerance`;
- `stderr` exactly, with the program's own path written as `<program>`.

`build-env.NAME` sets variables for the compiler. A case with `check = true`
only runs the checker, which must accept the file. One with `reject = true`
expects the checker to refuse it, optionally with `exit` (1 for an error,
2 for an unsupported construct), a `diagnostic` substring, or the checker's
exact `stdout`, where the file's path is written as `<file>`. Files named by
`stdin-file` and `stdout-file` are relative to the manifest. A case with an
unknown key fails as invalid.

The `integration` entry in `[tool.neo]` names one TOML file of native cases,
or a list of them, resolved relative to the project. `--unit-only` skips those
cases, and `neo test tests/integration.neo.toml` runs one file directly.

Every program a case runs gets `NEO_TEST_COMPILER`, `NEO_TEST_ROOT`,
`NEO_TEST_TARGET`, `NEO_TEST_PROJECT` and `NEO_TEST_SOURCE` (its own source
file). A test driver uses them to build and run further programs with the
compiler under test; `tests/support/driver.neo` has the helpers the
repository's own drivers in `tests/drivers/` share. The README lists the
repository's manifests, the tools the full suite needs and its opt-in checks.

`neo fmt [PATH...]` formats the specified files or recursively finds `.neo` and
`.ax` sources in directories. With no paths it uses the current directory.
`neo fmt --check` lists files that would change and exits with status 1 when
any file needs formatting. The formatter normalizes whitespace, indentation,
and final newlines while preserving tokens, comments, and literal spelling.

`neo build --report` emits JSON with frontend, LLVM compile, and link timings,
binary and source digests, and counts of optimization remarks emitted by LLVM.
`neo build --allow-unproven` permits experimental builds with unproven
obligations. Type, effect, and ownership checks still apply.

`neo build --library-cache DIR --library-root PATH` prepares and reuses a
native object for the dependency closure. `--library-root` can be repeated.
The object cache keys include dependency sources, generated IR and ABI, the
target, Clang, and optimization level. The compiler verifies artifact hashes
before linking and checks the source program on every build. `--no-cache`
rebuilds the prepared object. Prepared libraries require fully checked code.
The Python reference compiler also kept library inlining hints (`hints.ll`)
and answered unchanged rebuilds from a record (`NEO_QUICK`); it is in the
`v0.2.4` tag.

Run native benchmarks from the checkout. The compute and compile modes use
GNU `time` for child CPU and RSS measurements.

```sh
./neo run --dev bench/run.neo -- compute 7
./neo run --dev bench/run.neo -- compile 3
./neo run --dev bench/run.neo -- http 3
./neo run --dev bench/run.neo -- maps 3
NEO_BENCH_REPORT=report.md ./neo run --dev bench/run.neo -- servers 3
```

The runner writes one JSON record per sample. Pass a TOML manifest as the last
argument to select workloads. `NEO_BENCH_COMPARE` points to a directory of
comparison binaries named after the compute cases. Compile measurements use a
scratch copy and report cold, unchanged, and incremental builds. The HTTP
mode validates each response in a loopback pipeline. The maps mode samples
Linux RSS and PSS at the workload's seven checkpoints. To measure the JSON
workload, pass `bench/json/neo.toml` to the compute mode. The servers mode
compares `examples/http.neo` with Rust, Go and Bun servers under wrk on Linux
(see the README).

On ARM64 Linux with Clang/lld and QEMU installed:

```sh
NEO_TARGET=x86_64-unknown-linux-gnu ./neo build examples/hello.neo -o hello-x86
qemu-x86_64 ./hello-x86
NEO_TARGET=x86_64-unknown-linux-gnu NEO_RUNNER=qemu-x86_64 ./neo test tests/language.neo.toml
```

`neo test` builds every case for `NEO_TARGET` (or `--target`) and starts each
case's program through `NEO_RUNNER`. A driver that builds and starts further
programs runs them directly, so those cases also need QEMU registered with
`binfmt_misc`.

Emulation establishes functional compatibility, not native x86 performance.
The supplied CI matrix targets native ARM64 and x86-64 Linux when run in a GitHub
repository. Local verification does not establish that a remote CI run occurred.
