# Neo 0.1 development contract

This document defines the implemented language and library surface, including its
limits. This is the first public release, `0.1.0`, rather than a stability or
security certification. Application and database examples are separate clients
of this language and are outside this change.

## Build and execution boundary

Python 3.11+ runs the compiler; Clang/LLVM and a linker generate machine code.
The build audit also requires `nm`; Linux dependency checks use `readelf`.
They are build tools. Linux ARM64 and x86-64 executables contain Neo code and
direct kernel interfaces, with no CRT, ELF interpreter, imported functions or
shared-library dependencies. Runtime memory allocation, memory copying, process
scheduling, HTTP, DNS and cryptography are Neo source. Some compiler primitives
emit target instructions, including syscalls, atomic operations and vector work.

ARM64 macOS requires a libSystem load command even though no library functions
are imported. It therefore does not satisfy the Linux zero-loader-dependency
claim. Neo requires an operating-system kernel; CPU and kernel ABI portability
must be implemented and tested per target. Build self-hosting is separate work.

Configuration and application input remain data: DNS may read `resolv.conf`, and
TLS receives explicit trust-anchor certificates. Neither loads executable code
or delegates protocol work to another process or library.

## Types, alternatives and errors

Primitive values are `i64`, `i32`, `u8`, `f64`, `bool` and `unit`. Arrays use
`Arr T n`; `_` is an existential length. Records have finite value layouts,
including owned arrays, unit payloads, empty records and nested records.
Recursive value types are rejected.

Record and function type parameters are specialized at compile time. Calls may
infer value-type shapes or use `name::<T,...>(...)`. Record constructors use
`Name::<T,...> { ... }`. Array lengths inferred through a type parameter become
existential; a caller's local size variable cannot escape into a record layout.
Declared array size binders and refinements retain their separate checks.

```neo
import "std:option"
type Box<T> = { value:T }
fn identity<T>(value:T) -> T = value
fn main() -> i64
  = let box=Box::<i64> { value=identity(42) } in
    match Some(box.value) { None => 0, Some(value) => value }
```

```text
42
```

`enum Choice<T> { Empty, Value(T) }` defines tagged alternatives. `match`
requires complete coverage, or a final `_` arm; duplicate, unknown, unreachable
and incorrectly bound alternatives are errors. Alternative storage is private.
The current representation stores a tag and initialized storage for every
alternative. It is not a compact maximum-payload union representation.

`std:option` supplies `Option<T>`, `Some`, `None`, `option_is_some`, `option_or`.
`std:result` supplies `Result<T,E>`, `Ok`, `Err`, `result_is_ok`, `result_or`.
Existing `BytesResult`, `IntResult` and optional-value records remain available.

Error propagation is a scoped continuation bind:

```neo
import "std:result"
fn positive(value:i64) -> Result<i64,Arr u8 _>
  = if value>0 then Ok::<i64,Arr u8 _>(value) else Err::<i64,Arr u8 _>("negative")
fn convert(value:i64) -> Result<Arr u8 _,Arr u8 _>
  = let number=positive(value)? in
    check number>0 in Ok::<Arr u8 _,Arr u8 _>("done")
fn main() -> i64
  = match convert(-1) { Ok(text) => 0, Err(text) => len(text) }
```

```text
8
```

`?` is supported on the value of `let name = result()? in continuation`.
The continuation returns a compatible Result error type and may change the
success type. It lowers to ordinary branches; it is not an exception, an
unrestricted return expression, or an unwinder. Generic bodies are checked when
specialized; unused generic declarations do not establish universal trait bounds.
Traits, automatic lexical closure capture and a self-hosted compiler remain
absent. Generic external/exported ABIs are rejected. Typed function values,
explicit capture records and typed resource references are described below.

## Values, effects and resources

Ordinary arrays and records have value semantics. Live aliases retain their
contents; the compiler borrows reads and moves unique buffers where safe.
`move` on a value-record parameter permits ownership transfer for mutation;
using an ordinary value again still requires a copy rather than a dangling alias.
Read-only length/index/field operations do not copy entire owned containers.
Disjoint final managed-field projections can transfer separately from an owned
record. The compiler clears each transferred field in the remaining owner;
later projection or whole-record uses keep the required buffers alive by copying.
Borrowed records cannot transfer their fields.

Effects are `fs`, `net`, `time`, `env`, `process` and `unsafe`. Explicit capability
lists are checked transitively. Raw pointers, syscalls and atomics require the
systems boundary; refinements and parallel comprehensions cannot perform effects.
Unrestricted `effect fn` remains compatible. This is not an OS permission sandbox.

