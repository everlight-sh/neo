# Fetch benchmark, 2026-11-03

aarch64, 4 vCPU, Linux 6.8.0-147-generic. Bun 1.3.13, go version go1.25.14 linux/arm64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1688.7 | 1661.1 | 2150.6 | 592 | 1000 |
| Neo, keep-alive | 73.2 | 66.4 | 129.0 | 13,662 | 1 |
| Neo, resumed | 1131.4 | 1106.6 | 1563.8 | 884 | 1000 |
| Bun fetch | 1923.9 | 1847.1 | 2526.0 | 520 | 1000 |
| Bun fetch, keep-alive | 174.9 | 153.9 | 520.2 | 5,718 | 1 |
| Go net/http | 2527.0 | 2519.5 | 3169.1 | 396 | 1000 |
| Go net/http, keep-alive | 130.0 | 127.6 | 203.8 | 7,691 | 1 |
| Rust reqwest | 1142.3 | 1141.8 | 1617.7 | 875 | 1000 |
| Rust reqwest, keep-alive | 122.1 | 114.2 | 206.8 | 8,190 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1903.3 | 1889.8 | 2383.4 | 525 | 1000 |
| Neo, keep-alive | 211.3 | 199.4 | 316.9 | 4,734 | 1 |
| Neo, resumed | 1359.4 | 1338.7 | 1834.4 | 736 | 1000 |
| Bun fetch | 2144.6 | 2074.8 | 2950.0 | 466 | 1000 |
| Bun fetch, keep-alive | 341.2 | 308.7 | 737.6 | 2,931 | 1 |
| Go net/http | 2916.4 | 2843.3 | 3538.0 | 343 | 1000 |
| Go net/http, keep-alive | 356.3 | 315.8 | 713.9 | 2,807 | 1 |
| Rust reqwest | 1474.5 | 1455.8 | 2017.6 | 678 | 1000 |
| Rust reqwest, keep-alive | 268.8 | 250.3 | 444.0 | 3,720 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 3443.2 | 3389.8 | 4578.3 | 290 | 200 |
| Neo, keep-alive | 2030.6 | 1842.7 | 3080.8 | 492 | 1 |
| Neo, resumed | 2993.1 | 2897.0 | 4188.9 | 334 | 200 |
| Bun fetch | 3854.5 | 3712.4 | 6738.0 | 259 | 200 |
| Bun fetch, keep-alive | 2417.0 | 2147.3 | 4733.0 | 414 | 1 |
| Go net/http | 5438.8 | 5437.1 | 7110.3 | 184 | 200 |
| Go net/http, keep-alive | 3106.7 | 3056.9 | 4383.7 | 322 | 1 |
| Rust reqwest | 3111.9 | 2960.9 | 5082.6 | 321 | 200 |
| Rust reqwest, keep-alive | 2192.2 | 1874.4 | 4062.0 | 456 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTPS ms |
|---|---:|
| Neo | 5.61 |
| Bun fetch | 22.14 |
| Go net/http | 8.08 |
| Rust reqwest | 6.73 |
