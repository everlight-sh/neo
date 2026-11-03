# Fetch benchmark, 2026-11-03

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, RSA 2048 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTP GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 168.9 | 161.1 | 242.7 | 5,922 | 1000 |
| Neo, keep-alive | 41.5 | 39.4 | 90.1 | 24,121 | 1 |
| Bun fetch | 244.8 | 229.4 | 451.3 | 4,084 | 1000 |
| Bun fetch, keep-alive | 82.2 | 69.5 | 246.1 | 12,171 | 1 |
| Go net/http | 266.5 | 261.1 | 395.7 | 3,753 | 1000 |
| Go net/http, keep-alive | 78.9 | 76.0 | 127.6 | 12,679 | 1 |
| Rust reqwest | 241.5 | 233.5 | 354.2 | 4,140 | 1000 |
| Rust reqwest, keep-alive | 69.4 | 64.5 | 111.1 | 14,403 | 1 |

## HTTP GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 211.0 | 203.4 | 302.6 | 4,739 | 1000 |
| Neo, keep-alive | 70.1 | 64.6 | 111.1 | 14,274 | 1 |
| Bun fetch | 299.5 | 278.0 | 524.9 | 3,339 | 1000 |
| Bun fetch, keep-alive | 128.2 | 108.4 | 332.8 | 7,803 | 1 |
| Go net/http | 356.3 | 337.8 | 606.7 | 2,807 | 1000 |
| Go net/http, keep-alive | 161.6 | 144.3 | 384.9 | 6,187 | 1 |
| Rust reqwest | 353.6 | 349.4 | 496.9 | 2,828 | 1000 |
| Rust reqwest, keep-alive | 102.1 | 94.6 | 172.1 | 9,799 | 1 |

## HTTP GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 681.1 | 669.4 | 966.1 | 1,468 | 200 |
| Neo, keep-alive | 340.9 | 306.0 | 574.1 | 2,933 | 1 |
| Bun fetch | 1027.8 | 895.8 | 2476.5 | 973 | 200 |
| Bun fetch, keep-alive | 616.4 | 467.5 | 1932.8 | 1,622 | 1 |
| Go net/http | 1664.0 | 1672.1 | 3033.8 | 601 | 200 |
| Go net/http, keep-alive | 1033.7 | 1017.8 | 2151.1 | 967 | 1 |
| Rust reqwest | 894.0 | 875.8 | 1237.0 | 1,119 | 200 |
| Rust reqwest, keep-alive | 440.4 | 374.7 | 1130.6 | 2,270 | 1 |

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 2208.1 | 2126.7 | 2945.1 | 453 | 1000 |
| Neo, keep-alive | 53.2 | 47.6 | 107.1 | 18,782 | 1 |
| Neo, resumed | 703.9 | 693.5 | 958.2 | 1,421 | 1000 |
| Bun fetch | 2067.6 | 2012.0 | 2665.9 | 484 | 1000 |
| Bun fetch, keep-alive | 106.9 | 89.7 | 282.6 | 9,357 | 1 |
| Go net/http | 2434.4 | 2394.7 | 3006.4 | 411 | 1000 |
| Go net/http, keep-alive | 94.6 | 89.1 | 164.9 | 10,576 | 1 |
| Rust reqwest | 604.1 | 593.5 | 864.8 | 1,655 | 1000 |
| Rust reqwest, keep-alive | 87.0 | 80.3 | 151.4 | 11,491 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 2382.6 | 2356.6 | 2801.8 | 420 | 1000 |
| Neo, keep-alive | 166.7 | 158.4 | 241.8 | 5,998 | 1 |
| Neo, resumed | 882.4 | 865.1 | 1159.2 | 1,133 | 1000 |
| Bun fetch | 2273.4 | 2249.6 | 2908.4 | 440 | 1000 |
| Bun fetch, keep-alive | 211.4 | 189.2 | 438.5 | 4,731 | 1 |
| Go net/http | 2616.2 | 2587.9 | 3202.0 | 382 | 1000 |
| Go net/http, keep-alive | 227.0 | 203.3 | 455.0 | 4,406 | 1 |
| Rust reqwest | 825.7 | 816.0 | 1127.3 | 1,211 | 1000 |
| Rust reqwest, keep-alive | 196.1 | 186.0 | 322.6 | 5,099 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 4031.5 | 3991.7 | 4913.2 | 248 | 200 |
| Neo, keep-alive | 1625.1 | 1506.5 | 2440.1 | 615 | 1 |
| Neo, resumed | 2451.5 | 2385.6 | 3303.4 | 408 | 200 |
| Bun fetch | 4175.9 | 4097.8 | 5884.9 | 239 | 200 |
| Bun fetch, keep-alive | 1764.4 | 1496.2 | 3650.4 | 567 | 1 |
| Go net/http | 4979.0 | 4779.9 | 6828.8 | 201 | 200 |
| Go net/http, keep-alive | 2079.1 | 2007.4 | 3494.0 | 481 | 1 |
| Rust reqwest | 2237.2 | 2133.2 | 3422.3 | 447 | 200 |
| Rust reqwest, keep-alive | 1666.0 | 1595.6 | 2949.0 | 600 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTP ms | HTTPS ms |
|---|---:|---:|
| Neo | 1.20 | 3.39 |
| Bun fetch | 13.48 | 17.05 |
| Go net/http | 3.21 | 5.62 |
| Rust reqwest | 2.06 | 3.90 |