`resource type File = { ... } drop destructor` defines an affine resource.
Its representation is private outside the defining module. Only that module can
construct owners. Resources must be bound with `using`; they cannot be copied
into arrays/records/enums, escape a scope, or be moved from an outer repeating
region. Parameters borrow by default; `move` transfers ownership and inserts a
callee scope. Use after a possible move, including a move in one branch, is an
error. Destructors borrow one resource in an effect function and return unit.
Cleanup runs exactly once for each owner, including conditional transfers, nested
using scopes and explicit destructor calls.

```neo
import "std:file"
effect(fs) fn main() -> unit
  = using file=open_file("/dev/null",0) in
    let status=file_status(file) in check status.ok in
    let result=read_file(file,32) in check result.ok in
    let output=print_out(concat("read ",int_text(len(result.value))," bytes\n")) in noop()
```

```text
read 0 bytes
```

Cleanup runs after normal results, branches and scoped Result error binds.
A fatal trap or `process_exit` terminates the process; it does not run user
destructors. The kernel releases process-owned descriptors and mappings. Peers
must use deadlines to detect crashed processes. Resource types are currently
nongeneric and cannot be nested inside Result; opening a File/Socket produces an
owner with a status operation, including failed-open owners that are safe to drop.

The standard library uses a 4,096-slot generational handle table. Stale tokens
cannot close a reused descriptor. Ordinary files, sockets and TLS contexts are
process-bound; forked children close inherited process-bound handles. Cancellation
and channel mappings are explicitly shared across fork. Table memory itself is
private and copied on write. Raw integer-fd APIs remain the explicit lower layer.

`process_fork` is a legacy low-level API with unsafe heap semantics. Its
`process` capability does not guarantee memory isolation. The current allocator uses
shared mappings for compiler worker outputs; raw fork does not provide isolation
for preexisting ordinary heap values. Do not mutate or release inherited ordinary
heap allocations in independently running raw-fork branches. The bounded channel
and cancellation APIs use explicit shared storage; compiler workers borrow inputs,
publish controlled outputs and join before returning. General isolated process
spawning remains future work.

## Collections and arithmetic

`std:vec` provides `Vec<T>`, empty/length/capacity/get/push/set/pop/clear. Slots
store initialized Option values and grow geometrically. `pop` discards the final
value and returns the updated vector. Aliases preserve ordinary value semantics.

`std:hashmap` provides `HashMap<K,V>`, empty/random/length/capacity/get/put/delete.
Keys are i64/i32/u8/bool or byte arrays; values may be owned finite value types.
SipHash-2-4, bounded linear probing, tombstones and occupancy-triggered rehashing
replace linear association lookup. Explicit seeds support reproducibility;
`hashmap_random::<K,V>()` obtains independent kernel seed words and returns a
typed Result. Fixed seeds, including compatibility `map_empty`, do not establish
resistance to chosen-input hash flooding. `std:collections` preserves the
integer-vector and string-map call APIs, using geometric append, heapsort and
a compact byte map. Its former public StringMap representation has changed.

`std:bytesmap` provides `BytesMap`, empty/random/length/capacity/get/put/delete,
with_capacity, storage_bytes and explicit compact operations. It is specialized for byte keys
and values; arbitrary generic values continue to use `HashMap<K,V>`. Each bucket
has two adjacent 64-bit words packing four signed 32-bit arena offsets, plus a
one-byte control plane (17 bytes per capacity slot). Full keyed SipHash-2-4
selects the bucket; seven fingerprint bits filter candidate comparisons, which
still compare complete keys. Empty and tombstone control values are distinct.
The map owns one byte arena. Rehashing recomputes hashes over ranges without
copying keys; lookup returns an independent owned byte array. Empty/binary keys
and ordinary alias semantics
are preserved. Equal/smaller replacements reuse their old value range; growing
replacements and deletion record discarded bytes. A later insertion compacts
when discarded bytes exceed both 64 KiB and half the arena. Explicit compaction
can reclaim them sooner. `storage_bytes` reports logical arena length, excluding
the table, capacity slack and allocator caches. The checked arena limit is
2,147,483,647 bytes per map;
exceeding it traps rather than truncating offsets. `map_empty` retains its prior
deterministic seeds; `bytesmap_random` is available for untrusted keys.

Released blocks larger than 1 MiB and at most 8 MiB share one reusable buffer.
A matching allocation reuses it; a mismatched large allocation or another
eligible release evicts the previous buffer. Blocks larger than 8 MiB are
unmapped on release, preventing obsolete map-table generations from remaining
resident. The representative 1M-element stencil buffer remains reusable; larger
repeated-buffer workloads may pay additional mapping costs. This caps only the
large-buffer cache, not total RSS: smaller size-class free lists and worker
stacks remain reusable. The cache is private per process and resets in forked
children. This changes retention, not value lifetimes or dependencies.

