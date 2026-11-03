# HTTPS speed work, part three (2026-11-03)

Follows part two (`2026-11-03-https-speed.md`, commit 801dc53). Part two's numbers are unchanged. Same machine
type: Vultr voc-c-2c (AMD EPYC-Milan, 2 vCPU), Linux 6.8. The Go net/http server and every client run on CPU 0.
The method is `python3 bench/fetch/run.py --rounds 5 --schemes https`, run twice with the EC key and once with
`--key rsa`. These runs also built 801dc53's `fetch.neo` and ran it as one more client, interleaved with the
others. "801dc53" and "now" therefore share every round, the server process and the certificates.

Summary: both handshake targets from part two are met.

- **Full handshake.** A new connection with a full handshake is level with Bun at /hello: 807 and 802 µs against
  806 and 805 µs, and under the 815 µs part two measured for Bun.
- **Resumption.** A resumed connection is 35 µs ahead of Rust at /hello: 546 and 543 µs against 579 and 580 µs.
- **Kept-alive connections** are ahead of Rust, Go and Bun at every size, 1 MiB included: 1,408 µs against 1,474
  to 1,593 µs.
- **Large bodies on new connections** still trail Bun: 49 to 57 µs at 1 MiB, down from 266 µs in part two.
- **RSA certificates.** A new connection now beats Bun at every size.

## End to end (p50)

Each EC cell gives both EC runs, A / B.

| | Neo 801dc53 | Neo now | Rust reqwest | Go net/http | Bun fetch | Neo now, RSA key |
|---|---:|---:|---:|---:|---:|---:|
| HTTPS new connection, GET /hello | 924 / 925 µs | 807 / 802 µs | 579 / 580 µs ¹ | 1,148 / 1,145 µs | 806 / 805 µs | 1,954 µs |
| HTTPS new connection, GET /64k | 1,098 / 1,093 µs | 952 / 961 µs | 793 / 791 µs ¹ | 1,343 / 1,345 µs | 947 / 945 µs | 2,171 µs |
| HTTPS new connection, GET /1m | 2,562 / 2,573 µs | 2,345 / 2,328 µs | 2,097 / 2,076 µs ¹ | 3,159 / 3,261 µs | 2,287 / 2,279 µs | 3,721 µs |
| HTTPS new connection, resumed, GET /hello | 682 / 676 µs | 546 / 543 µs | 579 / 580 µs ¹ | — | — | 540 µs |
| HTTPS new connection, resumed, GET /64k | 852 / 849 µs | 698 / 708 µs | 793 / 791 µs ¹ | — | — | 701 µs |
| HTTPS new connection, resumed, GET /1m | 2,319 / 2,311 µs | 2,088 / 2,093 µs | 2,097 / 2,076 µs ¹ | — | — | 2,082 µs |
| HTTPS keep-alive GET /hello | 46 / 46 µs | 39 / 39 µs | 75 / 75 µs | 89 / 88 µs | 86 / 84 µs | 40 µs |
| HTTPS keep-alive GET /64k | 153 / 153 µs | 144 / 145 µs | 177 / 182 µs | 193 / 196 µs | 188 / 184 µs | 142 µs |
| HTTPS keep-alive GET /1m | 1,477 / 1,488 µs | 1,408 / 1,410 µs | 1,513 / 1,593 µs | 2,082 / 1,949 µs | 1,474 / 1,524 µs | 1,404 µs |
| HTTPS one request per process (median) | 2.18 / 2.15 ms | 2.13 / 2.14 ms | 2.69 / 2.73 ms | 4.31 / 4.34 ms | 15.36 / 15.30 ms | 3.25 ms |

The EC runs are `2026-11-03-022158` (A) and `2026-11-03-022358` (B). The RSA run is `2026-11-03-022557`. Its other
clients on a new connection:

| RSA run | /hello | /64k | /1m |
|---|---:|---:|---:|
| Bun | 1,960 µs | 2,219 µs | 4,077 µs |
| Go | 2,313 µs | 2,511 µs | 5,019 µs |
| Neo 801dc53 | 2,078 µs | 2,315 µs | 3,906 µs |
| Rust ¹ | 574 µs | 799 µs | 2,083 µs |

One request per process with the RSA key: Rust 3.81 ms, Go 5.52 ms and Bun 16.71 ms.

¹ As in part two, the Rust client reuses one reqwest `Client` with pooling off, so rustls resumes the TLS 1.3
session. Compare it with "Neo, resumed".

## What changed

- **TLS contexts are reused** (`runtime/handles.neo`, `std:tls`).
  - Before, each connection mapped a fresh 128 KiB context and unmapped it on close. Releasing a context clears
    every page, so the next fresh mapping took 32 page faults, and every close paid an `munmap`.
  - Now a dropped context, already cleared past its length word, goes to a per-process cache of four, and the
    next connection takes it from there.
  - A forked child forgets the cache along with the rest of the runtime state it resets.
- **Fixed-base X25519 key generation** (`std:x25519`).
  - `x25519_public` no longer runs the 255-step ladder on u = 9. It computes k·B on edwards25519 (ref10's
    `ge_scalarmult_base`, regrouped) and maps the result to u = (Z+Y)/(Z−Y).
  - The clamped key becomes 64 signed radix-16 digits in −8..8. Row j of a generated 15 KiB table holds 1..8
    times 16^(4j)·B as (y+x, y−x, 2dxy). Four passes each add one digit's multiple from every row, with four
    doublings between passes.
  - Each digit reads all eight entries of its row under masks and negates the result under a mask. No branch or
    memory address depends on the key. The shared-secret ladder is unchanged.
  - `tests/generate_crypto_fields.py` writes the table and checks every entry against the curve equation. Limb
    bounds keep every product input below 3·2^52.
  - Key generation now takes 14.2 µs per key instead of 38.0 µs (2.7×; best of 5 runs of 2,000 keys, pinned to
    CPU 1).
