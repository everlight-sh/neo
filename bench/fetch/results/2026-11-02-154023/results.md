# Fetch benchmark, 2026-11-02

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64. Server: Go net/http on CPU 0; each client on CPU 0. Median of 9 rounds after a warm-up.

## GET /hello (13 bytes), 1000 sequential requests per round

| Client | µs per request | requests/s | connections |
|---|---:|---:|---:|
| Neo http_request | 159.6 | 6,265 | 1000 |
| Bun fetch | 233.1 | 4,289 | 1000 |
| Bun fetch, keep-alive | 79.4 | 12,598 | 1 |
| Go net/http | 257.5 | 3,883 | 1000 |
| Go net/http, keep-alive | 74.3 | 13,463 | 1 |

## GET /64k (65536 bytes), 1000 sequential requests per round

| Client | µs per request | requests/s | connections |
|---|---:|---:|---:|
| Neo http_request | 219.0 | 4,566 | 1000 |
| Bun fetch | 287.3 | 3,481 | 1000 |
| Bun fetch, keep-alive | 121.7 | 8,220 | 1 |
| Go net/http | 340.2 | 2,940 | 1000 |
| Go net/http, keep-alive | 151.9 | 6,581 | 1 |

## GET /1m (1048576 bytes), 200 sequential requests per round

| Client | µs per request | requests/s | connections |
|---|---:|---:|---:|
| Neo http_request | 969.9 | 1,031 | 200 |
| Bun fetch | 990.1 | 1,010 | 200 |
| Bun fetch, keep-alive | 588.5 | 1,699 | 1 |
| Go net/http | 1693.0 | 591 | 200 |
| Go net/http, keep-alive | 894.5 | 1,118 | 1 |

## One request per process (GET /hello), median of 100

| Client | ms | p90 ms |
|---|---:|---:|
| Neo http_request | 1.14 | 1.30 |
| Bun fetch | 13.30 | 13.62 |
| Go net/http | 3.16 | 3.31 |

