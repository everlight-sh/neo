### HTTP hello, one worker (req/s), 11 rounds

| Implementation | Median req/s | Range | Vif vs it | Ranges |
|---|---:|---:|---:|---|
| Vif | 110,651 | 109,100-113,913 |  |  |
| Rust hyper | 80,358 | 79,696-81,647 | 1.38x | separate (Vif ahead) |
| Bun | 76,375 | 75,270-77,505 | 1.45x | separate (Vif ahead) |
| Zig http.zig default | 75,913 | 74,907-77,547 | 1.46x | separate (Vif ahead) |
| Zig std.http | 59,293 | 58,628-59,601 | 1.87x | separate (Vif ahead) |
| Zig http.zig 1+1 | 57,986 | 55,313-59,130 | 1.91x | separate (Vif ahead) |
| Go net/http | 54,236 | 53,778-55,222 | 2.04x | separate (Vif ahead) |

| Implementation | p50 us | p99 us | server CPU/request us (user + sys) | server CPUs busy | client CPUs busy | errors |
|---|---:|---:|---:|---:|---:|---|
| Vif | 558 | 751 | 0.17 + 8.85 = 9.02 | 1.00 | 1.37 | 0 |
| Rust hyper | 801 | 1000 | 1.17 + 11.24 = 12.40 | 1.00 | 1.23 | 0 |
| Go net/http | 1190 | 2450 | 5.55 + 12.91 = 18.46 | 1.00 | 0.86 | 0 |
| Bun | 807 | 1620 | 2.85 + 10.25 = 13.11 | 1.00 | 1.01 | 0 |
| Zig http.zig default | 825 | 2940 | 0.68 + 12.50 = 13.18 | 1.00 | 1.13 | 0 |
| Zig http.zig 1+1 | 1000 | 3910 | 1.14 + 16.05 = 17.19 | 1.00 | 0.97 | 0 |
| Zig std.http | 1080 | 1940 | 0.93 + 15.94 = 16.86 | 1.00 | 1.11 | 0 |

### Pipelined HTTP, 16 deep, one worker (req/s), 11 rounds

| Implementation | Median req/s | Range | Vif vs it | Ranges |
|---|---:|---:|---:|---|
| Vif | 1,448,375 | 1,425,684-1,473,079 |  |  |
| Rust hyper | 836,490 | 817,912-846,402 | 1.73x | separate (Vif ahead) |
| Zig std.http | 101,252 | 99,962-102,567 | 14.30x | separate (Vif ahead) |
| Bun | 84,471 | 83,283-85,511 | 17.15x | separate (Vif ahead) |
| Go net/http | 63,556 | 62,877-64,615 | 22.79x | separate (Vif ahead) |

| Implementation | p50 us | p99 us | server CPU/request us (user + sys) | server CPUs busy | client CPUs busy | errors |
|---|---:|---:|---:|---:|---:|---|
| Vif | 459 | 0 | 0.13 + 0.56 = 0.69 | 1.00 | 1.36 | 0 |
| Rust hyper | 678 | 1290 | 0.44 + 0.76 = 1.20 | 1.00 | 1.00 | 0 |
| Go net/http | 9140 | 25950 | 4.80 + 10.87 = 15.67 | 1.00 | 0.56 | 0 |
| Bun | 6610 | 13010 | 2.49 + 9.31 = 11.79 | 1.00 | 0.68 | 0 |
| Zig std.http | 5520 | 11360 | 0.51 + 9.35 = 9.86 | 1.00 | 0.73 | 0 |

### Memory: peak aggregate PSS of the server process tree under the hello load (MiB)

| Implementation | Median MiB | Range | Vif vs it | Ranges |
|---|---:|---:|---:|---|
| Vif | 0.79 | 0.79-0.80 |  |  |
| Rust hyper | 1.91 | 1.80-2.04 | 2.41x | separate (Vif ahead) |
| Zig http.zig 1+1 | 2.25 | 2.25-2.25 | 2.84x | separate (Vif ahead) |
| Zig http.zig default | 10.86 | 10.85-10.86 | 13.69x | separate (Vif ahead) |
| Go net/http | 11.47 | 11.12-11.60 | 14.46x | separate (Vif ahead) |
| Zig std.http | 18.00 | 18.00-18.00 | 22.70x | separate (Vif ahead) |
| Bun | 33.49 | 33.17-33.77 | 42.23x | separate (Vif ahead) |

### Memory: peak aggregate RSS under the hello load (MiB, for reference)

