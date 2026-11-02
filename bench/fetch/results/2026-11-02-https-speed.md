# HTTPS speed work, before and after (2026-11-02)

Same machine type as the other runs in this folder: Vultr voc-c-2c (AMD EPYC-Milan, 2 vCPU), Linux 6.8.
Go net/http server and each client on CPU 0. `python3 bench/fetch/run.py --rounds 5` (EC) and `--key rsa`.

## End to end

| | Neo before | Neo after | Rust reqwest | Go net/http | Bun fetch | Neo after, RSA key |
|---|---:|---:|---:|---:|---:|---:|
| HTTPS new connection, GET /hello (p50) | 62.01 ms | 1.26 ms | 568 µs ¹ | 1.14 ms | 802 µs | 2.33 ms |
| HTTPS one request per process (median) | 63.90 ms | 2.49 ms | 2.77 ms | 4.32 ms | 15.43 ms | 3.57 ms |
| HTTPS keep-alive GET /hello (p50) | 47 µs | 46 µs | 75 µs | 85 µs | 85 µs | 46 µs |
| HTTPS keep-alive GET /64k (p50) | 503 µs | 284 µs | 178 µs | 194 µs | 187 µs | 287 µs |
| HTTPS keep-alive GET /1m (p50) | 6.86 ms | 3.47 ms | 1.58 ms | 2.16 ms | 1.47 ms | 3.47 ms |
| HTTPS keep-alive 1 MiB throughput | 146 MiB/s | 288 MiB/s | 633 MiB/s | 462 MiB/s | 680 MiB/s | 288 MiB/s |
| HTTPS new connection, GET /1m (p50) | 69.03 ms | 4.82 ms | 2.09 ms ¹ | 3.20 ms | 2.27 ms | 5.96 ms |
| HTTP keep-alive GET /1m (p50) | 676 µs | 283 µs | 347 µs | 1.04 ms | 448 µs | 282 µs |
| HTTP new connection, GET /1m (p50) | 936 µs | 653 µs | 848 µs | 1.64 ms | 847 µs | 649 µs |
| HTTP keep-alive GET /hello (p50) | 37 µs | 35 µs | 64 µs | 73 µs | 65 µs | 34 µs |

Before: `2026-11-02-154925` (HTTPS rows, EC) and `2026-11-02-162947` (HTTP rows). After: `2026-11-02-191122`
(EC) and `2026-11-02-191321` (RSA). Other clients are from the after EC run. With the RSA key, the other clients'
new-connection /hello numbers are Rust 570 µs ¹, Go 2.30 ms and Bun 1.97 ms.

¹ The Rust client reuses one reqwest `Client` with pooling off, so rustls resumes the TLS 1.3 session from its
in-memory cache: no certificate verification and no server signature. That is why its number does not move with
the RSA key. Go and Bun do full handshakes here, as does Neo. One request per process cannot resume and is the
like-for-like full-handshake row.

About 40 ms of the old 62 ms handshake was not cryptography. The client never set TCP_NODELAY, so the request
written right after the TLS Finished waited for the server's delayed ACK.

## Primitives (Neo, one op, best of 3, pinned to CPU 1)

| | before | after | speed-up |
|---|---:|---:|---:|
| X25519 scalar multiplication | 1608.8 µs | 102.8 µs | 15.6× |
| P-256 key generation | 4292.6 µs | 180.3 µs | 23.8× |
| P-256 ECDH | 4254.0 µs | 180.4 µs | 23.6× |
| ECDSA P-256 sign (SHA-256) | 4445.3 µs | 219.6 µs | 20.2× |
| ECDSA P-256 verify (SHA-256) | 8513.9 µs | 188.1 µs | 45.3× |
| RSA-2048 PSS verify | 7816.8 µs | 134.0 µs | 58.3× |
| RSA-2048 PKCS#1 v1.5 verify | 7674.9 µs | 131.8 µs | 58.2× |
| RSA-4096 PSS verify ² | 29310.3 µs | 540.0 µs | 54.3× |
| ChaCha20-Poly1305 open, 16 KiB record | 79.7 µs | 34.6 µs | 2.3× |
| ChaCha20-Poly1305 seal, 16 KiB record | 79.6 µs | 36.3 µs | 2.2× |
| ChaCha20, 1 MiB | 3.88 ms (258 MiB/s) | 1.64 ms (608 MiB/s) | 2.4× |
| Poly1305, 1 MiB | 0.86 ms (1.13 GiB/s) | 0.66 ms (1.49 GiB/s) | 1.3× |
| SHA-256, 1 MiB | 6.20 ms (161 MiB/s) | 2.94 ms (340 MiB/s) | 2.1× |

² From the earlier primitive run, not repeated in the last one; RSA code is unchanged since then. Run-to-run noise
is about ±5–10%.

What changed:
- X25519 uses ref10's radix-2^25.5 field.
- P-256 uses a field-specialized Montgomery product over 9×29-bit limbs and a constant-time fixed 4-bit window
  for scalar multiplication. Verification uses wNAF with an affine G table.
- RSA uses 32-bit-limb CIOS Montgomery.
- ChaCha20 is record-based with 8-byte XOR. Poly1305 uses 26-bit limbs with wrapping arithmetic.
- SHA-256 is unrolled into SSA rounds.
- TLS records are read and decrypted in place in the context buffer.
- Content-Length HTTP bodies are read straight into one buffer.
- Client sockets set TCP_NODELAY.

KATs pass: RFC 7748 (including 1,000,000 iterations), RFC 8439 §2.8.2, and Wycheproof x25519 (518),
chacha20_poly1305 (325), ecdsa_secp256r1_sha256 (484), rsa_pss_2048_sha256_mgf1_32 (108) and
rsa_signature_2048_sha256 (257, 2 skipped for exponent or hash).

## Still short

- **Bulk HTTPS: 288 MiB/s against the >1 GB/s target.** The client spends its time in scalar ChaCha20 and
  Poly1305. Rust, Go and Bun use SIMD ChaCha20 or AES-GCM with AES-NI. Closing this needs neoc support for target
  features or vectors.
- **Full handshake.** Neo is faster than every client when each request is a new process. On reused-process new
  connections it is behind Go (1.26 vs 1.14 ms) and Bun (0.80 ms). The rest is X25519 (2 × ~100 µs) and
  P-256 verify (2 × ~190 µs). A 64×64→128 `mul_high` builtin would allow radix-2^51 X25519 and 64-bit-limb
  P-256 and RSA.
- **P-384** is still the generic code: about 2.2 ms per verify, 4.4 ms per Let's Encrypt ECDSA chain.