Pure internal calls returning no managed values may borrow array arguments
without blocking a later final ownership transfer. Array-returning, effectful,
external and explicit move parameters retain conservative ownership handling.

Internal functions can opt into `borrow` for managed array or record parameters,
including effectful functions: `effect(fs,unsafe) fn fd(borrow db:Database) -> i64`.
The caller retains ownership throughout the call; inspecting a borrowed record
does not deep-copy its arrays. Returning a borrowed managed value produces an
owned copy. Overlapping arguments retain value isolation (for example borrowing
an array while passing a modified copy in another argument). `borrow` is a
contextual parameter modifier, cannot combine with `move`, and is not an external
ABI or function-reference ownership contract. Use `move` for consumed builder
state and `borrow` for inspection. These are compile-time ownership rules and add
no runtime or shared-library dependency.
Small nonrecursive pure helpers are inlined before LLVM's cost model, exposing
checked bounds and lifetimes for optimization; `NEO_INLINE=0` disables this
alongside the existing literal/concat inlining. Ordinary overflow checks remain.
Decimal integer formatting is linear in digit count. Integer parsing uses
explicit wrapping arithmetic only after its existing digit/overflow guards.
`bytes_le16/32/64` provide checked little-endian loads from byte arrays without
raw pointers or imported memory routines.

Safe i64 arithmetic traps on overflow. Division truncates toward zero; remainder
has the dividend's sign. Explicit wrapping operations preserve modulo-2^64 bits.
Bitwise operations, logical shifts and arithmetic right shift operate on exact
64-bit patterns; shift counts are masked modulo 64. Casts to u8/i32 keep low bits.
Array bounds/division/refinement obligations must be proven or guarded by `check`.
`--allow-unproven` is an explicit unsafe experiment flag, not the release default.

`NEO_ALLOC_STATS=1` enables `std:debug` cumulative allocation requests and
requested-byte traffic. These are not live memory or RSS; counters are absent
from the default allocation path after optimization. Complexity tests enforce
geometric append, one sorting buffer and linear map allocation traffic.

## Processes, channels and time

Parallel pure computations keep the existing joined kernel-worker model. They
do not create a general thread runtime. Owned-element computations remain
sequential where child allocations cannot safely become parent pointers.
On Linux, the compiler also certifies allocation-free scalar/record computations,
including borrowed-array reads and nested scalar/record reductions, for joined
shared-address workers. Managed projections/construction, owned parameters,
array mutation, effects, recursion and unknown calls are rejected by that
certificate and retain the private worker path. Cheap certified bodies use a
work estimate to avoid worker startup for small ranges. Kernel worker-creation
failure runs the affected work sequentially before returning.

`std:channel` is a bounded single-producer/single-consumer queue across fork.
Capacity is 1..1,024 messages, each 0..4,096 bytes. A producer and consumer process
are claimed atomically; second processes receive an error. Acquire/release
publication makes complete messages visible in order. Try operations return
full/empty; blocking operations accept a monotonic deadline and Cancellation.
Linux uses direct futex wait/wake; macOS uses bounded sleeps. Polling intervals
are at most 1 ms, subject to OS scheduling. Sender close drains queued messages
before EOF. Crash detection relies on deadlines. Only SPSC is supported; channels
copy message bytes instead of exposing arbitrary heap values to peers. Raw fork
still has the inherited shared-mapping limitation described above.

`std:time` distinguishes Unix wall timestamps from monotonic durations/deadlines.
Linux uses CLOCK_MONOTONIC; Apple Silicon uses its architectural timebase and
frequency. Socket/channel deadlines do not depend on wall-clock corrections.
`std:random` uses kernel getrandom/getentropy, including from an empty root.

## DNS, HTTP and experimental TLS

`std:dns` resolves IPv4 addresses, validates response IDs/questions and compressed
names, follows bounded CNAME chains, and retries truncated UDP replies over TCP.
Resolver addresses may be supplied explicitly or read from `resolv.conf`. IPv6,
DNSSEC, search-domain policy and DNS caching are not implemented.

`std:socket` supplies scoped nonblocking IPv4 TCP owners. `std:http_client`
supports GET, HEAD, POST, PUT, PATCH, DELETE and OPTIONS; it handles Content-Length,
chunked and EOF framing, interim responses and bounded trailers. Streaming yields
chunks before the peer closes, with a 32 KiB working buffer and configurable body
limit up to 1 GiB. Header/trailer limits are 16 KiB; chunk/trailer lines are
bounded. Ambiguous framing, malformed fields and truncation are errors. The
compatibility POST API stays available. HTTP/1.1 response headers and explicit
keep-alive framing are available; the optional sibling `axon-libs/http-client`
package adds bounded pool bookkeeping. HTTP/2 is available over TLS through
`std:https_client` (below); redirects remain absent.
The server retains kernel workers and response batching.