| Implementation | Median MiB | Range | Vif vs it | Ranges |
|---|---:|---:|---:|---|
| Vif | 0.79 | 0.79-0.80 |  |  |
| Zig http.zig 1+1 | 3.73 | 3.72-3.73 | 4.70x | separate (Vif ahead) |
| Rust hyper | 3.88 | 3.77-4.08 | 4.90x | separate (Vif ahead) |
| Go net/http | 11.47 | 11.12-11.60 | 14.47x | separate (Vif ahead) |
| Zig http.zig default | 12.34 | 12.33-12.34 | 15.56x | separate (Vif ahead) |
| Zig std.http | 18.00 | 18.00-18.00 | 22.70x | separate (Vif ahead) |
| Bun | 35.83 | 35.49-36.07 | 45.18x | separate (Vif ahead) |

| Implementation | processes | threads (main process) | idle PSS MiB |
|---|---:|---:|---:|
| Vif | 1 | 1 | 0.30 |
| Rust hyper | 1 | 2 | 1.00 |
| Go net/http | 1 | 3 | 5.28 |
| Bun | 1 | 3 | 14.40 |
| Zig http.zig default | 1 | 34 | 9.98 |
| Zig http.zig 1+1 | 1 | 3 | 1.96 |
| Zig std.http | 1 | 65 | 1.00 |

Validation: Vif: hello ok, 16-deep pipelined ok, io_uring fds 1, Rust hyper: hello ok, 16-deep pipelined ok, io_uring fds 0, Go net/http: hello ok, 16-deep pipelined ok, io_uring fds 0, Bun: hello ok, 16-deep pipelined ok, io_uring fds 0, Zig http.zig default: hello ok, 16-deep pipelined FAIL, io_uring fds 0, Zig http.zig 1+1: hello ok, 16-deep pipelined FAIL, io_uring fds 0, Zig std.http: hello ok, 16-deep pipelined ok, io_uring fds 0 

### json-1M (15 rounds after 2 warm-ups; output 513500000)

| Implementation | Median ms | Range | Vif vs it | Ranges |
|---|---:|---:|---:|---|
| Vif | 187.1 | 185.0-201.0 |  |  |
| Bun JSON.parse | 204.5 | 199.2-253.4 | 1.09x | overlap |
| Zig std.json typed arena native | 321.2 | 313.4-346.4 | 1.72x | separate (Vif ahead) |
| Zig std.json typed arena | 330.4 | 324.6-351.3 | 1.77x | separate (Vif ahead) |
| Rust serde_json::Value | 337.0 | 333.9-346.7 | 1.80x | separate (Vif ahead) |
| Zig std.json typed | 352.1 | 343.4-369.5 | 1.88x | separate (Vif ahead) |
| Zig std.json Value arena | 624.3 | 614.0-647.3 | 3.34x | separate (Vif ahead) |
| Zig std.json Value | 674.9 | 663.2-715.5 | 3.61x | separate (Vif ahead) |
| Go encoding/json | 1876.8 | 1853.0-2079.5 | 10.03x | separate (Vif ahead) |

| Implementation | median CPU ms | peak RSS MiB |
|---|---:|---:|
| Vif | 186.3 | 1.9 |
| Rust serde_json::Value | 336.8 | 2.0 |
| Go encoding/json | 1876.5 | 8.5 |
| Bun JSON.parse | 204.0 | 45.9 |
| Zig std.json Value | 674.6 | 1.9 |
| Zig std.json Value arena | 624.0 | 1.9 |
| Zig std.json typed | 351.8 | 1.9 |
| Zig std.json typed arena | 329.1 | 1.9 |
| Zig std.json typed arena native | 321.0 | 1.9 |

### nbody-4096-10 (15 rounds after 2 warm-ups; output -0.8938489288152517)

| Implementation | Median ms | Range | Vif vs it | Ranges |
|---|---:|---:|---:|---|
| Vif | 376.2 | 374.7-378.7 |  |  |
| Zig native | 683.7 | 681.8-685.4 | 1.82x | separate (Vif ahead) |
| Zig | 684.1 | 682.4-688.1 | 1.82x | separate (Vif ahead) |
| Rust | 686.0 | 684.3-691.3 | 1.82x | separate (Vif ahead) |
| Bun | 833.0 | 822.3-860.1 | 2.21x | separate (Vif ahead) |
| Go | 1190.1 | 1188.2-1195.9 | 3.16x | separate (Vif ahead) |

| Implementation | median CPU ms | peak RSS MiB |
|---|---:|---:|
| Vif | 375.9 | 1.9 |
| Rust | 685.7 | 2.6 |
| Go | 1189.8 | 5.8 |
| Bun | 832.7 | 33.8 |
| Zig | 683.8 | 1.9 |
| Zig native | 683.4 | 1.9 |

