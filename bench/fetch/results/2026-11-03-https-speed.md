# HTTPS speed work, part two (2026-11-03)

Follows `2026-11-02-https-speed.md`. Same machine type: Vultr voc-c-2c (AMD EPYC-Milan, 2 vCPU), Linux 6.8.
Go net/http server and each client on CPU 0. `python3 bench/fetch/run.py --rounds 5` (EC) and `--key rsa`.
"Before" is the "after" column of the 2026-11-02 report.

Summary: kept-alive HTTPS is now at or ahead of Rust reqwest, Go and Bun at every size (1 MiB: 661 MiB/s, level
with Bun, ahead of Rust's 633). A full handshake on a new connection beats Go but is still 122 µs behind Bun. TLS
1.3 resumption and HTTP/2 (via ALPN, falling back to HTTP/1.1) are new; resumed connections are 110 µs behind
Rust's.

## End to end

| | Neo before | Neo after | Rust reqwest | Go net/http | Bun fetch | Neo after, RSA key |
|---|---:|---:|---:|---:|---:|---:|
| HTTPS keep-alive GET /hello (p50) | 46 µs | 48 µs | 75 µs | 88 µs | 88 µs | 48 µs |
| HTTPS keep-alive GET /64k (p50) | 284 µs | 154 µs | 186 µs | 201 µs | 187 µs | 158 µs |
| HTTPS keep-alive GET /1m (p50) | 3,470 µs | 1,512 µs | 1,579 µs | 1,835 µs | 1,509 µs | 1,511 µs |
| HTTPS keep-alive 1 MiB throughput (from p50) | 288 MiB/s | 661 MiB/s | 633 MiB/s | 545 MiB/s | 663 MiB/s | 662 MiB/s |
| HTTPS new connection, GET /hello (p50) | 1.26 ms | 937 µs | 585 µs ¹ | 1.16 ms | 815 µs | 2.13 ms |
| HTTPS new connection, GET /64k (p50) | 1.56 ms | 1.10 ms | 814 µs ¹ | 1.38 ms | 948 µs | 2.36 ms |
| HTTPS new connection, GET /1m (p50) | 4.82 ms | 2.62 ms | 2.13 ms ¹ | 3.33 ms | 2.35 ms | 3.99 ms |
| HTTPS new connection, resumed, GET /hello (p50) | — | 695 µs | 585 µs ¹ | — | — | 694 µs |
| HTTPS new connection, resumed, GET /64k (p50) | — | 857 µs | 814 µs ¹ | — | — | 865 µs |
| HTTPS new connection, resumed, GET /1m (p50) | — | 2.38 ms | 2.13 ms ¹ | — | — | 2.39 ms |
| HTTPS one request per process (median) | 2.50 ms | 2.24 ms | 2.82 ms | 4.47 ms | 15.72 ms | 3.39 ms |
| HTTP keep-alive GET /1m (p50) | 283 µs | 292 µs | 368 µs | 1.01 ms | 452 µs | 306 µs |
| HTTP new connection, GET /1m (p50) | 653 µs | 662 µs | 860 µs | 1.60 ms | 893 µs | 669 µs |

Before: `2026-11-02-191122` (EC). After: `2026-11-03-012146` (EC) and `2026-11-03-012513` (RSA). Other clients are
from the after EC run. With the RSA key, the other clients' new-connection /hello numbers are Rust 593 µs ¹,
Go 2.39 ms and Bun 2.01 ms. HTTPS keep-alive /1m means (over 5 rounds): Neo 1.62 ms, Bun 1.77 ms, Rust 1.67 ms,
Go 1.85 ms; p99: Neo 2.40 ms, Bun 3.57 ms, Rust 2.95 ms, Go 3.44 ms.

¹ The Rust client reuses one reqwest `Client` with pooling off, so rustls resumes the TLS 1.3 session: no
certificate verification and no server signature. Compare it with "Neo, resumed". "Neo" makes a new
`HttpClient`, and so a full handshake, for each request, as Go and Bun do.

## Primitives (Neo, one op, best of 5, pinned to CPU 1)

| | before | after | speed-up |
|---|---:|---:|---:|
| X25519 scalar multiplication | 93.5 µs | 37.8 µs | 2.5× |
| P-256 key generation | 181.1 µs | 99.7 µs | 1.8× |
| P-256 ECDH | 181.9 µs | 100.3 µs | 1.8× |
| ECDSA P-256 sign (SHA-256) | 217.1 µs | 127.5 µs | 1.7× |
| ECDSA P-256 verify (SHA-256) | 188.6 µs | 95.6 µs | 2.0× |
| RSA-2048 PSS verify | 133.9 µs | 63.4 µs | 2.1× |
| RSA-2048 PKCS#1 v1.5 verify | 131.1 µs | 59.8 µs | 2.2× |
| RSA-4096 PSS verify | 522.8 µs | 243.9 µs | 2.1× |
| P-384 ECDSA verify ² | 2.21 ms | 0.25 ms | 8.8× |
| TLS record open, 16 KiB (ChaCha20-Poly1305 → AES-128-GCM) | 34.4 µs | 6.62 µs | 5.2× |
| TLS record seal, 16 KiB (ChaCha20-Poly1305 → AES-128-GCM) | 35.9 µs | 6.37 µs | 5.6× |
| AES-128-GCM open, 1 MiB | — | 421 µs (2.49 GB/s) | |
| AES-128-GCM seal, 1 MiB | — | 403 µs (2.60 GB/s) | |
| Portable AES-128-GCM open, 16 KiB (no AES-NI) | 8.86 ms | 8.86 ms | |

Both columns come from the same run on the same box: "before" is a build of the 2026-11-02 tree, "after" a build
of this one. ChaCha20, Poly1305 and SHA-256 are unchanged (1.61 ms, 0.63 ms and 2.93 ms per MiB).

² The `TIME` lines of `tests/p384_language.py`, before and after. A Let's Encrypt ECDSA chain (`x509_verify`, two
P-384 verifications) went from about 4.5 ms to 0.5 ms.

