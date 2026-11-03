# Fetch benchmark, 2026-11-03

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-147-generic. Bun 1.3.13, go version go1.25.14 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 3 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTP GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 157.4 | 146.5 | 218.6 | 6,352 | 1000 |
| Neo, keep-alive | 36.8 | 32.8 | 63.1 | 27,145 | 1 |
| Bun fetch | 233.9 | 217.8 | 420.9 | 4,275 | 1000 |
| Bun fetch, keep-alive | 79.5 | 64.6 | 256.6 | 12,579 | 1 |
| Go net/http | 257.5 | 251.4 | 372.2 | 3,883 | 1000 |
| Go net/http, keep-alive | 76.0 | 72.9 | 137.0 | 13,154 | 1 |
| Rust reqwest | 232.0 | 222.9 | 336.8 | 4,311 | 1000 |
| Rust reqwest, keep-alive | 66.6 | 62.5 | 101.6 | 15,023 | 1 |

## HTTP GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 200.5 | 190.7 | 280.6 | 4,988 | 1000 |
| Neo, keep-alive | 64.8 | 59.4 | 104.2 | 15,422 | 1 |
| Bun fetch | 285.6 | 266.4 | 522.1 | 3,501 | 1000 |
| Bun fetch, keep-alive | 125.4 | 105.9 | 353.3 | 7,974 | 1 |
| Go net/http | 341.2 | 321.0 | 578.6 | 2,930 | 1000 |
| Go net/http, keep-alive | 150.6 | 132.3 | 362.0 | 6,639 | 1 |
| Rust reqwest | 338.5 | 332.8 | 448.2 | 2,954 | 1000 |
| Rust reqwest, keep-alive | 97.5 | 88.8 | 165.1 | 10,260 | 1 |

## HTTP GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 666.1 | 655.0 | 911.8 | 1,501 | 200 |
| Neo, keep-alive | 323.2 | 284.0 | 535.7 | 3,094 | 1 |
| Bun fetch | 992.3 | 862.5 | 1975.5 | 1,008 | 200 |
| Bun fetch, keep-alive | 594.0 | 439.8 | 1687.1 | 1,683 | 1 |
| Go net/http | 1689.5 | 1689.2 | 2636.4 | 592 | 200 |
| Go net/http, keep-alive | 1166.8 | 1095.3 | 1996.1 | 857 | 1 |
| Rust reqwest | 879.5 | 853.0 | 1234.4 | 1,137 | 200 |
| Rust reqwest, keep-alive | 444.3 | 361.5 | 982.1 | 2,251 | 1 |

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 812.4 | 799.5 | 1126.0 | 1,231 | 1000 |
| Neo, keep-alive | 45.2 | 39.2 | 82.0 | 22,132 | 1 |
| Neo, resumed | 553.0 | 538.6 | 778.0 | 1,808 | 1000 |
| Bun fetch | 814.6 | 798.7 | 1159.0 | 1,228 | 1000 |
| Bun fetch, keep-alive | 103.6 | 85.1 | 272.2 | 9,655 | 1 |
| Go net/http | 1168.6 | 1133.0 | 1582.5 | 856 | 1000 |
| Go net/http, keep-alive | 91.9 | 86.4 | 147.3 | 10,887 | 1 |
| Rust reqwest | 578.4 | 566.7 | 821.6 | 1,729 | 1000 |
| Rust reqwest, keep-alive | 79.6 | 73.0 | 134.4 | 12,567 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 944.7 | 936.5 | 1281.3 | 1,059 | 1000 |
| Neo, keep-alive | 140.0 | 129.2 | 220.5 | 7,145 | 1 |
| Neo, resumed | 697.1 | 683.4 | 943.0 | 1,434 | 1000 |
| Bun fetch | 960.0 | 937.6 | 1381.7 | 1,042 | 1000 |
| Bun fetch, keep-alive | 205.1 | 183.9 | 394.4 | 4,876 | 1 |
| Go net/http | 1386.9 | 1347.5 | 1860.5 | 721 | 1000 |
| Go net/http, keep-alive | 213.0 | 192.8 | 418.0 | 4,694 | 1 |
| Rust reqwest | 801.9 | 785.4 | 1101.0 | 1,247 | 1000 |
| Rust reqwest, keep-alive | 188.2 | 179.6 | 296.1 | 5,314 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 2309.4 | 2197.7 | 3229.3 | 433 | 200 |
| Neo, keep-alive | 1442.1 | 1259.5 | 2699.9 | 693 | 1 |
| Neo, resumed | 2008.4 | 1948.8 | 2817.1 | 498 | 200 |
| Bun fetch | 2456.5 | 2265.2 | 4359.2 | 407 | 200 |
| Bun fetch, keep-alive | 1746.4 | 1526.1 | 3864.8 | 573 | 1 |
| Go net/http | 3426.3 | 3297.3 | 5470.2 | 292 | 200 |
| Go net/http, keep-alive | 1738.0 | 1724.2 | 3185.7 | 575 | 1 |
| Rust reqwest | 2170.8 | 2094.4 | 3272.5 | 461 | 200 |
| Rust reqwest, keep-alive | 1686.0 | 1590.5 | 3006.9 | 593 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTP ms | HTTPS ms |
|---|---:|---:|
| Neo | 1.26 | 2.25 |
| Bun fetch | 13.37 | 15.46 |
| Go net/http | 3.27 | 4.52 |
| Rust reqwest | 2.05 | 2.79 |

