# HTTPS bodies without the extra copies (2026-11-03)

After 0.1.3, `memcpy` and `memset` were 15% of the samples of a client that downloads 1 MiB bodies over one
kept-alive HTTPS connection on x86-64. Each TLS record was decrypted into a new, zero-filled array. The unread
bytes behind the record in the wire buffer were moved to its front. The record's plaintext was then appended to
the body, which grew by reallocating.

With this change, each record is decrypted straight into one body buffer. The buffer is sized from
`Content-Length` and allocated without being filled. Plain HTTP bodies are read into the result in the same way,
without the final copy.

**Result.** Measured against `main` (v0.1.3, `bdabf90`) on the same box, in the same interleaved rounds:

| Row | x86-64 before → after | AArch64 before → after |
|---|---:|---:|
| HTTPS /1m, new connection | 2,198 → **2,012 µs** (−8.5%) | 3,477 → **3,235 µs** (−7.0%) |
| HTTPS /1m, kept-alive | 1,253 → **1,084 µs** (−13.5%) | 1,858 → 1,891 µs (+1.7%) ¹ |
| HTTPS /1m, resumed | 1,926 → **1,751 µs** (−9.1%) | 2,966 → **2,754 µs** (−7.2%) |
| HTTPS /64k, kept-alive | 133.3 → **122.9 µs** (−7.8%) | 193.4 → **183.3 µs** (−5.2%) |
| HTTP /1m, kept-alive | 291.7 → **258.9 µs** (−11.2%) | 453.9 → **424.2 µs** (−6.5%) |
| Client CPU, 100 kept-alive HTTPS /1m | 70.6 → **56.7 ms** (−20%) | 104.7 → **88.4 ms** (−16%) |

Each latency cell is the median, over interleaved rounds (7 for /1m, 5 for /64k), of each client's per-request
p50. Every response in every round was checked to be 200 with a body of the expected size.

¹ **The AArch64 kept-alive p50 did not move, but the total time did.** In "Where the time goes", 100 kept-alive
requests take 223.0 ms before and 206.3 ms after (−7.5%). The client's CPU time falls by the same 16 ms, the Go
server's stays at 117 ms, and CPU 0 is busy throughout. The per-request p50 moved by +1.7%, −0.8% and −2.8% in
three separate A/Bs, while the mean fell 6%.

Raw data, scripts, machine details and binary hashes are in `bench/core/results/2026-11-03-https-copies/`.

## Machines

Both boxes were temporary: created for this round and destroyed afterwards. They have 2 vCPUs, half the size of
the thin-rows boxes. The harnesses pin the server and every client to CPU 0, so none of these rows needs more.

| | x86-64 | AArch64 |
|---|---|---|
| Instance | Vultr `voc-c-2c-4gb-50s-amd`, Amsterdam | Scaleway `BASIC2-A2C-4G`, fr-par-2 |
| CPU | AMD EPYC-Milan, 2 vCPUs = 1 core × 2 SMT threads | Ampere Altra (Neoverse-N1), 2 vCPUs, one thread per core; `aes` and `pmull` in HWCAP |
| OS | Ubuntu 24.04.5, Linux 6.8.0-147-generic | Ubuntu 24.04.5, Linux 6.8.0-147-generic |
| Toolchains | clang 18.1.3, Go 1.25.14, Rust 1.99.1, Bun 1.3.13 | same |

- "Before" is `main` at v0.1.3 (`bdabf90`). Its `fetch.neo` executable is the one `bench/fetch/run.py` built on
  the box.
- "After" is that commit plus this change. Its executable was built on the box with `./neo build … --no-cache`.
- The x86-64 box is an EPYC-Milan, not the EPYC-Rome of the thin-rows report, and every row here ran on 2 vCPUs
  instead of 4. The "before" numbers therefore differ from that report's "after" numbers. Every before/after pair
  in this report was measured on one box.

## HTTPS and HTTP

`scripts/ab.sh PATH SIZE COUNT` runs every client in turn, in each round:

- main's `fetch.neo` and this tree's, each on a new connection, kept-alive and resumed;
- Bun `fetch`, new and kept-alive;
- Rust reqwest, new (which resumes, ²) and kept-alive;
- Go net/http, new and kept-alive.

It runs them over HTTPS and then over plain HTTP. `scripts/medians.py` prints each client's median and range.
Cells are the median of the rounds' p50, in µs.

### GET /1m, 100 requests per client per round, 7 rounds (`ab-1m.log`)

