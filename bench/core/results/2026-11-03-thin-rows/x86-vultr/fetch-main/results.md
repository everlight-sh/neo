# Fetch benchmark, 2026-11-03

AMD EPYC-Rome Processor, 4 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.14 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 3 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 852.9 | 845.3 | 1156.5 | 1,172 | 1000 |
| Neo, keep-alive | 72.3 | 67.0 | 108.3 | 13,826 | 1 |
| Neo, resumed | 608.3 | 599.3 | 867.4 | 1,644 | 1000 |
| Bun fetch | 885.5 | 869.7 | 1276.5 | 1,129 | 1000 |
| Bun fetch, keep-alive | 140.6 | 127.1 | 356.2 | 7,110 | 1 |
| Go net/http | 1273.9 | 1228.7 | 1725.3 | 785 | 1000 |
| Go net/http, keep-alive | 129.5 | 126.2 | 194.5 | 7,724 | 1 |
| Rust reqwest | 655.7 | 643.7 | 943.5 | 1,525 | 1000 |
| Rust reqwest, keep-alive | 113.6 | 107.1 | 171.5 | 8,802 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1004.1 | 996.1 | 1395.8 | 996 | 1000 |
| Neo, keep-alive | 178.6 | 170.2 | 275.3 | 5,600 | 1 |
| Neo, resumed | 770.3 | 760.2 | 1036.5 | 1,298 | 1000 |
| Bun fetch | 1035.3 | 1003.1 | 1438.3 | 966 | 1000 |
| Bun fetch, keep-alive | 248.1 | 223.5 | 458.4 | 4,031 | 1 |
| Go net/http | 1457.9 | 1411.0 | 1929.6 | 686 | 1000 |
| Go net/http, keep-alive | 250.8 | 228.2 | 467.2 | 3,987 | 1 |
| Rust reqwest | 864.8 | 854.3 | 1179.4 | 1,156 | 1000 |
| Rust reqwest, keep-alive | 226.6 | 209.8 | 385.2 | 4,414 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 2468.9 | 2428.9 | 3271.6 | 405 | 200 |
| Neo, keep-alive | 1606.6 | 1493.2 | 2649.4 | 622 | 1 |
| Neo, resumed | 2257.5 | 2191.9 | 3391.9 | 443 | 200 |
| Bun fetch | 2637.1 | 2406.9 | 4939.7 | 379 | 200 |
| Bun fetch, keep-alive | 1825.8 | 1527.2 | 3953.3 | 548 | 1 |
| Go net/http | 3571.7 | 3411.9 | 5205.2 | 280 | 200 |
| Go net/http, keep-alive | 1965.9 | 1890.9 | 3538.7 | 509 | 1 |
| Rust reqwest | 2298.2 | 2169.5 | 3940.6 | 435 | 200 |
| Rust reqwest, keep-alive | 1585.8 | 1371.1 | 3428.5 | 631 | 1 |

## One request per process (GET /hello), median of 1

| Client | HTTPS ms |
|---|---:|
| Neo | 2.17 |
| Bun fetch | 15.98 |
| Go net/http | 4.79 |
| Rust reqwest | 3.17 |