- **Owner checks use a cached process id** (`runtime/handles.neo`).
  - Each handle lookup for a process-owned kind compared the entry's owner with a fresh `getpid`. The runtime is
    freestanding, so that was a real system call, and system calls are expensive on this CPU with its SRSO
    mitigation on.
  - A 1 MiB HTTPS download on a new connection made 346 of these calls.
  - The id is now cached. `rt_fork`'s child clears the cache and reads its own id.
- **Fewer clock reads per TLS record** (`std:tls`).
  - Each socket read checked the deadline first, which is also a system call here.
  - The readiness wait still checks the deadline whenever the socket is empty.
  - With data already queued, the deadline is now checked before a context's first read and every eighth read
    after that, so a peer that keeps the socket full still runs out of time.

Client CPU per request and page faults, from `perf stat` (task clock), two runs each. Both builds ran against the
same server in one session.

| | 801dc53 | now |
|---|---:|---:|
| new connection /hello (1000 requests) | 580 / 580 µs, 32.2 faults | 459 / 473 µs, 0.2 faults |
| new connection, resumed /hello (1000) | 379 / 390 µs, 32.2 faults | 259 / 255 µs, 0.2 faults |
| new connection /1m (200) | 1,614 / 1,608 µs, 35.3 faults | 1,380 / 1,377 µs, 3.5 faults |
| keep-alive /1m (200) | 876 / 872 µs | 794 / 803 µs |

System calls for 100 new-connection /1m requests (`strace -c`):

| | 801dc53 | now |
|---|---:|---:|
| `getpid` | 34,611 | 1 |
| `clock_gettime` | 4,408 | 1,511 |
| `mmap` | 121 | 22 |
| `munmap` | 102 | 2 |
| `read` | 3,406 | 3,508 |
| `ppoll` | 403 | 405 |
| `sendto` | 300 | 300 |

An intermediate build had only the context reuse and the fixed-base table. It accounted for most of the /hello
and resumed drop. The process-id cache and the clock change accounted for the kept-alive drop and about half of
the new-connection /1m drop.

## Correctness

These ran on the final tree on the bench box (x86-64):

- **`./neo test`:** 40 native cases, 0 failed. This includes the new `tests/x25519_base_test.neo`: the RFC 7748
  key pairs, clamping edge cases, and 256 chained keys checked against the ladder.
- **Fixed-base key generation against the ladder:** 100,000 keys from a SHA-256 chain, 0 mismatches.
- **Known-answer tests:** RFC 7748 (including 1,000,000 iterations) and RFC 8439 §2.8.2.
- **Wycheproof:** all of these pass.
  - x25519: 518
  - chacha20_poly1305: 325
  - ecdsa_secp256r1_sha256: 484
  - rsa_pss_2048_sha256_mgf1_32: 108
  - rsa_signature_2048_sha256: 257 (2 skipped for exponent or hash)
  - aes_gcm AES-128 with a 96-bit IV and a 128-bit tag: 67
- **`tls_resume_language`:** OpenSSL and Go resume over HTTP/1.1 and h2. Tampered and expired tickets fall back to
  a full handshake, and a wrong PSK is rejected.
- **`tls12_language`, `http2_language` and `http_keepalive`:** pass. `http_keepalive` covers TCP and TLS 1.3,
  including the body limit and silent-close retries.
- **`tls_web_language`:** OpenSSL including KeyUpdate. All 18 live sites answer, all of them over h2.

## Still short

- **Large bodies on new connections.** Against Bun on a new connection, Neo is 49 to 57 µs behind at /1m
  (2,345 / 2,328 against 2,287 / 2,279 µs) and 5 to 16 µs behind at /64k. Part two had it 266 µs behind at /1m.
  The body still costs about 110 to 140 µs more client CPU on a new connection than on a kept-alive one. That
  remainder has not been traced to a cause.
- **Full handshake: level with Bun, not ahead.**
  - In `perf record` of 2,000 full handshakes, the Neo client spends 37% of its samples in P-256 field products
    and the verify loop: two ECDSA verifications per handshake, for the certificate signature and
    CertificateVerify. SHA-256 compression takes another 7%.
  - Verification already uses wNAF-7 against a precomputed generator table and wNAF-5 for the key. What remains
    is the 256 doublings and the Montgomery product itself.
  - Neo's client already uses less CPU per full handshake than Bun's: 459 to 473 µs against 496 µs. The Go
    server, which shares CPU 0, spends about 11 µs more per Neo connection than per Bun connection (375.5 against
    364 ms per 1,000 handshakes), for reasons not yet found.
  - Going further on the client needs better carry-chain code generation in neoc (an add-with-carry builtin, or
    MULX/ADX selection) and SHA extensions. That was out of scope for this round, which changed no neoc code.
- **Resumed /1m** is level with Rust (2,088 / 2,093 against 2,097 / 2,076 µs), not ahead.
- Unchanged from part two: HTTP/2 runs one stream at a time, there is no 0-RTT and no TLS 1.2 resumption, and
  tickets do not outlive their `HttpClient`.
