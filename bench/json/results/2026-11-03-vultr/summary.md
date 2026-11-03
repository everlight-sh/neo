CPU 1, 2 warmup rounds, 21 measured rounds, seed 20261103.

### doc-typed (checksum 513500000)

| Implementation | Median ms | Range ms | User ms | Neo after × | Paired | Separate |
|---|---:|---:|---:|---:|---:|---|
| **Neo after** | **92.1** | 91.9–95.4 | 90 | — | — | — |
| Neo before | 116.9 | 116.5–121.3 | 120 | 1.27× | 21/21 | yes |
| Rust serde typed | 164.2 | 162.7–187.0 | 160 | 1.78× | 21/21 | yes |
| Zig typed arena native | 290.0 | 287.4–294.1 | 290 | 3.15× | 21/21 | yes |
| Zig typed arena | 298.1 | 293.7–306.6 | 300 | 3.24× | 21/21 | yes |
| Rust serde Value | 323.5 | 321.0–336.8 | 320 | 3.51× | 21/21 | yes |

### orders-typed (checksum 34327000)

| Implementation | Median ms | Range ms | User ms | Neo after × | Paired | Separate |
|---|---:|---:|---:|---:|---:|---|
| **Neo after** | **71.5** | 71.2–72.0 | 70 | — | — | — |
| Neo before | 80.9 | 80.4–82.0 | 80 | 1.13× | 21/21 | yes |
| Rust serde typed | 93.3 | 92.7–94.9 | 90 | 1.31× | 21/21 | yes |
| Zig typed arena | 196.0 | 193.4–216.7 | 190 | 2.74× | 21/21 | yes |
| Zig typed arena native | 209.6 | 203.9–217.4 | 210 | 2.93× | 21/21 | yes |

### doc-dynamic (checksum 513500000)

| Implementation | Median ms | Range ms | User ms | Neo after × | Paired | Separate |
|---|---:|---:|---:|---:|---:|---|
| **Neo after** | **126.8** | 124.7–135.2 | 130 | — | — | — |
| Neo before | 181.0 | 178.4–185.7 | 180 | 1.43× | 21/21 | yes |
| Bun JSON.parse | 186.1 | 181.8–193.3 | 160 | 1.47× | 21/21 | yes |
| Zig typed arena native | 292.2 | 286.0–304.4 | 290 | 2.30× | 21/21 | yes |
| Zig typed arena | 298.8 | 296.3–305.1 | 300 | 2.36× | 21/21 | yes |
| Rust serde_json::Value | 308.2 | 301.6–314.5 | 310 | 2.43× | 21/21 | yes |
| Zig Value | 619.0 | 608.0–638.2 | 620 | 4.88× | 21/21 | yes |
| Go encoding/json | 1721.2 | 1676.3–1794.8 | 1710 | 13.57× | 21/21 | yes |

### orders-dynamic (checksum 34327000)

| Implementation | Median ms | Range ms | User ms | Neo after × | Paired | Separate |
|---|---:|---:|---:|---:|---:|---|
| **Neo after** | **171.4** | 168.9–183.4 | 170 | — | — | — |
| Neo before | 172.8 | 171.5–189.2 | 170 | 1.01× | 18/21 | no |
| Rust serde_json::Value | 346.4 | 341.1–369.0 | 350 | 2.02× | 21/21 | yes |
| Zig Value arena | 407.6 | 401.8–425.6 | 410 | 2.38× | 21/21 | yes |
| Zig Value | 997.6 | 986.8–1038.2 | 500 | 5.82× | 21/21 | yes |

