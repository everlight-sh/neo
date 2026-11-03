# Fetch benchmark, 2026-11-03

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo 801dc53 | 934.0 | 924.2 | 1215.1 | 1,071 | 1000 |
| Neo 801dc53, keep-alive | 49.5 | 46.0 | 83.2 | 20,184 | 1 |
| Neo 801dc53, resumed | 695.3 | 682.0 | 960.5 | 1,438 | 1000 |
| Neo | 823.4 | 807.2 | 1103.2 | 1,214 | 1000 |
| Neo, keep-alive | 44.4 | 39.0 | 84.1 | 22,545 | 1 |
| Neo, resumed | 556.2 | 546.3 | 792.5 | 1,798 | 1000 |
| Bun fetch | 841.8 | 805.7 | 1161.2 | 1,188 | 1000 |
| Bun fetch, keep-alive | 104.1 | 86.4 | 264.7 | 9,604 | 1 |
| Go net/http | 1179.2 | 1147.5 | 1600.6 | 848 | 1000 |
| Go net/http, keep-alive | 91.9 | 88.6 | 166.4 | 10,879 | 1 |
| Rust reqwest | 597.1 | 579.4 | 878.8 | 1,675 | 1000 |
| Rust reqwest, keep-alive | 82.4 | 75.0 | 130.3 | 12,138 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo 801dc53 | 1120.6 | 1097.9 | 1536.3 | 892 | 1000 |
| Neo 801dc53, keep-alive | 161.0 | 153.2 | 272.4 | 6,211 | 1 |
| Neo 801dc53, resumed | 875.9 | 851.7 | 1230.6 | 1,142 | 1000 |
| Neo | 960.0 | 952.1 | 1262.0 | 1,042 | 1000 |
| Neo, keep-alive | 150.2 | 143.8 | 230.7 | 6,656 | 1 |
| Neo, resumed | 710.0 | 697.7 | 969.6 | 1,408 | 1000 |
| Bun fetch | 973.2 | 946.7 | 1419.8 | 1,027 | 1000 |
| Bun fetch, keep-alive | 206.5 | 188.1 | 467.9 | 4,843 | 1 |
| Go net/http | 1373.0 | 1343.0 | 1815.1 | 728 | 1000 |
| Go net/http, keep-alive | 211.7 | 192.9 | 426.2 | 4,724 | 1 |
| Rust reqwest | 801.8 | 793.0 | 1143.9 | 1,247 | 1000 |
| Rust reqwest, keep-alive | 188.2 | 177.1 | 302.9 | 5,315 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo 801dc53 | 2611.2 | 2562.0 | 3389.2 | 383 | 200 |
| Neo 801dc53, keep-alive | 1583.8 | 1476.5 | 2507.3 | 631 | 1 |
| Neo 801dc53, resumed | 2396.4 | 2318.6 | 3379.6 | 417 | 200 |
| Neo | 2383.4 | 2344.8 | 3214.2 | 420 | 200 |
| Neo, keep-alive | 1530.4 | 1408.2 | 2373.0 | 653 | 1 |
| Neo, resumed | 2151.8 | 2087.5 | 3061.9 | 465 | 200 |
| Bun fetch | 2463.5 | 2287.4 | 4311.7 | 406 | 200 |
| Bun fetch, keep-alive | 1734.4 | 1474.3 | 3568.5 | 577 | 1 |
| Go net/http | 3277.7 | 3158.9 | 5027.4 | 305 | 200 |
| Go net/http, keep-alive | 2176.2 | 2082.1 | 3616.8 | 460 | 1 |
| Rust reqwest | 2161.3 | 2096.6 | 3355.1 | 463 | 200 |
| Rust reqwest, keep-alive | 1599.7 | 1513.2 | 2937.9 | 625 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTPS ms |
|---|---:|
| Neo 801dc53 | 2.18 |
| Neo | 2.13 |
| Bun fetch | 15.36 |
| Go net/http | 4.31 |
| Rust reqwest | 2.69 |
