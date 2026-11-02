# Shared TSX: native Axon versus Bun + React

Measured 2026-10-23T22:31:03.352349+02:00; Apple M1 Pro; 10 logical CPUs; Darwin 27.0.0.

Both servers use the same examples/jsx-ssr/page.tsx source. The example translator compiles its supported TSX subset into ordinary Axon rendering functions. The reference executes the components with React renderToStaticMarkup on Bun. Props are supplied and HTML is rendered on every request; there is no response cache or client JavaScript. This measures specialized native rendering against the general React renderer, not arbitrary React compatibility or universal language speed.

Both have one rendering worker and one server process; Bun background threads are included in CPU and memory measurements. This is a worker budget, not CPU affinity. The HTTP stacks and route parsers differ. No multicore Axon capacity is mixed into the headline comparison.

Bun 1.3.13; React/react-dom 19.2.8. Each server/case has 3 measured runs of 5s after 2s warm-up. wrk uses one client thread at one connection, otherwise 4 threads at 64 connections, without pipelining. Server order is shuffled with seed 20261023.

The normal page is /page/3; /page/2 adds a conditional badge; /page/13 changes the prop to script-like text, quotes and Unicode. The count is displayed and controls branches; it does not repeat components or increase row count. These are small page variants, not a scaling benchmark.

Before timing, the full smoke suite compares all 1,000 valid inputs byte-for-byte with React, checks one/four Axon workers, routing, escaping, Unicode, 100 concurrent requests and 129 pipelined responses. Every timed server is also checked against all 1,000 reference outputs before warm-up. Raw React reference bodies and preflight output are preserved.

CPU/request includes all server threads and user + kernel time. Memory is sampled every 100 ms; footprint means macOS physical footprint. Peak memory covers all measured repeats and is not per-request allocation. The client shares the host with the server. wrk latencies are closed-loop and can hide coordinated omission. Short runs on a shared machine are indicative, not production capacity estimates.

## Results

### base-c1: /page/3, 1 connection(s)

Identical HTML body: 518 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Peak RSS MiB | Peak macOS physical footprint MiB | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 34,559 | 34,550–34,590 | 9.87 | 26 | 67 | 1.67 | 1.22 | 0 / 0 | True |
| Bun + React | 20,329 | 18,109–20,515 | 28.84 | 43 | 299 | 193.66 | 39.61 | 0 / 0 | True |

Axon/Bun throughput ratio: **1.70×**. Axon uses **65.8% less server CPU per request** in this case.

### base-c64: /page/3, 64 connection(s)

Identical HTML body: 518 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Peak RSS MiB | Peak macOS physical footprint MiB | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 108,161 | 108,076–109,058 | 9.08 | 589 | 1140 | 2.91 | 2.45 | 0 / 0 | True |
| Bun + React | 43,489 | 43,386–43,556 | 22.87 | 1390 | 2720 | 210.30 | 50.36 | 0 / 0 | True |

Axon/Bun throughput ratio: **2.49×**. Axon uses **60.3% less server CPU per request** in this case.

### badge-c64: /page/2, 64 connection(s)

Identical HTML body: 571 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Peak RSS MiB | Peak macOS physical footprint MiB | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 107,945 | 107,921–109,076 | 9.10 | 591 | 1140 | 2.91 | 2.45 | 0 / 0 | True |
| Bun + React | 41,943 | 41,215–42,060 | 23.83 | 1440 | 2810 | 212.55 | 51.67 | 0 / 0 | True |

Axon/Bun throughput ratio: **2.57×**. Axon uses **61.8% less server CPU per request** in this case.

### escape-c64: /page/13, 64 connection(s)

Identical HTML body: 565 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Peak RSS MiB | Peak macOS physical footprint MiB | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 107,105 | 105,603–107,189 | 9.22 | 598 | 1140 | 2.91 | 2.45 | 0 / 0 | True |
| Bun + React | 41,798 | 41,670–42,157 | 23.77 | 1440 | 2820 | 211.98 | 50.25 | 0 / 0 | True |

Axon/Bun throughput ratio: **2.56×**. Axon uses **61.2% less server CPU per request** in this case.

## Deployment size and runtime dependencies

| Server | Executable + app/runtime packages MiB |
|---|---:|
| Axon JSX | 0.03 |
| Bun + React | 67.38 |

Axon size is its executable. Bun size includes its executable, the reference app sources and installed react/react-dom/scheduler packages; TypeScript, the translator and other build tools are excluded. OS libraries are excluded from both.

The generated Linux executable is static, with no undefined imports, ELF interpreter or shared libraries. macOS imports no libc functions but retains the required libSystem/dyld loader dependency. Python/LLVM and Bun/TypeScript are build tools for the native example. The Axon renderer supports only the documented example TSX subset.

Commands, binary/source hashes, per-run measurements, CPU/memory samples, reference bodies and logs: `bench/http/results/2026-10-23-223103-jsx-ssr`.