`std:tls` is an experimental TLS 1.3 client library outside the compiler core.
It implements X25519, ChaCha20-Poly1305, SHA-256/HMAC/HKDF, RSA-PSS-SHA256
or P-256 ECDSA CertificateVerify and SHA-256 certificate-chain verification
with RSA or P-256 keys, including mixed issuer chains. Trust anchors
are explicit Certificate values. Checks include certificate signatures, validity,
DNS/IP SAN, restricted wildcards, CA/path limits, key usage, EKU and unsupported
critical extensions. TLS read/write sequences are private, bound to one Socket,
limited per key and updated by authenticated KeyUpdate. Records and handshake
messages are bounded. Corrupt authentication releases no plaintext. Authenticated
close-notify is distinct from transport truncation; use `tls_close` for graceful
shutdown. Context cleanup clears active key storage; the process keeps up to
four cleared contexts for later connections and releases the rest.
TLS 1.3 sessions resume with PSK tickets (psk_dhe_ke only): `tls_take_ticket`
returns the newest NewSessionTicket with its PSK, bound to the host name and
suite, and `tls_connect_resume` offers it once, within its lifetime, with a
binder; a server that declines it gets a full handshake. `tls_resumed` reports
whether the certificate exchange was skipped. `tls_read_into` reads application
data into caller memory instead of a new array; over TLS 1.3 with AES-128-GCM
and the CPU's AES instructions, a record whose plaintext fits is opened straight
into it. More application data than the room given fails the session, and after
an error that memory may hold unauthenticated bytes.

