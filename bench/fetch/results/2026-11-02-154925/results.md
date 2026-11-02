# Fetch benchmark, 2026-11-02

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 7 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTP GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 159.5 | 149.2 | 229.5 | 6,268 | 1000 |
| Neo, keep-alive | 38.1 | 34.0 | 64.9 | 26,228 | 1 |
| Bun fetch | 236.7 | 218.2 | 451.6 | 4,225 | 1000 |
| Bun fetch, keep-alive | 79.8 | 64.8 | 252.6 | 12,533 | 1 |
| Go net/http | 265.2 | 254.4 | 446.7 | 3,771 | 1000 |
| Go net/http, keep-alive | 75.8 | 73.4 | 131.3 | 13,199 | 1 |
| Rust reqwest | 231.8 | 222.3 | 343.4 | 4,314 | 1000 |
| Rust reqwest, keep-alive | 68.5 | 63.5 | 117.9 | 14,598 | 1 |

## HTTP GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 216.2 | 207.4 | 325.2 | 4,626 | 1000 |
| Neo, keep-alive | 75.4 | 70.1 | 119.5 | 13,263 | 1 |
| Bun fetch | 288.1 | 267.5 | 523.8 | 3,471 | 1000 |
| Bun fetch, keep-alive | 123.7 | 105.7 | 323.6 | 8,081 | 1 |
| Go net/http | 342.3 | 323.9 | 561.0 | 2,921 | 1000 |
| Go net/http, keep-alive | 155.0 | 135.7 | 370.9 | 6,451 | 1 |
| Rust reqwest | 337.3 | 334.7 | 469.2 | 2,965 | 1000 |
| Rust reqwest, keep-alive | 97.3 | 89.0 | 169.3 | 10,278 | 1 |

## HTTP GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 981.4 | 932.0 | 1267.8 | 1,019 | 200 |
| Neo, keep-alive | 444.9 | 434.4 | 683.9 | 2,248 | 1 |
| Bun fetch | 980.2 | 844.2 | 2119.6 | 1,020 | 200 |
| Bun fetch, keep-alive | 590.2 | 427.3 | 1854.0 | 1,694 | 1 |
| Go net/http | 1591.5 | 1584.1 | 3075.2 | 628 | 200 |
| Go net/http, keep-alive | 1179.0 | 1098.4 | 2171.8 | 848 | 1 |
| Rust reqwest | 887.0 | 858.3 | 1974.5 | 1,127 | 200 |
| Rust reqwest, keep-alive | 422.1 | 352.1 | 953.8 | 2,369 | 1 |

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 62484.8 | 62005.5 | 72779.2 | 16 | 1000 |
| Neo, keep-alive | 113.9 | 47.1 | 91.1 | 8,779 | 1 |
| Bun fetch | 827.5 | 803.9 | 1171.2 | 1,208 | 1000 |
| Bun fetch, keep-alive | 102.5 | 87.8 | 255.0 | 9,754 | 1 |
| Go net/http | 1172.7 | 1145.7 | 1670.9 | 853 | 1000 |
| Go net/http, keep-alive | 92.6 | 88.2 | 157.0 | 10,797 | 1 |
| Rust reqwest | 577.0 | 567.7 | 830.9 | 1,733 | 1000 |
| Rust reqwest, keep-alive | 80.0 | 74.1 | 127.2 | 12,499 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 62886.4 | 62241.2 | 72460.0 | 16 | 1000 |
| Neo, keep-alive | 573.6 | 503.1 | 737.0 | 1,743 | 1 |
| Bun fetch | 971.1 | 943.3 | 1421.2 | 1,030 | 1000 |
| Bun fetch, keep-alive | 207.6 | 186.0 | 452.1 | 4,817 | 1 |
| Go net/http | 1388.2 | 1348.2 | 1885.1 | 720 | 1000 |
| Go net/http, keep-alive | 213.3 | 192.1 | 447.7 | 4,689 | 1 |
| Rust reqwest | 801.6 | 787.3 | 1140.4 | 1,248 | 1000 |
| Rust reqwest, keep-alive | 185.9 | 177.6 | 317.6 | 5,380 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo | 69524.0 | 69025.8 | 78037.1 | 14 | 200 |
| Neo, keep-alive | 7469.9 | 6862.8 | 10038.1 | 134 | 1 |
| Bun fetch | 2452.8 | 2250.3 | 4459.6 | 408 | 200 |
| Bun fetch, keep-alive | 1711.5 | 1458.3 | 3500.2 | 584 | 1 |
| Go net/http | 3327.6 | 3210.0 | 5186.2 | 301 | 200 |
| Go net/http, keep-alive | 2232.4 | 2128.6 | 3966.6 | 448 | 1 |
| Rust reqwest | 2162.8 | 2073.6 | 3532.7 | 462 | 200 |
| Rust reqwest, keep-alive | 1650.5 | 1579.6 | 3018.3 | 606 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTP ms | HTTPS ms |
|---|---:|---:|
| Neo | 1.15 | 63.90 |
| Bun fetch | 13.24 | 15.09 |
| Go net/http | 3.15 | 4.32 |
| Rust reqwest | 2.01 | 2.69 |

