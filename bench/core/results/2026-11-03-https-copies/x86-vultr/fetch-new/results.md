# Fetch benchmark, 2026-11-03

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-147-generic. Bun 1.3.13, go version go1.25.14 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTP GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 161.5 | 152.6 | 240.4 | 6,193 | 1000 |
| Neo, keep-alive | 37.4 | 32.9 | 67.5 | 26,769 | 1 |
| Bun fetch | 247.8 | 224.6 | 473.4 | 4,036 | 1000 |
| Bun fetch, keep-alive | 80.9 | 67.7 | 263.5 | 12,362 | 1 |
| Go net/http | 258.7 | 253.4 | 383.3 | 3,865 | 1000 |
| Go net/http, keep-alive | 76.1 | 73.9 | 138.4 | 13,139 | 1 |
| Rust reqwest | 234.1 | 225.8 | 336.6 | 4,271 | 1000 |
| Rust reqwest, keep-alive | 66.4 | 62.8 | 105.3 | 15,066 | 1 |

## HTTP GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 198.1 | 190.9 | 279.5 | 5,048 | 1000 |
| Neo, keep-alive | 62.6 | 56.2 | 92.9 | 15,982 | 1 |
| Bun fetch | 287.4 | 268.6 | 548.9 | 3,480 | 1000 |
| Bun fetch, keep-alive | 125.0 | 107.0 | 330.2 | 7,999 | 1 |
| Go net/http | 348.2 | 328.1 | 611.6 | 2,872 | 1000 |
| Go net/http, keep-alive | 156.8 | 136.6 | 384.1 | 6,376 | 1 |
| Rust reqwest | 344.2 | 336.2 | 484.9 | 2,905 | 1000 |
| Rust reqwest, keep-alive | 99.1 | 90.5 | 168.1 | 10,093 | 1 |

## HTTP GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 631.0 | 624.2 | 908.7 | 1,585 | 200 |
| Neo, keep-alive | 318.6 | 265.2 | 619.9 | 3,139 | 1 |
| Bun fetch | 1013.7 | 872.5 | 2396.2 | 986 | 200 |
| Bun fetch, keep-alive | 602.3 | 455.1 | 1907.9 | 1,660 | 1 |
| Go net/http | 1742.5 | 1670.2 | 2751.1 | 574 | 200 |
| Go net/http, keep-alive | 1121.2 | 1097.0 | 2105.6 | 892 | 1 |
| Rust reqwest | 864.3 | 842.3 | 1562.6 | 1,157 | 200 |
| Rust reqwest, keep-alive | 412.4 | 341.2 | 793.4 | 2,425 | 1 |

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 825.6 | 801.9 | 1129.6 | 1,211 | 1000 |
| Neo, keep-alive | 44.0 | 38.7 | 83.6 | 22,711 | 1 |
| Neo, resumed | 547.3 | 538.0 | 795.4 | 1,827 | 1000 |
| Bun fetch | 826.1 | 803.4 | 1290.0 | 1,210 | 1000 |
| Bun fetch, keep-alive | 103.1 | 88.1 | 270.1 | 9,696 | 1 |
| Go net/http | 1169.2 | 1139.3 | 1604.6 | 855 | 1000 |
| Go net/http, keep-alive | 90.2 | 86.0 | 148.9 | 11,092 | 1 |
| Rust reqwest | 585.3 | 576.0 | 861.9 | 1,708 | 1000 |
| Rust reqwest, keep-alive | 80.4 | 75.2 | 139.2 | 12,437 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 950.3 | 940.7 | 1256.4 | 1,052 | 1000 |
| Neo, keep-alive | 130.9 | 122.6 | 207.9 | 7,637 | 1 |
| Neo, resumed | 694.6 | 680.7 | 968.3 | 1,440 | 1000 |
| Bun fetch | 979.7 | 953.8 | 1405.3 | 1,021 | 1000 |
| Bun fetch, keep-alive | 211.0 | 189.3 | 442.7 | 4,740 | 1 |
| Go net/http | 1398.9 | 1364.4 | 1831.5 | 715 | 1000 |
| Go net/http, keep-alive | 218.0 | 197.0 | 441.5 | 4,588 | 1 |
| Rust reqwest | 815.0 | 800.6 | 1118.0 | 1,227 | 1000 |
| Rust reqwest, keep-alive | 189.9 | 181.8 | 308.4 | 5,266 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 2069.1 | 2015.9 | 2886.5 | 483 | 200 |
| Neo, keep-alive | 1253.5 | 1082.7 | 2043.2 | 798 | 1 |
| Neo, resumed | 1809.9 | 1747.3 | 2659.3 | 553 | 200 |
| Bun fetch | 2515.4 | 2313.3 | 4915.2 | 398 | 200 |
| Bun fetch, keep-alive | 1746.0 | 1502.3 | 3552.9 | 573 | 1 |
| Go net/http | 3390.0 | 3264.9 | 4879.4 | 295 | 200 |
| Go net/http, keep-alive | 1856.0 | 1737.2 | 3611.0 | 539 | 1 |
| Rust reqwest | 2208.9 | 2115.4 | 3386.5 | 453 | 200 |
| Rust reqwest, keep-alive | 1683.2 | 1582.0 | 2989.2 | 594 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTP ms | HTTPS ms |
|---|---:|---:|
| Neo | 1.25 | 2.19 |
| Bun fetch | 13.38 | 15.36 |
| Go net/http | 3.23 | 4.41 |
| Rust reqwest | 2.02 | 2.66 |

