# Fetch benchmark, 2026-11-02

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 7 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo, keep-alive | 116.0 | 47.9 | 94.8 | 8,620 | 1 |
| Bun fetch, keep-alive | 101.2 | 83.9 | 277.6 | 9,878 | 1 |
| Go net/http, keep-alive | 90.6 | 86.1 | 156.9 | 11,042 | 1 |
| Rust reqwest, keep-alive | 80.9 | 73.5 | 132.4 | 12,354 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo, keep-alive | 575.5 | 506.6 | 838.6 | 1,738 | 1 |
| Bun fetch, keep-alive | 209.5 | 186.8 | 457.5 | 4,773 | 1 |
| Go net/http, keep-alive | 211.5 | 192.4 | 423.8 | 4,728 | 1 |
| Rust reqwest, keep-alive | 193.6 | 183.9 | 319.6 | 5,164 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo, keep-alive | 7352.5 | 6926.2 | 9976.1 | 136 | 1 |
| Bun fetch, keep-alive | 1740.3 | 1524.0 | 3661.3 | 575 | 1 |
| Go net/http, keep-alive | 2239.0 | 2146.8 | 4098.5 | 447 | 1 |
| Rust reqwest, keep-alive | 1614.9 | 1564.9 | 2855.4 | 619 | 1 |


