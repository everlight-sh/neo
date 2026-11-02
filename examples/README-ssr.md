# Simple server-side rendering: Neo and Bun + React

For shared TSX components translated into native Neo outside the language
core, see the separate [JSX-to-Neo example](jsx-ssr/README.md).

Two standalone servers render the same product catalog. `/` displays three
products; `/page/50` and `/page/1000` generate larger pages. Product names,
prices, stock, escaped notes and the computed total match byte-for-byte.
Neither example ships client JavaScript or hydrates the document.

The Neo example is [`ssr.neo`](ssr.neo). Its `row` and `page` functions build
HTML using byte arrays and `concat`; `escape` handles HTML text. The handler
returns the document through Neo's HTTP runtime. There is no React, Bun, C
runtime or template package in the Neo application.

The React version is [`ssr-react/page.tsx`](ssr-react/page.tsx), with `Row` and
`Page` components rendered by `react-dom/server`'s `renderToString`.
[`ssr-react/server.tsx`](ssr-react/server.tsx) serves it using `Bun.serve`.

## Run Neo

From the repository root, on ARM64 macOS or Linux with Python and Clang:

```sh
./neoc.sh build examples/ssr.neo -o /tmp/neo-ssr
NEO_THREADS=1 /tmp/neo-ssr 8090
```

Open <http://localhost:8090/> or <http://localhost:8090/page/50>.
Omit `NEO_THREADS=1` to use one HTTP worker process per configured CPU.
Linux produces a static executable with no libc, CRT, interpreter or shared
libraries. Mac imports no libc functions, but Apple's libSystem/dyld loader
requirement remains. Python/LLVM are build tools, and both need the OS kernel.

## Run Bun + React

In another terminal, starting from the repository root:

```sh
cd examples/ssr-react
bun install --frozen-lockfile
bun run start 8091
```

Open <http://localhost:8091/> or <http://localhost:8091/page/50>.
The start script sets `NODE_ENV=production`. The React and react-dom versions
are pinned in `package.json` and `bun.lock`.

## Verify and compare

From the repository root, after installing the React example's dependencies:

```sh
python3 tests/ssr_smoke.py --binary /tmp/neo-ssr
python3 bench/http/compare_ssr.py --neo /tmp/neo-ssr
```

The smoke test checks nine page sizes against a Python renderer, escaping,
content lengths, valid/invalid routes, keep-alive, concurrent requests and
129 ordered pipelined pages. On Linux, root can also run
`--empty-root` to verify Neo in a temporary filesystem containing only its
executable. Use a test container for this check.

The benchmark uses 3, 50 and 1,000 rows, three five-second samples after a
two-second warm-up, and 64 connections. It records throughput, latency, CPU
per request, memory across every worker and deployment size. Measured routes
are `/page/N`, with the count parsed from each request and no response cache.
It saves `RESULTS-ssr-{macos,linux}-YYYY-MM-DD.md` and raw logs under
`bench/http/results/`.

Measured reports: [native Mac](../RESULTS-ssr-macos-2026-10-23.md) and
[static Linux](../RESULTS-ssr-linux-2026-10-23.md). The older
`RESULTS-http-ssr.md` describes the removed C runtime and different React
settings; use the new reports for these standalone examples.

Compare Neo with one worker to Bun + React for the single-rendering-worker
case. Neo's default worker count shows additional parallel capacity. React
builds a general component tree; Neo directly constructs HTML for this
page. These examples compare that tradeoff, not equivalent UI frameworks.
