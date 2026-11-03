# Fetch benchmark, 2026-11-03

aarch64, 2 vCPU, Linux 6.8.0-147-generic. Bun 1.3.13, go version go1.25.14 linux/arm64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 3 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTP GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 172.3 | 165.4 | 281.0 | 5,805 | 1000 |
| Neo, keep-alive | 59.0 | 54.9 | 117.7 | 16,963 | 1 |
| Bun fetch | 314.7 | 287.1 | 686.3 | 3,178 | 1000 |
| Bun fetch, keep-alive | 132.0 | 111.7 | 474.4 | 7,577 | 1 |
| Go net/http | 318.8 | 309.6 | 484.5 | 3,136 | 1000 |
| Go net/http, keep-alive | 106.1 | 101.5 | 200.4 | 9,426 | 1 |
| Rust reqwest | 285.9 | 277.0 | 426.3 | 3,497 | 1000 |
| Rust reqwest, keep-alive | 97.4 | 92.0 | 203.2 | 10,272 | 1 |

## HTTP GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 236.9 | 223.9 | 350.5 | 4,221 | 1000 |
| Neo, keep-alive | 102.0 | 93.6 | 168.0 | 9,808 | 1 |
| Bun fetch | 377.5 | 350.3 | 795.8 | 2,649 | 1000 |
| Bun fetch, keep-alive | 197.1 | 172.6 | 552.1 | 5,073 | 1 |
| Go net/http | 457.0 | 415.3 | 897.9 | 2,188 | 1000 |
| Go net/http, keep-alive | 237.1 | 202.2 | 547.5 | 4,217 | 1 |
| Rust reqwest | 406.4 | 406.2 | 656.0 | 2,461 | 1000 |
| Rust reqwest, keep-alive | 139.5 | 128.4 | 238.2 | 7,170 | 1 |

## HTTP GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 691.7 | 673.4 | 1024.2 | 1,446 | 200 |
| Neo, keep-alive | 498.0 | 450.1 | 951.4 | 2,008 | 1 |
| Bun fetch | 1264.9 | 1116.0 | 2610.7 | 791 | 200 |
| Bun fetch, keep-alive | 928.6 | 776.4 | 2112.0 | 1,077 | 1 |
| Go net/http | 2658.0 | 2592.2 | 3694.4 | 376 | 200 |
| Go net/http, keep-alive | 1814.3 | 1705.4 | 3090.2 | 551 | 1 |
| Rust reqwest | 983.5 | 920.6 | 1575.6 | 1,017 | 200 |
| Rust reqwest, keep-alive | 711.8 | 589.9 | 1238.2 | 1,405 | 1 |

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1678.8 | 1674.6 | 2178.6 | 596 | 1000 |
| Neo, keep-alive | 74.6 | 67.7 | 125.7 | 13,407 | 1 |
| Neo, resumed | 1106.1 | 1096.0 | 1541.6 | 904 | 1000 |
| Bun fetch | 1870.1 | 1820.0 | 2506.0 | 535 | 1000 |
| Bun fetch, keep-alive | 173.7 | 149.4 | 490.5 | 5,758 | 1 |
| Go net/http | 2555.3 | 2544.3 | 3220.2 | 391 | 1000 |
| Go net/http, keep-alive | 129.9 | 122.9 | 213.8 | 7,697 | 1 |
| Rust reqwest | 1146.1 | 1147.3 | 1594.7 | 873 | 1000 |
| Rust reqwest, keep-alive | 118.7 | 110.2 | 202.7 | 8,426 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1892.6 | 1872.0 | 2402.6 | 528 | 1000 |
| Neo, keep-alive | 202.8 | 190.0 | 299.4 | 4,930 | 1 |
| Neo, resumed | 1324.0 | 1319.0 | 1850.4 | 755 | 1000 |
| Bun fetch | 2069.1 | 2018.8 | 2909.0 | 483 | 1000 |
| Bun fetch, keep-alive | 317.1 | 288.9 | 707.0 | 3,154 | 1 |
| Go net/http | 2845.4 | 2773.0 | 3404.7 | 351 | 1000 |
| Go net/http, keep-alive | 340.5 | 297.3 | 719.4 | 2,937 | 1 |
| Rust reqwest | 1424.7 | 1403.5 | 1944.0 | 702 | 1000 |
| Rust reqwest, keep-alive | 248.1 | 237.9 | 413.0 | 4,030 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 3584.8 | 3501.0 | 4707.6 | 279 | 200 |
| Neo, keep-alive | 2196.9 | 1932.5 | 3147.5 | 455 | 1 |
| Neo, resumed | 3100.6 | 3015.0 | 4308.9 | 323 | 200 |
| Bun fetch | 4120.2 | 3901.3 | 6344.1 | 243 | 200 |
| Bun fetch, keep-alive | 2602.7 | 2329.3 | 4473.7 | 384 | 1 |
| Go net/http | 5617.6 | 5602.4 | 7537.8 | 178 | 200 |
| Go net/http, keep-alive | 3426.4 | 3294.3 | 5215.8 | 292 | 1 |
| Rust reqwest | 3143.0 | 3019.3 | 5204.2 | 318 | 200 |
| Rust reqwest, keep-alive | 2469.8 | 1984.4 | 4093.6 | 405 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTP ms | HTTPS ms |
|---|---:|---:|
| Neo | 1.91 | 3.71 |
| Bun fetch | 18.53 | 21.42 |
| Go net/http | 4.38 | 6.82 |
| Rust reqwest | 2.93 | 4.50 |

