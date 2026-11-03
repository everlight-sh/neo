# Fetch benchmark, 2026-11-03

aarch64, 2 vCPU, Linux 6.8.0-147-generic. Bun 1.3.13, go version go1.25.14 linux/arm64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTP GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 168.6 | 165.9 | 264.5 | 5,931 | 1000 |
| Neo, keep-alive | 54.6 | 52.4 | 87.6 | 18,327 | 1 |
| Bun fetch | 297.7 | 283.8 | 685.8 | 3,359 | 1000 |
| Bun fetch, keep-alive | 127.3 | 112.2 | 444.6 | 7,854 | 1 |
| Go net/http | 311.9 | 308.7 | 476.6 | 3,206 | 1000 |
| Go net/http, keep-alive | 104.7 | 102.4 | 172.7 | 9,547 | 1 |
| Rust reqwest | 286.7 | 290.5 | 434.1 | 3,487 | 1000 |
| Rust reqwest, keep-alive | 97.7 | 100.4 | 172.1 | 10,240 | 1 |

## HTTP GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 218.0 | 206.2 | 315.7 | 4,586 | 1000 |
| Neo, keep-alive | 90.8 | 83.3 | 155.2 | 11,009 | 1 |
| Bun fetch | 355.7 | 330.0 | 737.6 | 2,811 | 1000 |
| Bun fetch, keep-alive | 186.9 | 162.4 | 524.1 | 5,350 | 1 |
| Go net/http | 429.2 | 392.4 | 770.2 | 2,330 | 1000 |
| Go net/http, keep-alive | 224.8 | 190.6 | 532.2 | 4,449 | 1 |
| Rust reqwest | 381.0 | 379.0 | 545.8 | 2,625 | 1000 |
| Rust reqwest, keep-alive | 134.0 | 124.8 | 233.2 | 7,465 | 1 |

## HTTP GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 550.5 | 519.5 | 868.6 | 1,816 | 200 |
| Neo, keep-alive | 442.3 | 378.6 | 783.8 | 2,261 | 1 |
| Bun fetch | 1198.1 | 1061.7 | 2472.5 | 835 | 200 |
| Bun fetch, keep-alive | 927.8 | 763.6 | 2151.2 | 1,078 | 1 |
| Go net/http | 2563.9 | 2521.3 | 3701.2 | 390 | 200 |
| Go net/http, keep-alive | 1700.6 | 1647.2 | 3010.6 | 588 | 1 |
| Rust reqwest | 891.9 | 869.5 | 1898.4 | 1,121 | 200 |
| Rust reqwest, keep-alive | 656.7 | 542.2 | 1583.5 | 1,523 | 1 |

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1658.0 | 1641.8 | 2128.1 | 603 | 1000 |
| Neo, keep-alive | 71.4 | 65.4 | 112.6 | 14,005 | 1 |
| Neo, resumed | 1093.9 | 1090.5 | 1548.7 | 914 | 1000 |
| Bun fetch | 1804.7 | 1767.7 | 2448.0 | 554 | 1000 |
| Bun fetch, keep-alive | 167.4 | 142.2 | 488.4 | 5,975 | 1 |
| Go net/http | 2473.8 | 2455.7 | 3110.9 | 404 | 1000 |
| Go net/http, keep-alive | 125.5 | 119.1 | 197.3 | 7,968 | 1 |
| Rust reqwest | 1108.0 | 1101.6 | 1533.5 | 903 | 1000 |
| Rust reqwest, keep-alive | 117.1 | 109.4 | 180.4 | 8,537 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 1809.3 | 1791.8 | 2309.1 | 553 | 1000 |
| Neo, keep-alive | 190.7 | 177.2 | 275.8 | 5,243 | 1 |
| Neo, resumed | 1269.2 | 1264.4 | 1761.0 | 788 | 1000 |
| Bun fetch | 2071.6 | 2021.6 | 2894.9 | 483 | 1000 |
| Bun fetch, keep-alive | 311.4 | 283.2 | 658.1 | 3,211 | 1 |
| Go net/http | 2823.1 | 2761.8 | 3427.9 | 354 | 1000 |
| Go net/http, keep-alive | 339.3 | 297.2 | 684.3 | 2,948 | 1 |
| Rust reqwest | 1416.2 | 1399.3 | 1963.4 | 706 | 1000 |
| Rust reqwest, keep-alive | 250.0 | 238.5 | 410.0 | 4,000 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 3277.9 | 3200.1 | 4397.3 | 305 | 200 |
| Neo, keep-alive | 2004.2 | 2032.9 | 6938.0 | 499 | 1 |
| Neo, resumed | 2831.2 | 2765.2 | 9913.1 | 353 | 200 |
| Bun fetch | 4100.2 | 3981.4 | 13241.3 | 244 | 200 |
| Bun fetch, keep-alive | 2639.3 | 2483.6 | 9245.6 | 379 | 1 |
| Go net/http | 5637.4 | 5561.6 | 7325.7 | 177 | 200 |
| Go net/http, keep-alive | 3266.1 | 3052.3 | 4877.4 | 306 | 1 |
| Rust reqwest | 3083.6 | 2968.8 | 5025.0 | 324 | 200 |
| Rust reqwest, keep-alive | 2404.7 | 1964.3 | 4140.0 | 416 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTP ms | HTTPS ms |
|---|---:|---:|
| Neo | 1.86 | 3.70 |
| Bun fetch | 18.49 | 21.65 |
| Go net/http | 4.34 | 6.87 |
| Rust reqwest | 2.85 | 4.47 |