| | Neo main | Neo now | Bun | Rust | Go |
|---|---:|---:|---:|---:|---:|
| **x86-64** | | | | | |
| HTTPS new connection | 2,198 | **2,012** | 2,326 | 2,091 ² | 3,256 |
| HTTPS kept-alive | 1,253 | **1,084** | 1,620 | 1,585 | 2,209 |
| HTTPS resumed | 1,926 | **1,751** | — | 2,091 ² | — |
| HTTP new connection | 650.3 | **621.5** | 889.8 | 849.4 | 1,654 |
| HTTP kept-alive | 291.7 | **258.9** | 477.6 | 351.5 | 935.4 |
| **AArch64** | | | | | |
| HTTPS new connection | 3,477 | **3,235** | 3,908 | 3,030 ² | 5,517 |
| HTTPS kept-alive | 1,858 | 1,891 | 2,492 | 1,959 | 3,363 |
| HTTPS resumed | 2,966 | **2,754** | — | 3,030 ² | — |
| HTTP new connection | 679.3 | **559.7** | 1,148 | 907.6 | 2,366 |
| HTTP kept-alive | 453.9 | **424.2** | 810.8 | 618.3 | 1,554 |

The HTTPS rows' ranges do not overlap, except AArch64 kept-alive: 1,829–1,897 µs before and 1,735–1,998 µs
after, split between rounds near 1,750–1,860 and rounds near 1,950–2,000. The AArch64 plain HTTP rows are
noisier: the new-connection ranges are 587–726 µs before and 493–637 µs after.

### GET /64k, 400 requests per client per round, 5 rounds (`ab-64k.log`)

| | Neo main | Neo now | Bun | Rust | Go |
|---|---:|---:|---:|---:|---:|
| **x86-64** | | | | | |
| HTTPS new connection | 952.1 | **933.0** | 958.9 | 807.3 ² | 1,379 |
| HTTPS kept-alive | 133.3 | **122.9** | 201.4 | 182.5 | 196.9 |
| HTTPS resumed | 690.3 | **668.1** | — | 807.3 ² | — |
| HTTP new connection | 190.7 | 188.6 | 275.5 | 332.8 | 327.5 |
| HTTP kept-alive | 62.1 | **58.7** | 120.2 | 94.7 | 136.9 |
| **AArch64** | | | | | |
| HTTPS new connection | 1,849 | 1,841 | 2,037 | 1,461 ² | 2,802 |
| HTTPS kept-alive | 193.4 | **183.3** | 302.3 | 248.8 | 305.9 |
| HTTPS resumed | 1,297 | 1,280 | — | 1,461 ² | — |
| HTTP new connection | 223.5 | 216.4 | 359.2 | 406.5 | 428.8 |
| HTTP kept-alive | 95.3 | **90.4** | 182.0 | 132.8 | 208.3 |

A 64 KiB response is four or five records, so the handshake dominates the new and resumed rows, and they move
by 0.4–3%.

² As in the earlier HTTPS reports, the Rust client reuses one reqwest `Client` with pooling off, so rustls
resumes the TLS 1.3 session. Its new-connection row is compared with Neo's resumed row.

### Margins

The margin is the best other client's median divided by Neo's. New connections are compared with Bun and Go,
which do a full handshake. Resumed rows are compared with Rust (²).

| Row | x86-64 before → after | AArch64 before → after |
|---|---:|---:|
| HTTPS /1m new connection | 1.06× → 1.16× (Bun) | 1.12× → 1.21× (Bun) |
| HTTPS /1m kept-alive | 1.26× → 1.46× (Rust) | 1.05× → 1.04× (Rust) |
| HTTPS /1m resumed | 1.09× → 1.19× (Rust) | 1.02× → 1.10× (Rust) |
| HTTPS /64k new connection | 1.01× → 1.03× (Bun) | 1.10× → 1.11× (Bun) |
| HTTPS /64k kept-alive | 1.37× → 1.49× (Rust) | 1.29× → 1.36× (Rust) |
| HTTPS /64k resumed | 1.17× → 1.21× (Rust) | 1.13× → 1.14× (Rust) |
| HTTP /1m new connection | 1.31× → 1.37× (Rust) | 1.34× → 1.62× (Rust) |
| HTTP /1m kept-alive | 1.21× → 1.36× (Rust) | 1.36× → 1.46× (Rust) |

The thinnest rows are now x86-64 HTTPS /64k on a new connection (1.03× over Bun) and AArch64 HTTPS /1m kept-alive
(1.04× over Rust).

### Where the time goes (`account.log`)

`scripts/account.sh` runs 100 kept-alive HTTPS GET /1m per client process, 12 interleaved rounds. For each
process it records:

- the wall time;
- the client's CPU time, from `getrusage`;
- the Go server's CPU time over the same span, summed over its threads from `/proc/…/schedstat`.

Medians, in ms per 100 requests:

