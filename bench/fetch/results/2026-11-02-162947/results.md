# Fetch benchmark, 2026-11-02

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 7 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTP GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 161.9 | 153.4 | 237.0 | 6,177 | 1000 |
| Neo, keep-alive | 39.8 | 36.9 | 67.3 | 25,139 | 1 |
| Bun fetch | 236.4 | 220.3 | 445.2 | 4,229 | 1000 |
| Bun fetch, keep-alive | 78.8 | 64.2 | 235.2 | 12,697 | 1 |
| Go net/http | 257.8 | 251.9 | 380.8 | 3,880 | 1000 |
| Go net/http, keep-alive | 75.5 | 72.7 | 131.8 | 13,247 | 1 |
| Rust reqwest | 235.0 | 226.1 | 345.0 | 4,255 | 1000 |
| Rust reqwest, keep-alive | 66.9 | 62.9 | 106.0 | 14,947 | 1 |

## HTTP GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 217.3 | 209.4 | 308.0 | 4,602 | 1000 |
| Neo, keep-alive | 81.6 | 76.5 | 117.9 | 12,248 | 1 |
| Bun fetch | 285.6 | 267.4 | 531.9 | 3,502 | 1000 |
| Bun fetch, keep-alive | 121.8 | 102.1 | 322.6 | 8,213 | 1 |
| Go net/http | 338.9 | 320.1 | 563.5 | 2,951 | 1000 |
| Go net/http, keep-alive | 150.7 | 132.5 | 352.2 | 6,634 | 1 |
| Rust reqwest | 334.9 | 330.6 | 473.5 | 2,986 | 1000 |
| Rust reqwest, keep-alive | 95.7 | 87.9 | 160.5 | 10,450 | 1 |

## HTTP GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 978.1 | 935.7 | 1223.1 | 1,022 | 200 |
| Neo, keep-alive | 691.2 | 676.1 | 886.8 | 1,447 | 1 |
| Bun fetch | 972.9 | 850.3 | 2157.8 | 1,028 | 200 |
| Bun fetch, keep-alive | 593.1 | 440.5 | 1781.0 | 1,686 | 1 |
| Go net/http | 1657.4 | 1608.3 | 2694.3 | 603 | 200 |
| Go net/http, keep-alive | 1112.5 | 1130.9 | 2195.7 | 899 | 1 |
| Rust reqwest | 862.1 | 841.3 | 1852.4 | 1,160 | 200 |
| Rust reqwest, keep-alive | 426.8 | 346.1 | 1413.9 | 2,343 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTP ms |
|---|---:|
| Neo | 1.14 |
| Bun fetch | 13.09 |
| Go net/http | 3.08 |
| Rust reqwest | 1.98 |

