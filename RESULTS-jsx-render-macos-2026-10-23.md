# Shared TSX rendering workload: transformer optimization

Measured 2026-10-23 on Apple M1 Pro, native ARM64 macOS. This excludes HTTP and sockets.

| Renderer | Median documents/sec | Run range documents/sec | Median CPU µs/document |
|---|---:|---:|---:|
| Axon baseline | 1,924,160 | 1,909,747–1,930,461 | 0.515 |
| Axon optimized | 4,723,827 | 4,618,081–4,737,763 | 0.207 |
| Bun + React | 155,605 | 153,172–162,059 | 7.282 |

Optimized native throughput is **2.46× the original native throughput**, with **59.8% less CPU per document**. It is **30.4× Bun/React throughput** for this workload.

## Workload and interpretation

The same `page.tsx` is translated with optimizations disabled/enabled and also executed by production React `renderToStaticMarkup` on Bun 1.3.13 / React 19.2.8. Each run renders 500,000 documents, cycling through counts 1..1000, and sums every UTF-8 byte. Five rounds shuffle renderer order. Every measured checksum matches the React reference corpus. An unmeasured 1,000-document run for each implementation warms executable and filesystem caches.

Both native renderers share one executable and are selected by a mode argument. AXON_THREADS=1 ensures serial execution. Each measurement starts a fresh process; wall/CPU include startup, UTF-8 encoding and checksum work. This is a complete rendering workload, not isolated render-call timing. React uses general component-tree rendering; native code specializes the supported TSX subset. These ratios do not establish arbitrary React compatibility or overall HTTP performance.

The transformer coalesces static markup, pre-escapes literal text, distributes escaping over template fragments, expands bounded component trees, and shares repeated unconditional escaped props and integer formatting. It retains conditional branch selection and does not cache responses. Axon core/compiler/runtime are unchanged.

The HTTP comparison is in [the optimized HTTP report](RESULTS-jsx-ssr-optimized-macos-2026-10-23.md).

Raw commands, all runs, checksums, archived executable and generated source: `bench/http/results/2026-10-23-224258-jsx-render`.