This is a deliberately limited, unaudited implementation: no TLS 1.2 fallback,
client certificates, 0-RTT, AIA fetching,
OCSP/CRL revocation or general PKIX path construction. Ordered RSA chains with
SHA-256 signatures and exponent 65537 are supported at 2,048..4,096 bits. Unknown
critical extensions fail closed. The implementation and its secret-dependent
machine-code behavior have not received an independent cryptographic audit;
passing interoperability/vector tests is not a production security guarantee.
Source algorithms follow [RFC 8439](https://www.rfc-editor.org/rfc/rfc8439),
[RFC 7748](https://www.rfc-editor.org/rfc/rfc7748), and
[RFC 8446](https://www.rfc-editor.org/rfc/rfc8446).

## Modules, packages and tools

Imports are lexical. `import "a.neo" as a` exposes `a::function` and `a::Type`.
Declarations are public by default for compatibility; `private` hides them.
Unaliased imports keep transitive re-exports. Ambiguity, cycles and duplicate
aliases are errors. Canonical user names include package name/version/module
path; module identity is stable under project relocation. Standard/runtime ABI
names remain stable. Do not rely on generated specialization identifiers.

Local packages declare an exact `package.version` and dependencies such as
`math = { path = "../math", version = "1.2.3" }`. `import "pkg:math"` reads its
entry (default `src/lib.neo`); `pkg:math/sub` reads `src/sub.neo`. `neo pkg lock`
writes exact versions, source hashes and dependency edges. Verification rejects
changed dependency sources; editing root-package source does not require a lock
update. `neo pkg vendor` copies locked sources into `.neo/vendor`; later builds
need neither the original directories nor network access. Packages execute no
install/build scripts. There is no registry or range-version solver.

`neo lsp` speaks stdio LSP with full-document UTF-16 synchronization, checking of
unsaved buffers, completion, hover, definitions, symbols and formatting. Configure
an editor's generic LSP client to run that command. `neo check --library file.neo`
checks a module without main. Select `--diagnostic-format json` for structured
errors or `--diagnostic-format human` for source locations. `neo fmt`
normalizes token spacing while preserving deliberate line breaks, comments and
literal contents; it verifies lexical equivalence and is idempotent.

`neo version` reports the development version. `neo release -o bundle.tar.gz`
creates a deterministic compiler-source/tool bundle with a SHA-256 manifest,
fixed ownership/timestamps and no application examples. SOURCE_DATE_EPOCH may
set its timestamp. The native bundle builds programs with Clang and a linker.

## Compatibility and evidence

Development releases may change syntax, generated layouts and standard-library
internals. Source-level breaking changes must be called out, with tests and a
migration note; no binary ABI stability is promised. Exact package versions and
content hashes make dependency changes reviewable. Future stable minor releases
must preserve documented source APIs; breaking them requires a major version.

Run `neo test` for unit, documentation, native language, allocation-complexity,
network, cryptographic-vector, TLS and existing application regressions. OpenSSL,
Rust, Go and Bun are independent test/benchmark tools, not Neo runtime services.
Linux CI includes native ARM64 and x86-64 jobs, import/ELF audits, empty-root tests
and reproducible source bundles. A configured CI job is not evidence it ran;
local native and emulated results must be identified separately in reports.

Benchmarks retain outputs, warmups, shuffled trial order, CPU budgets, compiler
versions, source/binary hashes, raw times and footprint measurements. Allocation
profiles are separate instrumented builds. A win in one workload does not prove
universal language superiority; test safety and semantics before performance.


## Agent-core additions (2026-10-25)

`Fn(T,...)->R` is a pure function value. `Effect<fs,net>(T,...)->R` carries
explicit capabilities, checked again at every indirect call and through helper
functions. Capability order is immaterial. `function(named_function)` takes an
internal named function with no owned parameters or refinements. Effect targets
must declare their capabilities. Dependent or fixed array-length obligations
cannot be erased into function values: callback arrays use independent `_`
lengths. External/exported/variadic targets are rejected.

```neo
import "std:callback"
fn add(capture:i64,value:i64) -> i64 = capture+value
fn main() -> i64
  = let callback=closure::<i64,i64,i64>(function(add),35) in
    closure_apply(callback,7)
```

```text
42
```

`std:callback` supplies `Closure<C,A,R>` with an explicit capture value.
Captures can own arrays and records. Callback values can live in vectors,
queues, maps and records. There is no implicit lexical lambda capture or
language-level interface dispatch yet.

`std:arena` adds an affine `Arena` owner and copyable `Ref<Resource>` handles.
`adopt(owner,arena)` consumes a named resource owner. The arena retains its
payload and compiler-generated finalizer until explicit `ref_release(ref)` or
arena cleanup. Freed slots are reusable; each occupant has a fresh generation.
An old handle cannot access or close a replacement. `ref_live(ref)` checks
liveness. `borrow_ref(ref)` is allowed only as an immediate borrowed call
argument; it cannot be stored, returned, moved or escape as an owner. A stale
borrow traps. Checked handles can be stored in agent state and used in recursive
resource graphs, while recursive by-value layouts remain invalid.

Arena capacity is 1..65536 live resources; generation exhaustion and adoption
into a full or closed arena trap. Finalizer effects must fit fs/net/process.
Arena references are process-bound. Cleanup runs over occupied slots in
reverse slot order. Managed metadata is retained during a borrow. These are
single-process resource identities, not a garbage collector, synchronized
shared mutable heap or thread-safe reference counting.

`std:queue` supplies a bounded generic FIFO. Rejected pushes retain the queue;
popped slots release their managed contents. `std:task` supplies bounded task
admission and cooperative explicit-state callbacks. A tick visits each admitted
task once; completed tasks are removed and timers gate execution. Cancellation
stops admission and wakes all tasks for cleanup. A shutdown deadline bounds the
scheduler's outer loop and reports unfinished tasks. Callback code must return:
there is no preemption, stackful task, M:N scheduler or compiler-generated async
state machine. Blocking I/O must not run in a step. `std:reactor` waits on up to
4096 socket/process/listener/datagram interests together using kernel poll.
Interests are non-owning generational tokens; stale descriptor reuse is rejected.

`socket_try_read`/`socket_try_write` report EAGAIN without blocking.
`std:socket_cancel` offers socket reads/writes with monotonic deadlines and
cancellation, using readiness waits of at most 10 ms. Kernel scheduling and user
callbacks can add latency. Cancellation-aware connect, DNS (including TCP
fallback), TLS handshake and TLS reads/writes propagate the same token. CPU
cryptography itself is not preempted by cancellation.

`std:process` launches an absolute executable with explicit argument and
environment arrays, no shell or PATH lookup. It owns separate full-duplex
stdin/stdout and stderr streams, nonblocking reads/writes, polling exit status
and TERM/KILL signals. Scope cleanup kills and reaps a live child. An exec
failure becomes exit 127. Launch vectors and strings use private mappings so
parent cleanup cannot invalidate the child's arguments; Neo-opened files and
sockets are close-on-exec. Argument/environment limits are 1024 entries each,
64 KiB per entry and 1 MiB total each. `process_close_input` idempotently
half-closes stdin while preserving stdout/stderr. Process groups, working-directory
options and a high-level communicate API remain absent.

`std:fs` adds remove, mkdir, rename and `fs_atomic_replace`. Replacement uses an
exclusive 0600 temporary file beside the destination, complete write, file sync,
rename and parent-directory sync. If the directory sync fails after rename,
the caller receives an error with an uncertain durability outcome. It does not
provide a path sandbox, cross-file transaction or protection against changing
parent symlinks. Fatal traps do not run user destructors.

JSON now has typed scalar/array/object constructors, serialization, bool/float
accessors and ordered object keys (including duplicates). Values retain sealed
validation and depth limits. `std:numbers` provides finite binary64 conversion:
exact rational comparison and ties-to-even decimal parsing, and a 17-digit
round-trip formatter preserving signed zero. It rejects nonfinite numbers and
inputs longer than 4096 bytes. It is not a shortest-decimal or high-throughput
replacement for optimized numeric parsing. `float_bits` and `bits_float` are
pure bitcasts. `std:math` adds finite log/log1p/exp and nonnegative-base pow;
these routines are approximate, not a complete correctly-rounded math library.

`std:base64` implements strict canonical padded Base64 and unpadded Base64url.
`std:url` implements percent encoding/decoding and form '+' handling.
`std:datetime` parses numeric-offset RFC3339 into UTC milliseconds and formats
years 0001..9999; extra fractional digits are truncated. It has no leap-second
or timezone database. `std:unicode` provides checked scalar iteration, Unicode
16.0 full default case folding, letter/number categories and Unicode White_Space
splitting, with tables compiled into the executable. Locale case mapping,
normalization and grapheme segmentation remain absent.

`HttpIO<C>` adds typed transport callbacks to the existing bounded HTTP/1.1
reader. `http_start_io` accepts validated custom headers, including provider
authorization, and rejects reserved framing/header injection. `std:https_client`
supplies cancellation-aware plain TCP and experimental TLS transports over
arena references, and `HttpClient`, a keep-alive client for one origin:
`http_send(arena,client,...)` returns the response and the client, whose
connection lives in the caller's arena and is reopened after any response
that does not leave it reusable. A GET, HEAD or OPTIONS request that finds a
reused connection closed is sent once more; other methods return the error.
`http_client_disconnect` closes the connection but keeps the newest TLS session
ticket, so the next connection resumes; `http_client_close` forgets it. Over TLS
the client offers h2 and http/1.1 with ALPN and, when the server picks h2, speaks
HTTP/2 (`std:http2`, one stream at a time on a kept-alive connection) with HPACK
(`std:hpack`: static and dynamic tables, Huffman coding), CONTINUATION, padding,
flow control in both directions, PING, RST_STREAM and GOAWAY; a request the
server refused or never processed is sent again. Plain connections stay
HTTP/1.1 (no h2c). Over HTTP/1.1 a Content-Length body is read into one buffer
of the announced size: from a plain socket with reads as large as it has queued,
over TLS with `tls_read_into`. `HttpExchange` carries the response's header fields and the
protocol used. `std:sse` incrementally frames SSE data/event/id/retry fields
across arbitrary chunks, supports BOM/CR/LF/CRLF, and bounds pending event data.
Feed it decoded HTTP body chunks; EOF does not dispatch an unterminated event.
The optional sibling `axon-libs/http-server` package adds an explicit chunked
streaming writer and SSE flush; `axon-libs/http-client` supplies bounded
origin-keyed pool bookkeeping. Server-side HTTP/2, h2c, server push, redirects,
proxies, compression and IPv6 remain absent. TLS has cancellation-aware I/O and RSA/P-256 authentication,
but remains experimental without a security audit or general PKIX support.

These additions support bounded text-agent components and protocol prototypes.
They do not establish production parity with Go/Rust networking. The separate
`../axon-libs` source workspace now implements WebSocket clients, sequential
stdio MCP, a Responses text/tool profile, PCM/G.711, RTP, STUN and SRTP/SRTCP.
A full pure-Neo Opus audio codec, DTLS/ICE/TURN/SDP/SCTP/WebRTC stack, wider
provider adapters and complete agent behavior remain unfinished. Protocols stay
in libraries rather than becoming compiler syntax. See that workspace's explicit
readiness matrix for supported profiles and gaps.

## Bounded mutable protocol storage and crypto

`std:buffer` supplies a scoped, process-bound private mapping with checked byte
and unaligned i64 reads/writes, clear, copied read snapshots and zero-on-drop
cleanup. Typed Arena references can retain its owner without exposing a raw
pointer. Allocation errors are explicit; Arena capacity exhaustion still traps.
`std:datagram` supplies scoped nonblocking IPv4 UDP, including ephemeral ports,
zero-length datagrams, bounded receive, deadline and cancellation. IPv6 is absent.

`std:aes` provides experimental table-free AES-128, CTR and GCM (12-byte nonce,
16-byte tag), with authentication before plaintext release. `std:p256` provides
uncompressed P-256 key validation, ECDH and DER ECDSA SHA-256 signatures using
RFC6979 deterministic signing. `std:sha1` supplies legacy SHA-1/HMAC-SHA1 for
WebSocket/STUN/SRTP compatibility. These source algorithms and their generated
machine code have not been independently audited for cryptographic security or
constant-time behavior. Independent NIST/RFC and Go vectors are regression
evidence, not security certification.

A resource factory may use a temporary owner internally and return a distinct
new resource. Cleanup still occurs once; returning the temporary itself or a
borrowed resource remains rejected. Widened array loop states have one arbitrary
current-length identity per iteration, so explicit bounds guards prove access
without retaining an invalid assumption about the initial array length.


Managed arrays now retain immutable backing buffers when copied. Each descriptor
contains data, length, an ownership flag and a control pointer (32 bytes on the
64-bit targets). A mutation detaches a shared buffer; nested array children are
retained until they themselves change. Record arrays keep their SoA layout, so
length-changing pushes still relocate that layout. Reference counts use native
atomic operations, or plain ones in a natively compiled program that cannot
start a thread (objects kept or prepared ahead of the program test at run time
whether a thread has been started); final release destroys owned children and returns the block
to Neo's allocator. There is no tracing GC or external runtime dependency.

Static literals use an immortal control marker and need no heap allocation when
retained; mutations detach them. Unsafe raw views are copied when an owning
value is required. Explicit borrows do not retain or copy buffers.
Unsafe pointer writes remain the caller's responsibility. All native library
objects must be rebuilt together after this descriptor ABI change; compiler and
source hashes invalidate the existing build/library caches. Source-level value
semantics remain unchanged, including snapshot/alias isolation.

`byte_slice(bytes,start,end)` returns an owning immutable byte range and checks
`0 <= start <= end <= len(bytes)` at runtime. `str_slice` keeps its existing
empty-result behavior for invalid bounds. Slices retain a shared backing block,
including when their original owner is dropped; raw external views are copied.
Offset slices detach before mutation or growth. A small retained slice may keep
a larger source allocation alive, as with other shared-buffer designs.

`byte_read_le(bytes,offset,width)` reads a little-endian word with width 1, 2,
4 or 8. It checks the complete range against the array's logical length, including
slices, before an unaligned load. Widths below 8 return a nonnegative `i64`; width
8 preserves the signed 64-bit bit pattern. Other widths and invalid offsets trap.
It borrows its source, allocates nothing, and supports allocation-free parallel
reductions. `bytes_le16`, `bytes_le32` and `bytes_le64` use this primitive.

`byte_copy(destination,offset,source)` returns a byte array with the source bytes
written at the given offset. `byte_write_le(destination,offset,value,width)`
writes the low `width` bytes of an i64 in little endian order. Width must be
between zero and eight, and both operations check that the complete write fits.
Aliases and overlapping slices retain their original contents. Unique owned
buffers may be updated in place; shared buffers and literals detach first.

Automatic array allocations use a private heap when `NEO_THREADS=1`, with
separate slab/free-list pools. Worker-enabled execution retains shared backing
memory. Raw `ax_alloc` remains shared across fork for systems-level callers.

`json_object_key_at(object,index)` and `json_object_value_at(object,index)`
iterate cached object spans without building a key list or searching by name.
They preserve source order, including duplicate members. Out-of-range indices
and non-objects return the existing error/absence result types. Name lookup
continues to select the last matching member.


Borrowed managed records in internal calls use a pointer to live caller storage
(or a temporary when required), avoiding a copy of the record descriptor.
Indirect pure calls use the same convention; external/exported and consumed
parameters keep their existing ABI. Native objects must be rebuilt together;
content-addressed compiler/library caches invalidate automatically.

Private heap blocks use process-local reference counts; shared worker blocks
retain atomic counts. The allocation's immutable flags select the counter mode,
so shared values remain safe across worker processes.

`count_trailing_zeros(value)` counts low zero bits in an i64 bit pattern and
returns 64 for zero. It lowers to an LLVM intrinsic with defined zero behavior,
without importing a runtime function. The JSON scanner uses bounded word reads
and this operation to locate quotes, escapes, controls and non-ASCII bytes;
Unicode and escape validation remain unchanged.

`file_write_parts(fd,parts)` fully writes an array of byte spans in order,
skipping empty spans. It returns the total byte count or a cumulative error
position after a partial write. Like `file_write`, it retries interrupted writes;
it does not imply a sync. Durable applications still explicitly sync after all
parts have been written.


`utf8_valid_range(bytes,start,end)` validates UTF-8 within a borrowed byte span.
It returns false for invalid bounds or incomplete code points at either edge,
even if adjacent backing bytes would complete a sequence. ASCII word scanning
avoids allocating slices; `utf8_valid(bytes)` uses the same implementation for
the whole array.


`hashmap_get_or_insert(map,key,default)` returns `{map,value,inserted}`. A present
key retains its existing value; a missing key inserts the default and sets
`inserted=true`. Lookups share one probe in the common case, and observers end
before mutation so an unaliased map keeps geometric growth. Returned managed
values and held map snapshots retain ordinary immutable value semantics.


`byte_equal(a,b)` compares two byte arrays by value. The native implementation
checks lengths, recognizes identical storage and compares full words before a
bounded byte tail. `str_equal` uses it. Arguments retain value isolation even
when a later argument consumes and modifies the first argument's backing array.
No C `memcmp` or other runtime import is required.


Structured JSON output also supports a checked `JsonWriter`: begin/end an array
or object, write keys and typed string/int/bool/null values, and finish with a
`JsonResult`. Invalid transitions, unfinished containers, invalid UTF-8 and
excessive nesting produce an error. Retained writers and results have immutable
value semantics.

`json_fragment(value)` prepares a validated value with cached nesting depth;
`json_writer_fragment` can insert it repeatedly without reparsing its bytes.
`json_writer_fragment_finish` returns a fragment without creating object member
indexes; `json_fragment_json` creates those indexes when a full JSON object is
needed. Array element counts and duplicate object names retain their ordinary
JSON behavior.

For repeated object layouts, `json_object_encoder(keys)` validates and quotes
member names once. `json_encode_object(encoder, values)` accepts an array of
`json_encode_int`, `json_encode_bool`, `json_encode_null`, `json_encode_string`
and `json_encode_fragment` values. It checks field count, UTF-8 and nesting,
allocates the sized output once, and writes signed integers directly into it.
Duplicate keys remain in input order. This is a standard-library serializer;
there are no new runtime imports.

`bytes_match_at(text, offset, pattern)` compares a bounded byte span without
allocating a slice. It returns false for negative or out-of-range offsets and
preserves byte value semantics, including empty patterns at the end of a string.


`json_view(value)` retains validated JSON without building child object indexes.
`json_object_cursor`/`json_object_next` and
`json_array_cursor`/`json_array_next` advance only across validated member and
element boundaries. Object cursors preserve duplicate keys in source order;
ordinary lookup still selects the last key. `json_view_atom` and
`json_view_text` inspect scalars; `json_view_json` materializes a value with the
usual object indexes when needed. Cursors, views and their retained source have
immutable value semantics, including repeated reads from the same cursor and
advancing a cursor already at the end.


`std:bitset` provides an immutable growable `BitSet` for nonnegative positions.
`bitset_insert` accepts indices through 2,147,483,647; it checks that bound.
`bitset_remove`, `bitset_has`, `bitset_len` and `bitset_next` support deletion,
membership, cardinality and ordered iteration. Negative query indices return
false/None, and removing absent positions preserves the set. Storage grows in
64-bit words up to the highest inserted position; removing bits retains that
capacity. Retained copies preserve their values while uniquely owned updates
reuse storage. Dense and sparse independent tests cover 1M positions and bound
allocation growth on both one and four workers.


`json_tokens(value)` traverses validated JSON without rescanning an entire
container before entering it. `json_tokens_next` advances one token;
`json_tokens_skip` skips a compound value, and `json_tokens_take` returns its
validated `JsonView` together with the following cursor. Token kinds 1–6 match
JSON kinds, 7 identifies member names, and -5/-6 close arrays/objects. The cursor
reports nesting depth and retains its source. Scalar inspection uses
`json_token_atom`, `json_token_text` and `json_token_text_equal`. Advancing a
uniquely owned cursor transfers its source owner without allocating per token;
retained cursors remain immutable. Independent tests cover full token streams,
escaped/duplicate names, parser depth limits and 100k-object allocation growth.

Structured JSON writers format integers directly into their output and grow the
container stack as needed. Scalar integer arrays require logarithmic allocation
counts as their output grows; they do not allocate a decimal string per value.

### Data persistence barrier

`file_sync_data(fd) -> IntResult` persists file contents and metadata needed to
retrieve them, including changed file length. Linux uses the kernel `fdatasync`
syscall directly; Darwin retains the full hardware-cache barrier. Changes to
directory entries still require syncing the containing directory. Existing
`file_sync` and `rt_sync_full` behavior is unchanged. The new operation does not
promise persistence of unrelated inode timestamps. Errors propagate through
`IntResult`, including invalid handles and writeback failures.

### Loop field last-use optimization

The compiler plans owned record-field transfers separately for a loop update
and its final yield: the latter observes the replacement state, rather than the
previous iteration. Existing aliases and overlapping call borrows still force
copy-on-write when needed. This changes no language semantics or runtime ABI.
Linux x86 state storage is page-aligned for BSS-only ELF loader compatibility;
other supported target layouts retain their previous alignment.