## What changed

- **neoc: x86-64 AES-NI and PCLMULQDQ builtins.** `aes_round_*`, `aes_final_round_*` and `carryless_mul_*` work
  on 128-bit values split into two `i64` halves. They need the `unsafe` effect, compile to `aesenc`/`aesenclast`/`pclmulqdq`
  in functions marked with the `+aes,+pclmul,+sse4.1` target features, and trap on other targets.
  `aes_hardware()` is the CPUID check that guards them.
- **AES-128-GCM** (`std:aes`): eight counter blocks encrypted with their rounds interleaved, and GHASH over
  eight precomputed powers of H with Karatsuba carry-less products and one reduction per eight blocks. The
  portable fixed-work AES-GCM stays as the fallback for CPUs without AES-NI.
- **TLS suite order.** The client offers AES-128-GCM first when `aes_hardware()` is true, and ChaCha20-Poly1305
  first otherwise (TLS 1.3 and TLS 1.2).
- **X25519**: radix-2^51 field with `mul_high` (5 limbs, 128-bit products from `wrapping_mul` + `mul_high`,
  which LLVM merges into one `mul`).
- **P-256**: four 64-bit limbs, Montgomery with R = 2^256 and a product-scanning field multiply generated by
  `tests/generate_crypto_fields.py`. Secret scalars keep the constant-time fixed 4-bit window. Verification uses
  wNAF-7 for G against a 32-entry affine table and wNAF-5 for Q, and a binary extended GCD for s⁻¹ (s is public).
- **P-384**: six 64-bit limbs, field-specialized Montgomery arithmetic and wNAF verify (generated by
  `tests/generate_p384_fields.py`).
- **RSA**: fused CIOS Montgomery over 64-bit limbs, R² from doublings and squarings.
- **TLS 1.3 resumption** (PSK tickets, psk_dhe_ke only, no 0-RTT). `tls_take_ticket` returns the newest
  NewSessionTicket with its PSK, bound to the host name and suite, and `tls_connect_resume` offers it once with a
  binder (recomputed after a HelloRetryRequest). A declined, tampered or expired ticket falls back to a full
  handshake. `HttpClient` keeps the newest ticket across reconnects (`http_client_disconnect`); `http_client_close`
  forgets it. The bench has a new "Neo, resumed" row: one `HttpClient`, a new TCP connection per request, every
  handshake after the first resumed. That is what the Rust client does in the "new connection" rows.
- **Incremental transcript hashing** (`sha256_start`/`sha256_absorb`/`sha256_finish`): each TLS 1.3 transcript
  block is compressed once instead of once per hash point, and the TLS 1.2 session hash is computed once.
