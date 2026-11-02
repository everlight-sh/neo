# Fetch benchmark, 2026-11-02

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, RSA 2048 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTP GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 158.9 | 150.9 | 234.4 | 6,295 | 1000 |
| Neo, keep-alive | 38.1 | 34.3 | 68.5 | 26,250 | 1 |
| Bun fetch | 234.2 | 217.5 | 452.6 | 4,269 | 1000 |
| Bun fetch, keep-alive | 78.3 | 62.1 | 228.6 | 12,764 | 1 |
| Go net/http | 252.1 | 246.0 | 354.3 | 3,967 | 1000 |
| Go net/http, keep-alive | 72.1 | 70.1 | 126.9 | 13,865 | 1 |
| Rust reqwest | 229.7 | 220.3 | 325.3 | 4,353 | 1000 |
| Rust reqwest, keep-alive | 66.6 | 61.5 | 105.3 | 15,019 | 1 |

## HTTP GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 201.0 | 192.7 | 285.3 | 4,976 | 1000 |
| Neo, keep-alive | 65.4 | 61.9 | 94.3 | 15,301 | 1 |
| Bun fetch | 283.7 | 266.2 | 514.6 | 3,525 | 1000 |
| Bun fetch, keep-alive | 121.4 | 102.3 | 312.6 | 8,237 | 1 |
| Go net/http | 334.8 | 317.6 | 560.4 | 2,987 | 1000 |
| Go net/http, keep-alive | 148.9 | 131.5 | 357.2 | 6,715 | 1 |
| Rust reqwest | 332.0 | 327.5 | 442.0 | 3,012 | 1000 |
| Rust reqwest, keep-alive | 95.4 | 88.2 | 161.5 | 10,482 | 1 |

## HTTP GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 657.5 | 649.4 | 877.4 | 1,521 | 200 |
| Neo, keep-alive | 327.2 | 282.1 | 565.1 | 3,056 | 1 |
| Bun fetch | 973.0 | 832.7 | 2164.8 | 1,028 | 200 |
| Bun fetch, keep-alive | 590.4 | 435.2 | 1809.1 | 1,694 | 1 |
| Go net/http | 1670.2 | 1628.7 | 2692.5 | 599 | 200 |
| Go net/http, keep-alive | 1089.1 | 1009.2 | 2044.1 | 918 | 1 |
| Rust reqwest | 864.2 | 843.7 | 1751.1 | 1,157 | 200 |
| Rust reqwest, keep-alive | 433.7 | 348.5 | 1007.1 | 2,306 | 1 |

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 2373.6 | 2334.8 | 2830.4 | 421 | 1000 |
| Neo, keep-alive | 50.7 | 45.6 | 77.5 | 19,726 | 1 |
| Bun fetch | 2023.3 | 1966.2 | 2709.9 | 494 | 1000 |
| Bun fetch, keep-alive | 104.1 | 85.9 | 259.8 | 9,608 | 1 |
| Go net/http | 2345.3 | 2304.3 | 2819.8 | 426 | 1000 |
| Go net/http, keep-alive | 90.4 | 85.2 | 136.8 | 11,063 | 1 |
| Rust reqwest | 581.7 | 570.4 | 841.5 | 1,719 | 1000 |
| Rust reqwest, keep-alive | 81.8 | 73.9 | 123.1 | 12,223 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 2742.2 | 2725.2 | 3186.1 | 365 | 1000 |
| Neo, keep-alive | 293.4 | 286.8 | 374.6 | 3,409 | 1 |
| Bun fetch | 2299.7 | 2247.1 | 3034.1 | 435 | 1000 |
| Bun fetch, keep-alive | 211.2 | 186.4 | 449.1 | 4,735 | 1 |
| Go net/http | 2631.5 | 2577.5 | 3304.3 | 380 | 1000 |
| Go net/http, keep-alive | 216.8 | 195.3 | 428.1 | 4,612 | 1 |
| Rust reqwest | 818.1 | 804.6 | 1138.7 | 1,222 | 1000 |
| Rust reqwest, keep-alive | 203.9 | 189.1 | 328.0 | 4,906 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 6047.7 | 5960.3 | 7119.8 | 165 | 200 |
| Neo, keep-alive | 3601.8 | 3467.5 | 5074.5 | 278 | 1 |
| Bun fetch | 4111.3 | 4009.9 | 6544.6 | 243 | 200 |
| Bun fetch, keep-alive | 1715.8 | 1522.6 | 3540.2 | 583 | 1 |
| Go net/http | 4971.8 | 4648.3 | 7237.1 | 201 | 200 |
| Go net/http, keep-alive | 2094.3 | 2007.9 | 3636.0 | 477 | 1 |
| Rust reqwest | 2144.8 | 2074.4 | 3309.6 | 466 | 200 |
| Rust reqwest, keep-alive | 1679.2 | 1587.1 | 2883.9 | 596 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTP ms | HTTPS ms |
|---|---:|---:|
| Neo | 1.21 | 3.57 |
| Bun fetch | 13.70 | 16.65 |
| Go net/http | 3.14 | 5.48 |
| Rust reqwest | 2.00 | 3.78 |
