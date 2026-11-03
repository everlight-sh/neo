# Fetch benchmark, 2026-11-03

AMD EPYC-Rome Processor, 4 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.14 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 837.1 | 832.1 | 1065.6 | 1,195 | 1000 |
| Neo, keep-alive | 71.6 | 66.6 | 103.0 | 13,971 | 1 |
| Neo, resumed | 597.4 | 591.5 | 803.0 | 1,674 | 1000 |
| Bun fetch | 872.4 | 854.0 | 1153.3 | 1,146 | 1000 |
| Bun fetch, keep-alive | 138.2 | 121.7 | 284.0 | 7,238 | 1 |
| Go net/http | 1228.6 | 1194.5 | 1562.6 | 814 | 1000 |
| Go net/http, keep-alive | 124.8 | 121.3 | 170.5 | 8,010 | 1 |
| Rust reqwest | 643.8 | 636.4 | 860.8 | 1,553 | 1000 |
| Rust reqwest, keep-alive | 112.9 | 107.2 | 154.1 | 8,855 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 990.7 | 980.6 | 1238.3 | 1,009 | 1000 |
| Neo, keep-alive | 166.2 | 155.9 | 249.2 | 6,015 | 1 |
| Neo, resumed | 760.9 | 748.6 | 982.0 | 1,314 | 1000 |
| Bun fetch | 1026.3 | 997.5 | 1402.8 | 974 | 1000 |
| Bun fetch, keep-alive | 243.2 | 221.5 | 446.3 | 4,111 | 1 |
| Go net/http | 1439.2 | 1401.7 | 1857.3 | 695 | 1000 |
| Go net/http, keep-alive | 250.5 | 228.4 | 473.8 | 3,992 | 1 |
| Rust reqwest | 872.8 | 860.0 | 1212.8 | 1,146 | 1000 |
| Rust reqwest, keep-alive | 225.1 | 210.3 | 378.1 | 4,442 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 2323.6 | 2270.5 | 3443.2 | 430 | 200 |
| Neo, keep-alive | 1508.9 | 1348.2 | 2701.2 | 663 | 1 |
| Neo, resumed | 2088.4 | 2038.0 | 3301.2 | 479 | 200 |
| Bun fetch | 2579.4 | 2355.3 | 4865.5 | 388 | 200 |
| Bun fetch, keep-alive | 1762.1 | 1475.7 | 3971.4 | 567 | 1 |
| Go net/http | 3523.9 | 3420.7 | 4837.6 | 284 | 200 |
| Go net/http, keep-alive | 2556.9 | 2346.2 | 3585.1 | 391 | 1 |
| Rust reqwest | 2310.1 | 2186.4 | 4045.0 | 433 | 200 |
| Rust reqwest, keep-alive | 1629.4 | 1379.9 | 3640.6 | 614 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTPS ms |
|---|---:|
| Neo | 2.33 |
| Bun fetch | 15.62 |
| Go net/http | 4.62 |
| Rust reqwest | 2.89 |
