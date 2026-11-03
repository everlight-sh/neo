# Fetch benchmark, 2026-11-03

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTP GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 169.2 | 160.8 | 244.6 | 5,911 | 1000 |
| Neo, keep-alive | 40.8 | 35.9 | 71.9 | 24,481 | 1 |
| Bun fetch | 241.7 | 225.2 | 461.4 | 4,138 | 1000 |
| Bun fetch, keep-alive | 81.2 | 66.7 | 243.4 | 12,314 | 1 |
| Go net/http | 263.6 | 257.9 | 380.7 | 3,794 | 1000 |
| Go net/http, keep-alive | 79.0 | 75.3 | 136.4 | 12,662 | 1 |
| Rust reqwest | 241.1 | 235.2 | 369.9 | 4,148 | 1000 |
| Rust reqwest, keep-alive | 71.0 | 69.2 | 119.8 | 14,081 | 1 |

## HTTP GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 209.1 | 198.3 | 289.8 | 4,783 | 1000 |
| Neo, keep-alive | 69.4 | 64.4 | 119.1 | 14,409 | 1 |
| Bun fetch | 296.7 | 278.4 | 552.2 | 3,371 | 1000 |
| Bun fetch, keep-alive | 125.1 | 106.8 | 310.1 | 7,991 | 1 |
| Go net/http | 350.6 | 331.5 | 589.8 | 2,852 | 1000 |
| Go net/http, keep-alive | 156.0 | 137.3 | 362.4 | 6,411 | 1 |
| Rust reqwest | 344.1 | 340.2 | 468.8 | 2,906 | 1000 |
| Rust reqwest, keep-alive | 100.1 | 91.8 | 167.8 | 9,994 | 1 |

## HTTP GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 671.4 | 661.6 | 880.9 | 1,489 | 200 |
| Neo, keep-alive | 333.3 | 292.5 | 580.5 | 3,001 | 1 |
| Bun fetch | 1014.3 | 892.8 | 2442.9 | 986 | 200 |
| Bun fetch, keep-alive | 607.6 | 452.0 | 1766.2 | 1,646 | 1 |
| Go net/http | 1664.4 | 1603.3 | 3024.4 | 601 | 200 |
| Go net/http, keep-alive | 1031.9 | 1006.9 | 1952.9 | 969 | 1 |
| Rust reqwest | 878.9 | 859.7 | 1531.9 | 1,138 | 200 |
| Rust reqwest, keep-alive | 442.6 | 368.2 | 1145.9 | 2,259 | 1 |

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 944.5 | 937.4 | 1209.7 | 1,059 | 1000 |
| Neo, keep-alive | 52.3 | 47.7 | 97.5 | 19,114 | 1 |
| Neo, resumed | 710.8 | 694.8 | 948.5 | 1,407 | 1000 |
| Bun fetch | 834.4 | 814.7 | 1139.5 | 1,198 | 1000 |
| Bun fetch, keep-alive | 104.7 | 87.9 | 276.7 | 9,547 | 1 |
| Go net/http | 1184.8 | 1162.4 | 1584.0 | 844 | 1000 |
| Go net/http, keep-alive | 92.3 | 87.9 | 155.6 | 10,834 | 1 |
| Rust reqwest | 595.1 | 584.8 | 905.8 | 1,680 | 1000 |
| Rust reqwest, keep-alive | 82.4 | 75.0 | 134.9 | 12,129 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1117.9 | 1103.7 | 1422.9 | 895 | 1000 |
| Neo, keep-alive | 160.4 | 154.1 | 229.7 | 6,233 | 1 |
| Neo, resumed | 864.4 | 857.2 | 1120.2 | 1,157 | 1000 |
| Bun fetch | 974.5 | 947.6 | 1414.5 | 1,026 | 1000 |
| Bun fetch, keep-alive | 208.3 | 186.8 | 418.6 | 4,801 | 1 |
| Go net/http | 1408.4 | 1376.5 | 1923.4 | 710 | 1000 |
| Go net/http, keep-alive | 227.0 | 201.5 | 458.7 | 4,406 | 1 |
| Rust reqwest | 826.5 | 814.1 | 1167.0 | 1,210 | 1000 |
| Rust reqwest, keep-alive | 196.3 | 185.8 | 346.1 | 5,094 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 2665.6 | 2620.9 | 3345.8 | 375 | 200 |
| Neo, keep-alive | 1615.6 | 1511.8 | 2395.7 | 619 | 1 |
| Neo, resumed | 2445.1 | 2377.7 | 3353.9 | 409 | 200 |
| Bun fetch | 2522.7 | 2355.0 | 4825.7 | 396 | 200 |
| Bun fetch, keep-alive | 1773.5 | 1509.0 | 3574.4 | 564 | 1 |
| Go net/http | 3437.7 | 3330.3 | 4968.1 | 291 | 200 |
| Go net/http, keep-alive | 1846.2 | 1834.5 | 3436.3 | 542 | 1 |
| Rust reqwest | 2210.3 | 2130.9 | 3394.9 | 452 | 200 |
| Rust reqwest, keep-alive | 1670.8 | 1578.7 | 2949.4 | 599 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTP ms | HTTPS ms |
|---|---:|---:|
| Neo | 1.19 | 2.24 |
| Bun fetch | 13.60 | 15.72 |
| Go net/http | 3.22 | 4.47 |
| Rust reqwest | 2.03 | 2.82 |
