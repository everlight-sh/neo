# Fetch benchmark, 2026-11-02

AMD EPYC-Milan Processor, 2 vCPU, Linux 6.8.0-146-generic. Bun 1.3.13, go version go1.25.1 linux/amd64. Server: Go net/http on CPU 1; each client on CPU 0. Median of 5 rounds after a warm-up.

## GET /hello (13 bytes), 1000 sequential requests per round

| Client | µs per request | requests/s | connections |
|---|---:|---:|---:|
| Neo http_request | 489.6 | 2,042 | 1000 |
| Bun fetch | 655.5 | 1,526 | 1000 |
| Bun fetch, keep-alive | 422.3 | 2,368 | 1 |
| Go net/http | 782.7 | 1,278 | 1000 |
| Go net/http, keep-alive | 535.2 | 1,868 | 1 |

## GET /64k (65536 bytes), 1000 sequential requests per round

| Client | µs per request | requests/s | connections |
|---|---:|---:|---:|
| Neo http_request | 733.6 | 1,363 | 1000 |
| Bun fetch | 1071.6 | 933 | 1000 |
| Bun fetch, keep-alive | 428.7 | 2,333 | 1 |
| Go net/http | 768.8 | 1,301 | 1000 |
| Go net/http, keep-alive | 470.4 | 2,126 | 1 |

## GET /1m (1048576 bytes), 200 sequential requests per round

| Client | µs per request | requests/s | connections |
|---|---:|---:|---:|
| Neo http_request | 1168.2 | 856 | 200 |
| Bun fetch | 1223.9 | 817 | 200 |
| Bun fetch, keep-alive | 921.1 | 1,086 | 1 |
| Go net/http | 1909.0 | 524 | 200 |
| Go net/http, keep-alive | 780.9 | 1,281 | 1 |

## One request per process (GET /hello), median of 100

| Client | ms | p90 ms |
|---|---:|---:|
| Neo http_request | 1.17 | 1.25 |
| Bun fetch | 13.30 | 13.75 |
| Go net/http | 3.08 | 3.34 |

