# Fetch benchmark, 2026-11-03

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64, rustc 1.99.1 (58cf8f9c3 2026-10-13), Ubuntu clang version 18.1.3 (1ubuntu1).
Server: Go net/http on CPU 0; each client on CPU 0. HTTPS: TLS 1.3, HTTP/1.1, ECDSA P-256 certificates.
Mean is the median over 5 rounds after a warm-up; percentiles are over every request of those rounds.

## HTTPS GET /hello (13 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo 801dc53 | 931.2 | 924.9 | 1214.2 | 1,074 | 1000 |
| Neo 801dc53, keep-alive | 50.2 | 46.2 | 81.0 | 19,911 | 1 |
| Neo 801dc53, resumed | 679.1 | 676.2 | 915.9 | 1,472 | 1000 |
| Neo | 807.7 | 802.4 | 1067.8 | 1,238 | 1000 |
| Neo, keep-alive | 44.4 | 39.4 | 84.9 | 22,535 | 1 |
| Neo, resumed | 549.2 | 542.5 | 785.7 | 1,821 | 1000 |
| Bun fetch | 819.1 | 804.7 | 1180.9 | 1,221 | 1000 |
| Bun fetch, keep-alive | 101.2 | 84.3 | 267.1 | 9,883 | 1 |
| Go net/http | 1178.6 | 1145.1 | 1652.6 | 848 | 1000 |
| Go net/http, keep-alive | 91.7 | 87.9 | 169.2 | 10,909 | 1 |
| Rust reqwest | 588.2 | 580.0 | 898.3 | 1,700 | 1000 |
| Rust reqwest, keep-alive | 80.8 | 74.8 | 136.6 | 12,382 | 1 |

## HTTPS GET /64k (65536 bytes), 1000 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo 801dc53 | 1103.3 | 1092.7 | 1380.8 | 906 | 1000 |
| Neo 801dc53, keep-alive | 159.7 | 153.1 | 249.9 | 6,262 | 1 |
| Neo 801dc53, resumed | 860.2 | 849.3 | 1243.0 | 1,163 | 1000 |
| Neo | 992.2 | 960.9 | 1335.5 | 1,008 | 1000 |
| Neo, keep-alive | 150.4 | 144.9 | 244.4 | 6,651 | 1 |
| Neo, resumed | 720.0 | 708.3 | 1036.0 | 1,389 | 1000 |
| Bun fetch | 969.7 | 944.6 | 1400.6 | 1,031 | 1000 |
| Bun fetch, keep-alive | 206.2 | 184.0 | 423.4 | 4,850 | 1 |
| Go net/http | 1370.3 | 1344.5 | 1838.4 | 730 | 1000 |
| Go net/http, keep-alive | 215.6 | 196.0 | 429.4 | 4,639 | 1 |
| Rust reqwest | 799.7 | 791.4 | 1126.6 | 1,250 | 1000 |
| Rust reqwest, keep-alive | 191.3 | 181.6 | 299.2 | 5,229 | 1 |

## HTTPS GET /1m (1048576 bytes), 200 sequential requests per round

| Client | mean µs | p50 µs | p99 µs | requests/s | connections |
|---|---:|---:|---:|---:|---:|
| Neo 801dc53 | 2620.1 | 2573.1 | 3616.6 | 382 | 200 |
| Neo 801dc53, keep-alive | 1569.3 | 1488.0 | 2473.4 | 637 | 1 |
| Neo 801dc53, resumed | 2368.0 | 2310.8 | 3152.7 | 422 | 200 |
| Neo | 2359.7 | 2327.9 | 2927.1 | 424 | 200 |
| Neo, keep-alive | 1517.4 | 1410.0 | 2438.4 | 659 | 1 |
| Neo, resumed | 2147.3 | 2092.9 | 2798.3 | 466 | 200 |
| Bun fetch | 2474.3 | 2279.2 | 4697.4 | 404 | 200 |
| Bun fetch, keep-alive | 1740.5 | 1523.7 | 3565.4 | 575 | 1 |
| Go net/http | 3364.1 | 3261.4 | 4665.2 | 297 | 200 |
| Go net/http, keep-alive | 1867.4 | 1948.9 | 3675.4 | 536 | 1 |
| Rust reqwest | 2148.5 | 2076.0 | 3381.7 | 465 | 200 |
| Rust reqwest, keep-alive | 1652.3 | 1592.8 | 2959.6 | 605 | 1 |

## One request per process (GET /hello), median of 100

| Client | HTTPS ms |
|---|---:|
| Neo 801dc53 | 2.15 |
| Neo | 2.14 |
| Bun fetch | 15.30 |
| Go net/http | 4.34 |
| Rust reqwest | 2.73 |
