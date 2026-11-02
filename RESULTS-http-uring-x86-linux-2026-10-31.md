# HTTP: io_uring backend, x86-64 Linux (2026-10-31)

Follows the compiler round in `RESULTS-compute-db-x86-linux-2026-10-30.md`, where HTTP stayed at 1.14×
Rust. The question was whether fewer system calls per request could reach 2×.

`runtime/http_uring.ax`; the default on x86-64 Linux since this round (see "Default" below). Same binary, same request parsing and
rendering (`rt_prepare`), only the event loop differs, so epoll and io_uring are measured from one
executable. Temporary Vultr `voc-c-8c-16gb-150s-amd` (8 dedicated AMD vCPUs; four for the server, four
for `wrk -t4 -c64`), Ubuntu 24.04, Linux 6.8.0, clang 18.1.3, rustc 1.99.1; destroyed afterwards. Rust is
hyper/tokio with `pipeline_flush`. Medians of five interleaved 10 s runs after a 2 s warm-up. Server CPU
per request is user + system time of every server process (from `/proc`) divided by completed requests.

| Workers | Server | req/s | p50 | p99 | CPU/request (user + kernel) | vs Rust |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Rust | 88,802 | 713 µs | 970 µs | 1.52 + 9.80 = 11.32 µs | |
| 1 | Axon epoll | 98,051 | 638 µs | 870 µs | 0.76 + 9.39 = 10.15 µs | 1.10× |
| 1 | Axon io_uring | **118,817** | 516 µs | 739 µs | 0.19 + 8.20 = **8.39 µs** | **1.34×** |
| 2 | Rust | 142,923 | 447 µs | 713 µs | 2.74 + 11.06 = 13.79 µs | |
| 2 | Axon epoll | 191,908 | 305 µs | 649 µs | 0.77 + 9.63 = 10.40 µs | 1.34× |
| 2 | Axon io_uring | **213,863** | 288 µs | 379 µs | 0.20 + 9.14 = **9.34 µs** | **1.50×** |
| 4 | Rust | 268,256 | 220 µs | 439 µs | 3.15 + 10.34 = 13.49 µs | |
| 4 | Axon epoll | 318,563 | 100 µs | 247 µs | 1.04 + 9.81 = 10.85 µs | 1.19× |
| 4 | Axon io_uring | 309,895 | 103 µs | 245 µs | 0.62 + 9.51 = 10.13 µs | 1.16× |

- One worker: every io_uring round (114–129k req/s) beat every epoll round (92–110k).
- Four workers are client-bound: the servers are 78–90% busy while four `wrk` threads saturate their
  CPUs, so io_uring's lower CPU per request (1.33× less than Rust, 7% less than epoll) does not show as
  throughput. Two workers on two CPUs are server-bound and show it.
- Why not 2×: kernel time is 77–98% of every server's CPU per request. A profile of the server CPU is
  flat: TCP send/receive, socket buffers, netfilter/conntrack (about 6% on this image), timekeeping and
  the AMD return-stack mitigation. On loopback the server's CPU also runs the client socket's receive
  path and wake-up. io_uring cuts Axon's user time to 0.19 µs (Rust: 1.52 µs) and the kernel time by
  0.3–1.2 µs (fewer system calls, batched submissions), but the TCP work stays.

On the 2-vCPU box used for development (one `wrk` thread, client-bound at ~80k req/s), server CPU per
request was Rust 11.51 µs, epoll 10.65, io_uring 10.08, and io_uring with `IORING_RECVSEND_POLL_FIRST`
9.83 µs; the last is the shipped default.

### Design

- One ring per worker process (`SINGLE_ISSUER | DEFER_TASKRUN | SUBMIT_ALL`, 2048 submissions, 4096
  completions; at most 1026 operations are ever in flight). Completions are only posted inside the
  worker's own `io_uring_enter`.
- Each loop is one `io_uring_enter`: it publishes every queued submission and waits for a completion
  (one-second timeout via `IORING_ENTER_EXT_ARG`, so orphaned workers still exit).
- A connection has at most one operation in flight, a receive or a send, so states are dropped and
  reused only when nothing references them (free slots are reused; no compaction). Connection sockets
  stay blocking, as io_uring expects.
- Receives use `IORING_RECVSEND_POLL_FIRST`: after a response the next request cannot be there yet.
- Accepts keep the epoll backend's round-robin turn: the listener and the worker notification socket are
  polled through the ring and accepted with `accept`; `rt_accept` became `rt_accept_at` so both backends
  share it.
- If the ring cannot be created (Linux before 6.1, Docker's default seccomp profile), the worker runs
  the epoll backend; with `AXON_HTTP_URING=1` it also prints `axon: io_uring unavailable, serving with
  epoll`.
- Compiler: new `atomic_load_i32` (acquire) and `atomic_store_i32` (release) for the ring head and tail
  words. Platform: `rt_map_ring` (shared, prefaulted mmap) for x86-64 and ARM64 Linux; only x86-64 was
  run.

### Default

io_uring is the default HTTP backend on x86-64 Linux (`rt_uring_default` in
`runtime/platform_linux_x86_64.ax`). ARM64 Linux keeps epoll unless `AXON_HTTP_URING=1`, because io_uring
has not been run there. `AXON_HTTP_URING=0` selects epoll; `AXON_HTTP_POLL=1` still selects the older
ppoll loop. Containers under Docker's default seccomp profile fall back to epoll silently.

### Verification

- Compiler unit tests: 137 pass, including the new `atomic_load_i32`/`atomic_store_i32` gating and
  codegen test in `tests/test_systems.py`.
- `tests/http_smoke.py` now runs every case on Linux three times: epoll with N workers, io_uring with N
  workers and io_uring with one worker, and asserts the ring is open. All pass on both boxes (three
  consecutive runs on the 2-vCPU box): endpoints and checksums, 100 concurrent requests, slow readers,
  fragmented POST with pipelining, 512 pipelined responses across batch limits, ready-batch close and
  descriptor reuse, backpressure over 80 large responses, invalid framing, and
  `bench/http/protocol_test.py`.
- Language integration: the other 56 scripts pass. Its first `http_smoke` run failed in the new ring
  check, not the server: the listener completes TCP handshakes before worker 0 has created its ring, so
  on two vCPUs the check ran too early. It now waits up to five seconds.
- axon-kv integration: 27/27.
- Both temporary boxes were destroyed; Vultr lists no servers or volumes afterwards.

After making io_uring the default (third temporary instance, 2 vCPUs, destroyed afterwards): compiler
unit tests pass, `tests/http_smoke.py` passes on the default (io_uring) backend with 4 and 1 workers and
on `AXON_HTTP_URING=0`, language integration 57/57 (every HTTP-serving script now runs on io_uring),
axon-kv 27/27. With `kernel.io_uring_disabled=2` the default serves with epoll silently,
`AXON_HTTP_URING=1` serves with epoll and prints the note, and `AXON_HTTP_URING=0` serves with epoll;
with io_uring available the default and `=1` open a ring and `=0` does not.