- **HTTP/2 over TLS** (`std:http2`, `std:hpack`). The client offers h2 then http/1.1 with ALPN and speaks HTTP/2
  when the server picks it: one stream at a time, HPACK with static and dynamic tables and Huffman decoding,
  CONTINUATION, padding, flow control, PING, RST_STREAM, GOAWAY with reconnect, and a retry of refused streams.
  Plain connections and servers without h2 stay on HTTP/1.1. The bench server is HTTP/1.1, so the bench rows
  measure HTTP/1.1.
- **KeyUpdate fix.** KeyUpdate derived a 32-byte traffic key whatever the suite, so an AES-128-GCM session failed
  its first record after a KeyUpdate. Offering AES first exposed it; `tls_web_language.py` now runs an OpenSSL
  KeyUpdate case per suite.

## Correctness

On the final tree (box, x86-64):
- `./neo test` (39 native cases, 0 failed) and every step of `.github/workflows/verify.yml`: the empty-root HTTP
  smoke test, the reproducible release bundle and the empty-root language, crypto and TLS binaries.
- RFC 7748 (including 1,000,000 iterations), RFC 8439 §2.8.2, and Wycheproof x25519 (518),
  chacha20_poly1305 (325), ecdsa_secp256r1_sha256 (484), rsa_pss_2048_sha256_mgf1_32 (108),
  rsa_signature_2048_sha256 (257, 2 skipped for exponent or hash) and aes_gcm AES-128 with 96-bit IV and 128-bit
  tag (67, through both the AES-NI and the portable paths).
- `tls_language`, `tls12_language`, `tls_resume_language` (OpenSSL and Go resume, both suites, HelloRetryRequest
  and stateless cookie; tampered and expired tickets fall back; a wrong binder is rejected), `http2_language`
  (Go's HTTP/2 server, and a scripted server for PING, SETTINGS, padding, priority, CONTINUATION, trailers,
  RST_STREAM, GOAWAY and connection errors),
  `tls_web_language` (OpenSSL including KeyUpdate under both suites; 18 of 18 live sites answer, all of them over h2),
  `x509_web_language`, `http_keepalive` and `p384_language` (1,643 ECDSA verifications differential against Go).

## Still short

- **Full handshake against Bun.** Neo is ahead of Go on every new-connection row and ahead of everyone at one
  request per process, but 122 µs behind Bun at /hello (937 vs 815 µs). Client CPU per handshake (`perf stat`,
  1000 handshakes, two runs) is 370 µs user + 220 µs system for Neo and 305 + 177 µs for Bun. Neo spends about
  270 µs of its user time on 2 X25519 operations and 2 P-256 verifications. BoringSSL's assembly should need about
  half of that, so Neo's other handshake work already costs less than Bun's. The P-256 field product is about 280
  instructions (23 `mul`, 36 `adc`); hand-written MULX/ADX code is about 130. Closing this needs better code
  generation for carry chains in neoc (an add-with-carry builtin, or MULX/ADX selection), and a fixed-base X25519
  table for key generation.
- **Resumption against Rust.** "Neo, resumed" is 110 µs behind Rust at /hello (695 vs 585 µs). Per handshake:
  188 µs user + 197 µs system for Neo, 133 + 148 µs for Rust. The user-time gap is likely the X25519 pair
  (2 × 38 µs; psk_dhe_ke keeps the key exchange). The system-time gap most likely comes from the per-connection
  128 KiB TLS context: about 32 page faults per connection, one per page of a fresh mapping, plus the unmap on
  close. Reusing the context across connections should remove
  most of it, and it would help the full handshake too.
- **Large bodies on new connections.** Kept alive, 1 MiB is level with Bun and ahead of Rust and Go. On a new
  connection the body costs Neo about 180 µs more client CPU than on a kept-alive one (`perf stat`, 200 requests
  each way), so new-connection /1m trails Bun by 266 µs, against 122 µs at /hello. It is not page faults: the
  count does not change with the body size. It has not been profiled yet.
- **HTTP/2** runs one stream at a time and has no h2c or server push. The HPACK encoder uses no dynamic table and
  no Huffman coding. No 0-RTT, no TLS 1.2 resumption, and tickets do not outlive their `HttpClient`.
- **Compile time.** The TLS fixture takes about 50 s at `-O3` on this box. It was about 35 s before this round
  (AES-GCM, the new field arithmetic and P-384 are all large generated or unrolled code).