| | Wall | Client CPU | Server CPU | Rest of CPU 0 | p50 µs |
|---|---:|---:|---:|---:|---:|
| x86-64 main | 146.0 | 70.6 | 74.3 | 1.1 | 1,265 |
| x86-64 now | **129.5** | **56.7** | 71.9 | 0.6 | 1,092 |
| AArch64 main | 223.0 | 104.7 | 116.9 | 0.6 | 1,942 |
| AArch64 now | **206.3** | **88.4** | 117.5 | 0.5 | 1,887 |

The server and the client share CPU 0 and keep it busy, so the wall time is the sum of their CPU times. On both
boxes, the client's saving reaches the wall time in full. The wall-time ranges do not overlap on x86-64
(141.5–160.1 ms before, 126.0–134.0 after). On AArch64 they overlap by 2 ms (217.5–257.6 before, 202.1–219.8
after).

On AArch64 the per-request p50 moved less than the total, in all three runs that measured it:

| AArch64 kept-alive /1m, p50 µs | Before | After |
|---|---:|---:|
| `ab-1m.log` (7 rounds, all clients) | 1,858 | 1,891 |
| `keep-ab-noperf.log` (15 rounds, main and now only) | 1,965 | 1,951 |
| `account.log` (12 rounds) | 1,942 | 1,887 |

In `keep-ab-noperf.log` the mean per request fell from 2,247 to 2,116 µs (−5.9%). Why the AArch64 p50 does not
follow the mean was not found.

### Instructions, cycles and the profile

`scripts/keep-ab.sh` runs the same 100 kept-alive requests per process under `perf stat`, 15 interleaved rounds
(`keep-ab.log`). Medians per process:

| | Task-clock ms | Cycles | Instructions | Context switches | Page faults |
|---|---:|---:|---:|---:|---:|
| x86-64 main | 92.2 | 234.2 M | 459.7 M | 462 | 700 |
| x86-64 now | **78.8** | **175.5 M** | **302.0 M** | 500 | **440** |
| AArch64 main | 136.0 | 298.2 M | 516.5 M | 796 | 695 |
| AArch64 now | **116.7** | **236.8 M** | **422.2 M** | 930 | **435** |

The client now finishes each record sooner and blocks on the socket more often, which accounts for the extra
context switches: +8% on x86-64 and +17% on AArch64.

`scripts/prof.sh` profiles one process of 200 kept-alive requests (`prof.log`):

| Share of samples | x86-64 main | x86-64 now | AArch64 main | AArch64 now |
|---|---:|---:|---:|---:|
| GCM kernel (`gcm_open_kernel`) | 42.1% | 43.0% | 44.9% | 60.5% |
| `memcpy` | 9.6% | 1.3% | 16.5% | 1.0% |
| `memset` | 3.7% | — | 2.7% | — |
| Kernel copy to user space | 4.0% | 5.8% | 8.0% | 9.2% |

"—" means the symbol is not among the top 14 entries. On the body's path, the kernel's copy from the socket into
the wire buffer is the one copy left besides the decryption itself.

The GCM kernel became cheaper per byte on x86-64 and dearer on AArch64. By share × cycles ÷ 209,715,200
bytes:

- **x86-64:** 0.92 → 0.76 cycles per byte. The 8-block decrypt step is shorter: 304 → 276 instructions, with the
  same AES and carry-less multiply counts.
- **AArch64:** 1.20 → 1.32 cycles per byte. The kernel now stores into the 1 MiB body buffer instead of a fresh
  16 KiB array, and on the N1 it seems to absorb store misses that `memcpy` used to take. That was not
  isolated. The net is still 21% fewer cycles.

One request per process is unchanged (`oneshot.log`, GET /hello over HTTPS, 400 interleaved runs each):

- x86-64: 2.178 ms before, 2.169 ms after;
- AArch64: 3.566 ms before, 3.564 ms after.

