# Docker SSR preflight at 512 MiB

This preliminary harness check used one-second warm-up and one one-second load
run, not the final benchmark protocol. Each server container had 512 MiB,
no swap, the same CPU affinity/quota, nonroot UID, read-only root and dropped
capabilities. Image artifacts and successful one-worker cases are retained in
the raw JSON; their short timing numbers are not used as final results.

All four initial variants (Neo, static-musl Rust, Bun direct, Bun React)
passed byte-for-byte checks for all 1,000 valid prop values, HTTP error routes,
Unicode/escaping, concurrent requests and pipelining with one rendering worker.

The four-worker Bun/React container passed correctness checks, then was
OOM-killed during the first warm-up load. The Docker Engine emitted an `oom`
event for container
`1e24a9ecc6c554c8f51e6d80eacd66fe714d04fcce8e9d2489f502c0bd22edac`.
The warm-up recorded 138 read errors and 4,603 write errors; the first intended
measured run could not connect because the server was gone. This is a failed
512-MiB configuration, not a throughput measurement. Other four-worker variants
were not reached by that initial driver attempt; no result is inferred for them.

The main comparison gives every variant the same 1-GiB limit. A separate
one-second preflight at 1 GiB passed for all initial variants with one and four
workers. A glibc build of the same Rust source is additionally included in the
main comparison to distinguish runtime-library and packaging choices.

Evidence: `bench/http/results/2026-10-23-213157-docker-ssr/oom-evidence.json`,
`measurements.json`, `w4-bun-react-server.log`, `w4-bun-react-warmup.txt` and
`w4-bun-react-1.txt`. The original measurement-time harness is archived alongside
them. The driver now preserves failed-container state and continues other cases.
