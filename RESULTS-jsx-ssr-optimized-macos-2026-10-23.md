# Shared TSX: native Axon versus Bun + React

Measured 2026-10-23T22:43:27.045620+02:00; Apple M1 Pro; 10 logical CPUs; Darwin 27.0.0.

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
| Axon JSX | 35,402 | 35,134–35,451 | 9.50 | 26 | 63 | 1.66 | 1.20 | 0 / 0 | True |
| Bun + React | 20,954 | 20,880–20,983 | 27.90 | 42 | 286 | 196.22 | 39.69 | 0 / 0 | True |
| Axon baseline | 35,259 | 34,321–35,288 | 9.74 | 26 | 64 | 1.67 | 1.22 | 0 / 0 | True |

Axon/Bun throughput ratio: **1.69×**. Axon uses **66.0% less server CPU per request** in this case.

Optimized/baseline throughput ratio: **1.004×**; server CPU/request change: **-2.4%**. Compare run ranges before interpreting small changes.

### base-c64: /page/3, 64 connection(s)

Identical HTML body: 518 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Peak RSS MiB | Peak macOS physical footprint MiB | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 115,832 | 115,682–116,144 | 8.51 | 555 | 1070 | 2.89 | 2.44 | 0 / 0 | True |
| Bun + React | 44,027 | 42,329–44,031 | 22.87 | 1380 | 2680 | 213.66 | 50.22 | 0 / 0 | True |
| Axon baseline | 109,351 | 108,380–109,515 | 9.05 | 585 | 1130 | 2.91 | 2.45 | 0 / 0 | True |

Axon/Bun throughput ratio: **2.63×**. Axon uses **62.8% less server CPU per request** in this case.

Optimized/baseline throughput ratio: **1.059×**; server CPU/request change: **-5.9%**. Compare run ranges before interpreting small changes.

### badge-c64: /page/2, 64 connection(s)

Identical HTML body: 571 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Peak RSS MiB | Peak macOS physical footprint MiB | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 113,008 | 109,448–113,055 | 8.77 | 569 | 1100 | 2.89 | 2.44 | 0 / 0 | True |
| Bun + React | 42,742 | 42,600–42,840 | 23.31 | 1410 | 2760 | 229.67 | 53.03 | 0 / 0 | True |
| Axon baseline | 108,647 | 108,058–109,649 | 9.08 | 591 | 1130 | 2.91 | 2.45 | 0 / 0 | True |

Axon/Bun throughput ratio: **2.64×**. Axon uses **62.4% less server CPU per request** in this case.

Optimized/baseline throughput ratio: **1.040×**; server CPU/request change: **-3.4%**. Compare run ranges before interpreting small changes.

### escape-c64: /page/13, 64 connection(s)

Identical HTML body: 565 bytes.

| Server | Median req/s | Run range req/s | CPU µs/req | p50 µs | p99 µs | Peak RSS MiB | Peak macOS physical footprint MiB | Errors / non-2xx | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Axon JSX | 109,329 | 99,628–112,589 | 8.83 | 575 | 1200 | 2.89 | 2.44 | 0 / 0 | True |
| Bun + React | 42,133 | 41,757–42,146 | 23.74 | 1440 | 2800 | 229.39 | 51.47 | 0 / 0 | True |
| Axon baseline | 106,414 | 106,347–106,975 | 9.27 | 601 | 1150 | 2.91 | 2.45 | 0 / 0 | True |

Axon/Bun throughput ratio: **2.59×**. Axon uses **62.8% less server CPU per request** in this case.

Optimized/baseline throughput ratio: **1.027×**; server CPU/request change: **-4.7%**. Compare run ranges before interpreting small changes.

## Deployment size and runtime dependencies

| Server | Executable + app/runtime packages MiB |
|---|---:|
| Axon JSX | 0.03 |
| Bun + React | 67.38 |
| Axon baseline | 0.03 |

Axon size is its executable. Bun size includes its executable, the reference app sources and installed react/react-dom/scheduler packages; TypeScript, the translator and other build tools are excluded. OS libraries are excluded from both.

The generated Linux executable is static, with no undefined imports, ELF interpreter or shared libraries. macOS imports no libc functions but retains the required libSystem/dyld loader dependency. Python/LLVM and Bun/TypeScript are build tools for the native example. The Axon renderer supports only the documented example TSX subset.

Commands, binary/source hashes, per-run measurements, CPU/memory samples, reference bodies and logs: `bench/http/results/2026-10-23-224327-jsx-ssr`.

## Recorded invalid attempt

One original optimized base-c64 measured run reported one timeout; warm-up and other runs had zero errors. The invalid attempt and logs are preserved. A separately recorded rerun with identical settings is used for this cell.
The table uses the clean rerun; the observed timeout remains part of this experiment. It has not been attributed to a root cause or fixed by this optimization.

## Optimization and verification

Changes are confined to the example translator: coalescing static markup; escaping static text at build time; bounded component expansion; distributing text escaping over template fragments; sharing repeated unconditional escaped strings and formatted integers. There is no response cache. Axon compiler and runtime sources are unchanged.
The rendering workload improved from 1.92 million to 4.72 million documents/sec (2.45×), with 59.8% less CPU per document. It includes UTF-8 byte checksumming and process startup; the HTTP gains are smaller. See [the rendering report](RESULTS-jsx-render-macos-2026-10-23.md).
The concurrent HTTP cells show about 3–6% more median throughput than the freshly measured original binary; the one-connection change is small (0.4%) and should be treated as unchanged. These are short measurements on a shared host. The affected base-c64 cell uses the explicitly recorded clean retry.
31 translator tests and 28 compiler unit tests passed. Optimized native output matched React for all 1,000 inputs on macOS and Linux, with one/four workers, concurrent and pipelined HTTP checks. The optimized ARM64 Linux binary has no undefined imports, interpreter or shared libraries and passed from an empty root containing only the executable.
The measurement-time benchmark driver is archived as measurement-harness.py. Subsequent changes to the current driver only add report annotations and suppress ratios for invalid cells; report_renderer_sha256 records that version.