The full harness, `bench/fetch/run.py`, was also run on main (3 rounds) and on this tree (5 rounds) on both
boxes; its tables are in `fetch-main/` and `fetch-new/`. Those were separate runs, and the AArch64 box drifts
between runs (p99 up to 13 ms in the new tree's run), so the interleaved tables above are the comparison.

## What changed

Before, after the kernel's copy into the TLS wire buffer, a 1 MiB HTTPS body went through these steps:

1. each record's plaintext array was zero-filled, then decrypted into;
2. the unread bytes behind each record were moved to the front of the wire buffer;
3. each record's plaintext was appended to the body;
4. the body grew by reallocating, copying what it held so far.

Now each record is decrypted straight into one body buffer of the announced `Content-Length`, which is
allocated once and never zero-filled.

### `byte_uninit` (`neoc/check.py`, `neoc/llvm.py`)

`byte_uninit(length)` is a new systems builtin. It returns an owned byte array of that length without filling it.
`arr(i in 0..n) u8(0)` emits a fill loop; `byte_uninit` emits only the allocation.

- It needs `unsafe`, like `view` and the other pointer builtins: its contents are unspecified until the caller
  has written every byte through `data()`.
- Its length is an obligation (`length >= 0`). The result's type carries that length, so later accesses are
  bounds-checked against it as for any other array.

### GCM into caller memory (`stdlib/aes.neo`)

The GCM kernel used to thread its output array through the loop state and return it with the tag. It now writes
through a `ptr`:

- `aes128_gcm_seal_fast` and `aes128_gcm_open_fast` allocate their result with `byte_uninit`, so the zero-fill
  of every sealed and opened record is gone.
- `aes128_gcm_open_into(key, nonce, aad, wire, dst)` opens into memory the caller owns and returns the count.
  When the tag does not match, it returns error 74. The bytes already written to `dst` are then unauthenticated,
  and the caller discards them. Without AES instructions it opens with the portable code and copies.

### TLS records opened in place (`stdlib/tls.neo`)

- **`tls_read_into(socket, session, dst, room, deadline)`** reads application data into `dst[0..room)` instead
  of a new array.
  - **Direct path.** A TLS 1.3 AES-128-GCM record whose plaintext fits in `room`, on a CPU with AES
    instructions, is opened where it lies in the wire buffer, straight into `dst`. The inner content type is found
    by scanning back over the padding.
  - **Handshake messages and alerts** that arrive on the direct path are passed to the same code as before.
  - **Every other record**, including TLS 1.2 and ChaCha20-Poly1305 records, goes through `tls_read` and is
    copied.
- **A record larger than `room`** fails the session (27), since the rest of its plaintext would have nowhere to
  go.
- **The wire buffer is compacted lazily.** It used to move the unread bytes to its front after every record. It
  now keeps a consumed offset, and compacts only when the free space after the unread bytes can no longer hold a
  whole record.

### Content-Length bodies (`stdlib/http_client.neo`, `stdlib/https_client.neo`)

- **Over TLS,** `http_read_length_body_tls` allocates one `byte_uninit` buffer of the announced size. It copies in
  what the header read already buffered, and fills the rest with `tls_read_into`.
- **Over plain TCP,** `http_read_length_body` already read the body with large reads, but into a separate
  buffer that was then copied into the result. It now reads into the result itself.
- **Unchanged:** chunked bodies, bodies without a length, bodies larger than the response limit, and HTTP/2.

### Tests

- **`tests/http_large_body.py`** (new) serves Content-Length bodies from 1 byte to 1 MiB over four transports:
  TCP, TLS 1.3 with AES-128-GCM, TLS 1.3 with ChaCha20-Poly1305, and TLS 1.2. It checks each body by length and
  FNV-1a hash. Its requests cover:
  - sizes on both sides of a 16 KiB record;
  - a body sent in 997-byte writes;
  - a server that closes halfway (error 5, after which the next request reconnects);
  - a server that sends 10 bytes more than it announced (error 27 over TLS).

  On a CPU with AES instructions it asserts that both TLS 1.3 suites were negotiated, so both the in-place path
  and the copying path ran.
- **`tests/test_systems.py`** checks that `byte_uninit` needs `unsafe`, that its length must be proven
  non-negative, and that it lowers to an allocation with no fill loop.
- **`tests/tls_language.py`** expected ChaCha20-Poly1305 as the client's first choice on every target but
  x86-64. Since 0.1.3, Linux AArch64 with AES and PMULL offers AES-128-GCM first, and on this round's AArch64
  box `tls_web_language.py` failed on that stale expectation. The test now expects AES-128-GCM there.

## Correctness

On both boxes, with this tree:

- **The suites this change touches pass** (`tests.log`):
  - 31 unit tests in `tests.test_systems` and `tests.test_proved_checks`;
  - `http_large_body`, `http_keepalive`, `aes_language` (with `aes_hardware()` true), `tls_language`,
    `tls12_language`, `http2_language`;
  - `tls_web_language`, against live sites.
- **The `verify.yml` steps pass** (`scripts/ci.sh`; `ci.log`):
  - `./neo test`: 31 Bun tests, server-rendering parity with React on 1 and 4 workers, and 40 native cases;
  - the freestanding HTTP smoke test from an empty root;
  - a reproducible `neo release`;
  - the empty-root language, crypto and TLS fixtures.

## macOS

Nothing ran on macOS. `bench/fetch/fetch.neo` builds there with this change.

On macOS, `aes_hardware()` is false, so `tls_read_into` takes the copying path for every record. It still
removes the body's appends and growth copies. Plain HTTP bodies are read into the result as on Linux. Neither
was measured on macOS.

## Still open

- **AArch64 kept-alive p50.** The total time and the CPU time fall, but the per-request p50 does not; see
  "Where the time goes".
- **The GCM kernel on the N1** costs 10% more per byte when it writes into the body buffer.
- **Chunked bodies** still go through the stream buffer and the appends.
