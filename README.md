# Neo

A programming language made for LLMs, with one goal: native code at least as fast as Rust, and parallel by default like Go.

Pipeline, same shape as rustc:

```
source (.neo)  ->  content-addressed graph  ->  refinement checker  ->  LLVM IR  ->  native binary
                  (every node hashed)         (proof obligations)     (neoc/llvm.py)   (LLVM -O3 + link)
```

The compiler emits LLVM IR directly (`neoc/llvm.py`). The application and
the runtime in `runtime/*.neo` compile together into one LLVM module and then
a native executable. Allocation, memory operations, formatting, scheduling and
HTTP handling are Neo source. OS services use direct ARM64 or x86-64 kernel syscalls,
with no libc function imports. Linux builds a static ELF with no interpreter,
shared libraries or CRT. Native ARM64 macOS still loads `libSystem`: Apple's
loader requires it and rejects static executables, even though Neo imports
none of its functions. The kernel remains a runtime requirement on both.
Python implements the compiler, and Clang/LLVM supplies code generation and
linking; compiler self-hosting and eliminating those build tools are not done.
The macOS restriction comes from Apple's
[ARM64 executable loader](https://github.com/apple/darwin-xnu/blob/main/bsd/kern/mach_loader.c).

## Install

```sh
curl -fsSL https://neolang.dev/install.sh | sh
neo doctor
```

`neo doctor` checks Python 3.11+, Clang and the linker, then builds and runs a
one-line program. From a checkout, `ln -s "$PWD/neo" ~/.local/bin/neo` puts the
driver on your PATH. See [docs/getting-started.md](docs/getting-started.md).

## Build profiles

`./neo build file.neo -o app` defaults to LLVM `-O3`.
Use `--opt-level 0` for a faster development build (`1` and `2` are also
supported). All levels retain type/refinement checking and checked arithmetic.
Optimization level and `NEO_INLINE_BUDGET` participate in the build cache key;
the latter defaults to the existing 160-node forced-inlining budget.
`--report` includes compiler phase timings and optimization settings, and
`inline_budget_misses`: calls inside loops and comprehensions whose callee
exceeded that budget and so is no longer force-inlined. `inline fn` forces
inlining of a non-recursive internal function whatever its size.

The proof engine keeps integral constraints in arbitrary-precision integers,
clearing rational denominators by positive exact scaling during elimination.
The optional `--library-cache DIR --library-root dependency-path` path reuses
checked dependency objects and optimized IR, statically linked into the final
executable. All application bodies/signatures remain checked. Changes in
dependency sources, imported types, compiler or flags invalidate the artifact;
corrupt artifacts are rebuilt. Neo Web uses `./web prepare` for this step.

LLVM receives only reachable internal bodies; public ABI entries and
address-taken callbacks/parallel regions are preserved. These are build-time
changes and add no runtime dependencies.

## What the design changes

- **Proofs replace checks.** Every array index, division and range carries a
  proof obligation. The checker discharges it from parameter refinements,
  range bounds, branch conditions and `check` nodes using Fourier-Motzkin
  elimination over integer constraints. An unproven obligation is a compile
  error with a counterexample, never a silent runtime check.
- **Parallel by default.** Every `sum(i in a..b)` and `arr(i in a..b)` at the
  top of a function is outlined into a region function and dispatched over a
  set of kernel workers in up to `ncpu * 8` chunks. On Linux, compiler-certified
  allocation-free scalar/vector and record bodies share the address space with
  separate stacks;
  allocating bodies use fork workers with borrowed inputs and controlled shared
  output buffers. Raw `process_fork` does not isolate preexisting ordinary heap
  mappings; see the language contract. Workers are joined after each
  region. Ranges below 1,024 elements run
  sequentially to avoid process startup overhead. Nested comprehensions and functions called
  from inside a region are compiled in sequential mode, so regions never nest.
  Comprehensions producing owned strings or nested arrays run sequentially;
  allocations made inside a child cannot become parent-process pointers.
  Cheap straight-line vector bodies also use an estimated work threshold, so
  a small pass can run sequentially within a larger configured CPU budget.
- **Content-addressed graph.** Functions and nodes are named by the hash of
  their structure with variables as binder distances. Renaming changes no
  hash; builds are cached by program hash.
- **Compiler-owned memory.** Arrays are `{ptr, len, owned}`. Ownership moves
  along a uniqueness discipline: an array variable whose every control-flow
  path uses it at most once as a whole (passed to a call, updated with `set`,
  returned, stored into a loop state) is moved at that use, and `set(a, i, v)`
  then updates the buffer in place instead of copying. Whatever still owns a
  buffer at scope exit frees it. No GC, no refcounts, no `Rc`. The Neo runtime
  implements power-of-two free lists over kernel-mapped memory. Small blocks
  come from slabs. Freed mapped blocks stay on their class list while those of a
  heap kind total at most 64 MiB; a block beyond that is parked, one per heap
  kind, and the next allocation of its size class takes it back with its pages
  resident. Parking unmaps the previously parked block and every new allocator
  mapping unmaps both parked blocks first, so resident memory never exceeds what
  was live before the free. On Linux, private managed blocks of 4 MiB or more ask
  for transparent huge pages over the 2 MiB regions their bytes fully cover, and a
  program whose parallel regions all run on threads keeps managed arrays in
  private pages at any worker count. There is no malloc/free library dependency.
- **Compiler-chosen layout.** `Arr Body n` for a scalar numeric record is stored
  struct-of-arrays inside one buffer, fields ordered by size; the program
  indexes records and never sees the layout.
- **Bounded arithmetic.** A conservative compiler pass propagates signed
  integer and array-element intervals through pure calls, branches and loops.
  For a small bounded dividend, `% constant` becomes a few comparisons and
  subtractions, using 32-bit arithmetic when its bounds permit. This makes the
  HTTP stencil cheaper without changing its source, passes or checksum.
  Possible overflow, unknown inputs and effect boundaries keep conservative
  bounds. `NEO_RANGE=0` disables the optimization for differential checks.
- **Compile-time evaluation.** Ordinary functions are pure, so a call whose
  arguments are all literals is run by the compiler and replaced by its result
  (`escape("Ben & Jerry's …")` becomes a constant; `NEO_FOLD=0` disables).
  Calls to `effect fn` and `extern fn` are never evaluated at compile time.
- **Inlining into `concat`.** A call whose body is a `concat` is inlined at a
  `concat` argument and the nested concat flattened, so `concat(acc, row(i))`
  appends the row's pieces straight onto `acc` with no intermediate buffer
  (`NEO_INLINE=0` disables).
- **Cross-iteration vectorisation.** A `sum` whose body is scalar arithmetic,
  possibly with a data-dependent `loop` and calls to small scalar functions,
  evaluates 16 iterations at a time: `if` becomes `select` and the loop
  runs while any lane is active, freezing finished lanes with masks. LLVM
  cannot vectorise such loops because each iteration's trip count is data
  dependent; the Neo graph has no dependencies between iterations, so the
  compiler may (`NEO_VEC=0` disables it). Mandelbrot's escape loop is the
  canonical case. Scalar numeric `arr` bodies also use four-lane vectors with
  affine array reads. The compiler finds an interior where every speculative
  read is valid; edges and tails remain scalar. Overflow checks stay active
  unless existing proofs establish safety. Both paths are allocation-free.
- **Structured diagnostics.** `neoc check` prints JSON: each obligation with
  its node hash, position, normalised goal, status, counterexample and
  suggested fixes. An agent can act on it without parsing prose.

## Usage

The [latest N-body and map-memory results](RESULTS-nbody-map-linux-2026-10-25.md)
include compiler/stdlib changes, unchanged-workload benchmarks, correctness
checks and dependency audits.

The [0.1 language contract](docs/language-v01.md) describes generic types,
checked enums and Result binds, scoped resources, efficient collections,
bounded process channels, DNS/streaming HTTP, experimental pure-Neo TLS,
local packages, LSP and release tooling, with their current limits.

The [application guide](docs/getting-started.md) covers modules, owned data,
structured errors, capabilities, project commands, the JSON CLI, persistent notes,
and durable webhook delivery. Run `./neo test` for the complete verification suite.

The [JSON optimization report](RESULTS-json-optimized-linux-2026-10-24.md) compares
the unchanged dynamic JSON workload against the preserved Neo binary, Rust/serde
and Bun, with strict validation, ownership regressions and dependency audits.

For a standalone HTML example and the matching production Bun + React
implementation, see [the SSR example](examples/README-ssr.md).
The [JSX-to-Neo prototype](examples/jsx-ssr/README.md) compiles a small subset
of React-style TSX components into ordinary Neo functions, outside the language core.

```bash
./neoc.sh build examples/mandel.neo -o mandel && ./mandel 3000 3000 2000
./neoc.sh build examples/http.neo -o http && ./http 8080   # HTTP server: / and /smooth/N
./neoc.sh build examples/sieve.neo -o sieve && ./sieve 100000000   # in-place sieve via set
./neoc.sh build examples/nbody.neo -o nbody && ./nbody 4096 20     # records, SoA layout
./neoc.sh check examples/unproven.neo        # JSON obligations, exit 1
./neoc.sh build examples/stencil.neo --emit-llvm | less
./neoc.sh graph examples/mandel.neo          # content hashes
```

Requirements: clang (15 or newer, for opaque pointers) and Python 3.11+, on
ARM64 macOS/Linux or x86-64 Linux (little-endian kernel syscall backends;
`docker build -f Dockerfile.linux-test -t neo-linux-test . && docker run --rm neo-linux-test`
runs the verification on ARM64 Ubuntu). Both use HTTP worker processes and
event loops written in Neo over kernel epoll (Linux) or poll (macOS) syscalls. Other CPU
architectures need their own kernel ABI backends before they can build.

Verification:

```bash
python3 -m unittest discover -s tests -v
python3 tests/http_smoke.py
python3 tests/kernel_runtime_smoke.py
python3 tests/compute_smoke.py
python3 tests/bounded_stencil_smoke.py
python3 tests/vector_arrays_smoke.py
```

The kernel runtime smoke test also audits executable imports and exercises
allocation reuse, memory operations, direct syscalls and shared-memory workers.
On Linux, a root-only check runs the HTTP suite inside an empty filesystem,
with only the static executable present:

```bash
python3 tests/freestanding_linux_smoke.py --binary /path/to/http
```

To rebuild and compare the current HTTP runtime with Rust (hyper/tokio), Go
(net/http), and Bun (Bun.serve), including CPU/request, latency, RSS, physical
footprint and executable size on macOS or Linux:

```bash
python3 bench/http/compare.py
```

This saves a dated `RESULTS-http-kernel-{macos,linux}-YYYY-MM-DD.md` report and raw per-run
measurements under `bench/http/results/`. The older `RESULTS-http.md` and
`RESULTS-http-compute.md` describe the removed C runtime. The current harness
includes both default-worker and single-worker scenarios; worker settings
are not CPU affinity. CPU and memory include every worker process. Linux PSS
and macOS physical footprint are different accounting metrics; aggregate RSS
can count shared pages more than once. The reproducible Linux tool image is
`tests/Dockerfile.bench`; use `docker run --init` so orphaned test workers are reaped.

The bounded-arithmetic compiler comparison is in
[`RESULTS-http-stencil-linux-2026-10-23.md`](RESULTS-http-stencil-linux-2026-10-23.md)
and [`RESULTS-http-stencil-macos-2026-10-23.md`](RESULTS-http-stencil-macos-2026-10-23.md).
Both retain the same HTTP workload and runtime source as the preceding
kernel-runtime reports, with fresh Rust/Go/Bun measurements and import audits.

The current standalone stencil comparison is in
[`RESULTS-stencil-optimized-linux-2026-10-24.md`](RESULTS-stencil-optimized-linux-2026-10-24.md).
Run `python3 bench/stencil/run.py` on native Linux to repeat the unchanged
Neo/Rust/Go workload across sizes, iteration counts and one/four CPU budgets.
It also reruns the preserved previous Neo executable, checks every checksum,
and saves raw timings, CPU usage, peak RSS, hashes and static-link audits.

The current Linux epoll backend and container SSR comparison with Rust and
Bun are documented in
[`RESULTS-http-epoll-docker-linux-2026-10-24.md`](RESULTS-http-epoll-docker-linux-2026-10-24.md).
It includes the previous poll image and the same executable's poll fallback,
with both the single-CPU improvement and multicore throughput tradeoff retained.

## Language (textual projection)

```
fn stencil (xs : Arr i64 n) -> Arr i64 n
  = arr(i in 0..n)
      if i == 0 || i + 1 == n then xs[i]
      else (xs[i-1] + 2 * xs[i] + xs[i+1]) % 1000003

fn main (n : i64{n > 0}, iters : i64{iters >= 0}) -> i64
  = let ys = loop (a = arr(i in 0..n) (i * 2654435761) % 1000003, k = 0)
               while k < iters
               next (stencil(a), k + 1)
               yield a in
    sum(i in 0..n) ys[i]
```

Types: `i64`, `f64`, `u8`, `u16` (UTF-16 code units), `bool`, record types declared with
`type Body = { x : f64, m : f64 }`, and `Arr T n` (n is a size variable bound
from the argument; in a return type the size may be an expression over the
parameters, `Arr u8 (n + m)`, or `_` when the caller learns it at runtime).
Parameter refinements go in braces; a return refinement names the value
`result`: `fn digits (v : i64{v >= 0}) -> i64 {result >= 1}`. The checker
proves it from the body and uses it at every call site. Expressions: `let ... in`,
`if ... then ... else`, `sum(i in lo..hi) e`, `arr(i in lo..hi) e`,
`loop (state = init, ...) while c next (...) yield e`, `check p in e`,
`len(xs)`, `f64(x)`, `i64(x)`, `u8(x)`, `u16(x)` (wrapping, like `u8`), `sqrt(x)`, byte strings `"GET / "`
(type `Arr u8 6`) and byte literals `'G'`. Records: `Body { x = 1.0, m = 2.0 }`,
`b.x`, `b with { x = b.x + 1.0 }`; `sum` over a record type adds fieldwise.
`set(a, i, v)` is `a` with `a[i] = v`, updated in place when `a` is uniquely
owned (see [examples/sieve.neo](examples/sieve.neo)). `concat(a, b, ...)` joins
byte arrays (or `Arr u16` arrays) in one allocation; when `a` is uniquely owned and its buffer has
spare capacity the result is appended in place, so `loop (acc = "", …) next
(concat(acc, piece), …)` builds output in amortised linear time. A loop state may carry an invariant,
`loop (i : i64{i >= 0} = 0, ...)`: the checker proves it holds initially and is
preserved by `next`, and uses it as a fact inside the loop. Integer arithmetic
wraps; floats are strict IEEE with no fused multiply-add, matching Rust,
except that `sum` over `f64` is order-free (the compiler may reassociate and
vectorise it; the parallel version already sums in chunks).
An else-if chain comparing one variable or field against four or more integer,
byte or `u16` constants (including `match` on an enum) lowers to one LLVM
`switch`, a jump table when dense (`NEO_SWITCH=0` keeps the branches).
In-place writers (`set`, `byte_write_le`, `byte_copy`) mark their result as the
only reference to its buffer; moves through records, helpers and loop states
keep that mark unless the binding was shared, so later writes skip the
reference-count test (`NEO_UNIQUE=0` disables). A loop state written only by
such writers (possibly chosen by `if`) is made unique once at loop entry.

Facts the checker has in scope: parameter refinements; `lo <= i < hi` for the
variable of `arr(i in lo..hi)` and `sum(i in lo..hi)`; the condition inside
the `then` branch and its negation in `else`, and the left operand of `&&`
while checking the right; loop invariants, plus the loop condition inside
`next` and its negation at `yield`; `len(xs) >= 0`. About opaque terms it
knows: a call's return refinement, the invariant of the state a loop yields,
both branches of an `if`, `x * y >= 0` when both factors are non-negative
(and `x * y >= y` when `x >= 1`), `b*q <= a < b*q + b` for `q = a / b` with a
positive constant `b` (and `q >= 0` when `a >= 0`), `-b < a % b < b`, and
`sum … >= 0` when the body is, `0 <= bit_and(x, c) <= c` for a constant
`c >= 0`, and that two reads of the same field of one binding (`r.pos`) are
equal. Anything else needs a `check`. What a call's return refinement says
holds only where the call ran: such facts carry the path conditions under
which they were produced (branches, short-circuits, loop and comprehension
guards, `check`s), and prove a goal only when its conditions include them;
an `if` passes each branch's facts on, guarded by that branch's condition.

Array sizes: a parameter's size must be a variable (`xs : Arr i64 n`); a
return type may use a variable, an expression over parameters, `_`, or a
constant written in parentheses, `Arr i64 (16)`.

### Effects and the Neo runtime

`fn` declares a pure function. `effect fn` permits I/O, foreign calls and
trusted low-level memory operations. A pure function cannot call an effect
function; neither can a refinement or a comprehension body. An effectful
entry point is explicit:

```text
effect fn main (port : i64{port > 0, port < 65536}) -> i64
  = serve(port, handle)
```

`serve(port, handler)` calls `ax_serve`, implemented in `runtime/http.neo`.
The accept/read/write loop, HTTP framing, partial writes, keep-alive,
pipelining and connection cleanup are Neo code. `handler : Arr u8 n ->
Arr u8 _` remains a pure function from request bytes to response bytes.
The implementation starts one worker process per configured CPU, with
`NEO_THREADS=N` selecting a worker count. Each owns a dense vector of up to
1,024 connections, with a 64 KiB input limit per connection. A shared accept
turn and inherited notification socketpairs assign connections round-robin.
Each event can batch up to 64 responses, with a 256 KiB flush threshold. Retained
output buffers handle partial writes and backpressure; buffered complete
requests keep progressing even when no new input bytes arrive.
x86-64 Linux serves with io_uring (Linux 6.1+): one ring per worker, one
`io_uring_enter` per loop for every queued receive and send, and at most one
operation in flight per connection. Where a ring cannot be created (older
kernels, Docker's default seccomp profile) and on ARM64 Linux, it uses
persistent, level-triggered epoll registrations, with write readiness
enabled only for queued output or buffered requests. Registrations survive
ordinary requests; closing connections compacts their slots only after the
entire ready batch has been handled. `NEO_HTTP_URING=0` selects epoll,
`NEO_HTTP_URING=1` requests io_uring on ARM64 too and reports a fallback, and
`NEO_HTTP_POLL=1` selects the previous Linux ppoll backend for diagnostics.
All backends use direct kernel syscalls and the same HTTP framing, batching and
worker assignment.
It supports Content-Length bodies; duplicate/invalid Content-Length and
Transfer-Encoding are rejected by closing the connection. The previous
`NEO_SERVE=threads` mode has been removed. Compute comprehensions dispatch
with shared-address clone/wait workers for allocation-free numeric regions on
Linux and isolated fork/wait workers elsewhere, outside request handlers. Worker
startup is more expensive than a persistent thread pool; numerical outputs
are regression-tested separately. Process groups should be terminated as a
unit; HTTP children also exit after detecting that their parent has died.
The historical `RESULTS-http.md` files describe the earlier C runtime;
`RESULTS-http-native-2026-10-23.md` describes the intermediate single-worker
Neo runtime. The `RESULTS-http-kernel-*` reports describe this runtime.

`extern fn` declares a platform ABI symbol. External signatures use `i32`,
`i64`, `f64`, `ptr`, and `unit` (void return); variadic declarations use `...`.
`export` exposes a Neo function with an unmangled symbol name. Platform
constants and syscall wrappers live in `runtime/platform_macos.neo` and
`runtime/platform_linux.neo`. `extern` remains an opt-in interoperability
feature; the shipped runtime has no extern declarations. A libc-free Linux
link rejects unresolved extern symbols. For example, kernel process identity
is available without a foreign library:

```text
effect fn main () -> i64 = rt_getpid()
```

The systems boundary is intentionally **trusted and unchecked**: `ptr_add`,
`load_u8/i32/i64/ptr`, `store_u8/i32/i64/ptr`, `view`, `data`, `addr`,
`invoke_region` and `handler_call` are only available in effect functions.
The kernel boundary additionally exposes `syscall6`, `fork_syscall`,
`stack_alloc`, `runtime_state`, pointer/integer conversions and volatile
memory operations. Those primitives generate LLVM instructions/assembly;
they do not embed another language's runtime. Darwin's raw syscall ABI is
platform-specific, and its required loader dependency remains explicit.
On x86-64, `aes_round_low/high`, `aes_final_round_low/high` and
`carryless_mul_low/high` are AESENC, AESENCLAST and PCLMULQDQ on 128-bit
values held as two i64 halves; functions using them, and the callers they are
inlined into, are compiled with those target features. `aes_hardware()` says
whether the CPU has them (it needs an effect function but not `unsafe`). On
other targets it is false and the instructions trap.
They do not prove pointer validity, lifetimes, callback signatures or foreign
contracts. `data(array)` borrows a named byte array (or a static literal);
the pointer must not outlive or invalidate that storage. `view(ptr, length)`
creates a borrowed byte array with a nonnegative length obligation. Normal
array bounds and refinement checking still applies to the runtime's pure
HTTP parser and to application code. This is an initial systems interface,
not a complete memory-safe FFI or effect capability system.

See
[examples/http.neo](examples/http.neo): `GET /` is hello-world, `GET /smooth/N`
runs 32 stencil passes and returns JSON, `POST /nbody` parses a JSON body and
runs the n-body model, and `GET /page/N` server-renders an HTML catalog
byte-identical to React's `renderToString` output for the same page. Request
parsing, integer and float formatting, JSON field lookup, HTML escaping and
concatenation are all Neo code there, with every array access proven in
range. Results: `RESULTS-http-compute.md` and `RESULTS-http-ssr.md`.

`main` takes `i64` arguments from argv; its refinements are checked at the
program boundary, which is the only place a runtime check is inserted
without the program asking for one.

ZetaDB, a separate project written in Neo, implements a persistent byte-key/value
store with atomic batches, persisted indexes, compaction, numeric aggregation and crash recovery, using kernel calls
directly. Its own reports compare it with embedded SurrealDB on document loading,
updates/deletes, fresh-process reopen and independently checked aggregation.

## Layout

```
neoc/syntax.py   lexer, AST, parser (the textual projection)
neoc/graph.py    content-addressed hashing (de Bruijn variables)
neoc/linear.py   linear integer constraints, Fourier-Motzkin, counterexamples
neoc/check.py    type checker and obligation discharge
neoc/llvm.py     LLVM IR backend, region outlining, ownership, SoA records
neoc/vectorize.py cross-iteration vectorisation of scalar sums and affine array bodies
neoc/kernel_workers.py Linux raw-clone stack switch for allocation-free regions
neoc/fold.py     compile-time evaluation of pure calls with literal arguments
neoc/inline.py   inlining of concat-producing calls, concat flattening
neoc/cli.py      build / check / graph, build cache
runtime/core.neo  allocator/free lists, memory operations, formatting, fork scheduling
runtime/http.neo multicore connection assignment, HTTP framing and response batches
runtime/http_linux.neo persistent Linux epoll registrations and ready-event dispatch
runtime/platform_*.neo ARM64 kernel syscall numbers/wrappers; no library declarations
examples/         mandel.neo, stencil.neo, http.neo, sieve.neo, nbody.neo, unproven.neo
bench/            Rust, Go, Bun and React (Bun and Node) equivalents; run.py (compute), http/run.py (wrk)
experiments/      agent-loop: four agents writing Neo from the README alone
RESULTS.md        compute benchmarks; RESULTS-http.md, RESULTS-http-compute.md,
                  RESULTS-http-ssr.md: HTTP; RESULTS-agent-loop.md: the agent experiment
Dockerfile.linux-test  builds and verifies on Ubuntu (clang 18, Neo kernel runtime)
```

## Not done yet

Ownership is a per-scope uniqueness analysis, not full region inference; a
variable used twice as a whole is borrowed everywhere and its buffer is copied
by `set`. Records now hold owned arrays and nested records, and arrays may contain managed
values. Managed-element comprehensions currently stay sequential. Safe-code
signed arithmetic now traps on overflow; explicit wrapping operations are available. `llvm.assume` emission of proven facts is
implemented (`NEO_ASSUME=1`) but off by default: LLVM 21 did not use them to
vectorise and they cost 15 percent on the stencil. The prover is
Fourier-Motzkin over linear constraints; non-linear index expressions need a
`check`. A general effect system (tokens for I/O,
files, time) needs finer-grained capabilities beyond the current `effect fn`
boundary. Vectorisation covers scalar sums and affine scalar array bodies;
loops with array state still dispatch each pass separately.

The freestanding runtime targets ARM64 macOS/Linux and x86-64 Linux. CLI float output uses a
17-significant-digit scientific formatter, not a complete correctly rounded
decimal conversion implementation. The standard library includes generic records/alternatives, scoped resources,
JSON, files, collections, DNS, bounded IPv4 TCP/UDP, a kernel poll reactor,
streaming HTTP/1.1 and experimental pure-Neo TLS with RSA/P-256 authentication.
Optional application protocols live in a separate package workspace.
Full WebRTC/Opus support remains unfinished. An
OS-enforced capability sandbox and self-hosted compiler are not implemented. The
allocator and syscall/pointer boundary are trusted code rather than fully
proved memory-safe implementations.

## License

Neo is licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))
- MIT license ([LICENSE-MIT](LICENSE-MIT))

at your option. Unless you explicitly state otherwise, any contribution
intentionally submitted for inclusion in Neo, as defined in the Apache-2.0
license, shall be dual licensed as above, without any additional terms or
conditions.
