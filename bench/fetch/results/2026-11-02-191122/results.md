# Fetch benchmark, 2026-11-02

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTP GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 160.9 | 153.5 | 225.4 | 6,215 | 1000 |
| Neo, keep-alive | 38.9 | 34.5 | 64.6 | 25,695 | 1 |
| Bun fetch | 235.6 | 219.6 | 435.3 | 4,245 | 1000 |
| Bun fetch, keep-alive | 78.9 | 64.5 | 250.8 | 12,675 | 1 |
| Go net/http | 256.1 | 250.5 | 362.0 | 3,905 | 1000 |
| Go net/http, keep-alive | 74.3 | 73.0 | 137.1 | 13,468 | 1 |
| Rust reqwest | 233.9 | 227.4 | 359.0 | 4,276 | 1000 |
| Rust reqwest, keep-alive | 68.3 | 63.7 | 106.4 | 14,644 | 1 |

## HTTP GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 202.0 | 193.8 | 303.2 | 4,951 | 1000 |
| Neo, keep-alive | 67.7 | 63.0 | 106.9 | 14,774 | 1 |
| Bun fetch | 288.9 | 269.7 | 554.0 | 3,461 | 1000 |
| Bun fetch, keep-alive | 123.3 | 102.5 | 318.1 | 8,108 | 1 |
| Go net/http | 338.4 | 320.5 | 561.8 | 2,955 | 1000 |
| Go net/http, keep-alive | 150.9 | 133.0 | 349.1 | 6,626 | 1 |
| Rust reqwest | 336.7 | 330.2 | 448.1 | 2,970 | 1000 |
| Rust reqwest, keep-alive | 97.7 | 89.7 | 163.5 | 10,232 | 1 |

## HTTP GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 667.3 | 653.4 | 918.4 | 1,499 | 200 |
| Neo, keep-alive | 331.5 | 282.7 | 573.7 | 3,017 | 1 |
| Bun fetch | 986.6 | 847.0 | 2079.0 | 1,014 | 200 |
| Bun fetch, keep-alive | 602.3 | 447.5 | 1710.0 | 1,660 | 1 |
| Go net/http | 1696.7 | 1637.4 | 2720.5 | 589 | 200 |
| Go net/http, keep-alive | 1084.4 | 1040.5 | 2168.1 | 922 | 1 |
| Rust reqwest | 868.1 | 848.0 | 1737.1 | 1,152 | 200 |
| Rust reqwest, keep-alive | 412.5 | 347.1 | 1124.3 | 2,424 | 1 |

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1287.1 | 1264.0 | 1696.0 | 777 | 1000 |
| Neo, keep-alive | 49.7 | 46.1 | 81.0 | 20,103 | 1 |
| Bun fetch | 830.5 | 801.6 | 1183.1 | 1,204 | 1000 |
| Bun fetch, keep-alive | 101.9 | 85.3 | 257.0 | 9,814 | 1 |
| Go net/http | 1164.5 | 1135.6 | 1586.0 | 859 | 1000 |
| Go net/http, keep-alive | 88.9 | 85.2 | 146.4 | 11,245 | 1 |
| Rust reqwest | 577.0 | 568.1 | 850.4 | 1,733 | 1000 |
| Rust reqwest, keep-alive | 80.9 | 74.7 | 130.3 | 12,357 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1569.4 | 1558.8 | 1932.7 | 637 | 1000 |
| Neo, keep-alive | 289.4 | 284.5 | 366.5 | 3,456 | 1 |
| Bun fetch | 967.6 | 948.6 | 1402.9 | 1,034 | 1000 |
| Bun fetch, keep-alive | 211.4 | 186.6 | 442.0 | 4,730 | 1 |
| Go net/http | 1387.8 | 1350.7 | 1950.5 | 721 | 1000 |
| Go net/http, keep-alive | 213.3 | 193.6 | 416.8 | 4,688 | 1 |
| Rust reqwest | 800.0 | 787.9 | 1133.0 | 1,250 | 1000 |
| Rust reqwest, keep-alive | 189.5 | 177.7 | 309.1 | 5,277 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 4870.3 | 4818.1 | 6109.2 | 205 | 200 |
| Neo, keep-alive | 3596.7 | 3466.3 | 4717.3 | 278 | 1 |
| Bun fetch | 2493.1 | 2269.6 | 4775.3 | 401 | 200 |
| Bun fetch, keep-alive | 1723.0 | 1469.9 | 3640.2 | 580 | 1 |
| Go net/http | 3324.3 | 3204.2 | 5118.0 | 301 | 200 |
| Go net/http, keep-alive | 2287.4 | 2164.9 | 3844.6 | 437 | 1 |
| Rust reqwest | 2168.1 | 2085.2 | 3457.4 | 461 | 200 |
| Rust reqwest, keep-alive | 1666.0 | 1579.0 | 2986.3 | 600 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTP ms | HTTPS ms |
|---|---:|---:|
| Neo | 1.16 | 2.49 |
| Bun fetch | 13.69 | 15.43 |
| Go net/http | 3.14 | 4.32 |
| Rust reqwest | 2.07 | 2.77 |
