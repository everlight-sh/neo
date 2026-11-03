# Fetch benchmark, 2026-11-03

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, RSA 2048 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo 801dc53 | 2131.1 | 2078.2 | 2728.3 | 469 | 1000 |
| Neo 801dc53, keep-alive | 51.9 | 46.6 | 81.6 | 19,262 | 1 |
| Neo 801dc53, resumed | 678.9 | 674.4 | 913.5 | 1,473 | 1000 |
| Neo | 2035.0 | 1953.8 | 2628.8 | 491 | 1000 |
| Neo, keep-alive | 46.4 | 39.6 | 72.7 | 21,561 | 1 |
| Neo, resumed | 548.6 | 539.5 | 785.0 | 1,823 | 1000 |
| Bun fetch | 2021.0 | 1960.0 | 2698.9 | 495 | 1000 |
| Bun fetch, keep-alive | 101.4 | 84.5 | 243.6 | 9,858 | 1 |
| Go net/http | 2378.6 | 2312.9 | 3174.2 | 420 | 1000 |
| Go net/http, keep-alive | 90.9 | 86.3 | 151.6 | 11,005 | 1 |
| Rust reqwest | 583.3 | 574.3 | 873.2 | 1,715 | 1000 |
| Rust reqwest, keep-alive | 82.2 | 75.3 | 120.8 | 12,162 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo 801dc53 | 2353.6 | 2314.7 | 3199.3 | 425 | 1000 |
| Neo 801dc53, keep-alive | 159.7 | 150.8 | 245.9 | 6,263 | 1 |
| Neo 801dc53, resumed | 855.3 | 846.4 | 1149.4 | 1,169 | 1000 |
| Neo | 2211.5 | 2170.9 | 2890.1 | 452 | 1000 |
| Neo, keep-alive | 151.9 | 141.8 | 220.1 | 6,584 | 1 |
| Neo, resumed | 721.7 | 700.5 | 982.0 | 1,386 | 1000 |
| Bun fetch | 2267.5 | 2219.1 | 3053.1 | 441 | 1000 |
| Bun fetch, keep-alive | 206.8 | 183.0 | 457.2 | 4,836 | 1 |
| Go net/http | 2557.2 | 2511.0 | 3202.4 | 391 | 1000 |
| Go net/http, keep-alive | 214.4 | 194.6 | 438.2 | 4,665 | 1 |
| Rust reqwest | 799.8 | 798.5 | 1144.5 | 1,250 | 1000 |
| Rust reqwest, keep-alive | 193.2 | 183.4 | 330.5 | 5,177 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo 801dc53 | 3967.7 | 3906.1 | 4923.5 | 252 | 200 |
| Neo 801dc53, keep-alive | 1593.4 | 1483.3 | 2517.4 | 628 | 1 |
| Neo 801dc53, resumed | 2413.9 | 2319.7 | 3464.2 | 414 | 200 |
| Neo | 3787.7 | 3720.9 | 4831.8 | 264 | 200 |
| Neo, keep-alive | 1527.4 | 1403.7 | 2384.7 | 655 | 1 |
| Neo, resumed | 2144.4 | 2081.8 | 2849.8 | 466 | 200 |
| Bun fetch | 4157.1 | 4077.2 | 6772.3 | 241 | 200 |
| Bun fetch, keep-alive | 1746.0 | 1481.6 | 3645.4 | 573 | 1 |
| Go net/http | 5095.5 | 5019.4 | 6935.4 | 196 | 200 |
| Go net/http, keep-alive | 2252.8 | 2155.9 | 3646.6 | 444 | 1 |
| Rust reqwest | 2157.6 | 2083.1 | 3349.2 | 463 | 200 |
| Rust reqwest, keep-alive | 1683.0 | 1584.3 | 2862.9 | 594 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTPS ms |
|---|---:|
| Neo 801dc53 | 3.31 |
| Neo | 3.25 |
| Bun fetch | 16.71 |
| Go net/http | 5.52 |
| Rust reqwest | 3.81 |
