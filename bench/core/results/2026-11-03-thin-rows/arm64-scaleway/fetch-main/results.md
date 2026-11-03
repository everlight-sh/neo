# Fetch benchmark, 2026-11-03

aarch64, 4 vCPU, Linux 6.8.0-147-generic. Bun 1.3.13, go version go1.25.14 linux/arm64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 3 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1597.7 | 1583.2 | 2033.1 | 626 | 1000 |
| Neo, keep-alive | 73.9 | 69.3 | 106.4 | 13,526 | 1 |
| Neo, resumed | 1059.4 | 1046.8 | 1467.8 | 944 | 1000 |
| Bun fetch | 1737.4 | 1682.6 | 2274.1 | 576 | 1000 |
| Bun fetch, keep-alive | 164.6 | 139.4 | 470.6 | 6,076 | 1 |
| Go net/http | 2455.3 | 2418.8 | 3014.4 | 407 | 1000 |
| Go net/http, keep-alive | 127.5 | 121.1 | 175.5 | 7,841 | 1 |
| Rust reqwest | 1097.5 | 1092.9 | 1563.2 | 911 | 1000 |
| Rust reqwest, keep-alive | 117.1 | 109.0 | 163.8 | 8,540 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 2262.7 | 2263.9 | 2706.3 | 442 | 1000 |
| Neo, keep-alive | 629.9 | 627.0 | 681.4 | 1,588 | 1 |
| Neo, resumed | 1750.1 | 1743.8 | 2177.4 | 571 | 1000 |
| Bun fetch | 2056.7 | 1965.9 | 2830.7 | 486 | 1000 |
| Bun fetch, keep-alive | 314.6 | 281.3 | 658.5 | 3,179 | 1 |
| Go net/http | 2793.7 | 2730.5 | 3361.5 | 358 | 1000 |
| Go net/http, keep-alive | 324.0 | 288.0 | 610.0 | 3,086 | 1 |
| Rust reqwest | 1345.5 | 1335.1 | 1870.5 | 743 | 1000 |
| Rust reqwest, keep-alive | 252.0 | 236.2 | 426.6 | 3,968 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 10637.4 | 10437.0 | 12030.7 | 94 | 200 |
| Neo, keep-alive | 9006.7 | 8842.8 | 10083.5 | 111 | 1 |
| Neo, resumed | 10148.8 | 9933.7 | 11575.0 | 99 | 200 |
| Bun fetch | 3915.9 | 3705.6 | 7106.8 | 255 | 200 |
| Bun fetch, keep-alive | 2415.0 | 2108.7 | 5116.7 | 414 | 1 |
| Go net/http | 5282.3 | 5160.8 | 7186.6 | 189 | 200 |
| Go net/http, keep-alive | 2838.1 | 2770.7 | 3990.4 | 352 | 1 |
| Rust reqwest | 3102.7 | 2968.9 | 5179.3 | 322 | 200 |
| Rust reqwest, keep-alive | 2237.0 | 1909.2 | 4882.4 | 447 | 1 |

## One request per process (GET /hello), median of 20

| Client | HTTPS ms |
|---|---:|
| Neo | 4.72 |
| Bun fetch | 22.44 |
| Go net/http | 8.22 |
| Rust reqwest | 6.18 |
