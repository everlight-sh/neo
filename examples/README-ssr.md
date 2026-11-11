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

From the repository root, on ARM64 macOS or Linux with Clang:

```sh
./neo build examples/ssr.neo -o /tmp/neo-ssr
NEO_THREADS=1 /tmp/neo-ssr 8090
```

Open <http://localhost:8090/> or <http://localhost:8090/page/50>.
Omit `NEO_THREADS=1` to use one HTTP worker process per configured CPU.
Linux produces a static executable with no libc, CRT, interpreter or shared
libraries. Mac imports no libc functions, but Apple's libSystem/dyld loader
requirement remains. Clang/LLVM are build tools, and both need the OS kernel.

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

From the repository root:

```sh
./neo test tests/runtime.neo.toml
```

Its case `ssr-exact-pages-and-pipelining` (driver `tests/drivers/ssr_smoke.neo`)
builds `examples/ssr.neo` and, with one and four workers, checks exact pages
for nine sizes against frozen digests of the earlier Python renderer, escaping,
content lengths, valid/invalid routes, keep-alive, 100 concurrent requests and
129 ordered pipelined pages. It does not start the Bun + React server, and
the old `--empty-root` mode is not ported for this example: the opt-in
`NEO_TEST_ROOT_CHECKS=1` check described in the README runs
`examples/http.neo` from an empty root instead.

The Bun + React comparison benchmark, `bench/http/compare_ssr.py`, is not
ported; it is in the `v0.2.4` tag. It used 3, 50 and 1,000 rows, three
five-second samples after a two-second warm-up, and 64 connections, and
recorded throughput, latency, CPU per request, memory across every worker and
deployment size. Measured routes were `/page/N`, with the count parsed from
each request and no response cache. Its raw logs are under
`bench/http/results/`. `./neo run --dev bench/run.neo -- servers` compares
`examples/http.neo`, not this example, with Rust, Go and Bun servers (see the
README's benchmark section and `bench/http/compare.neo`).

Measured reports: [native Mac](../RESULTS-ssr-macos-2026-10-23.md) and
[static Linux](../RESULTS-ssr-linux-2026-10-23.md). The older
`RESULTS-http-ssr.md` describes the removed C runtime and different React
settings; use the new reports for these standalone examples.

Compare Neo with one worker to Bun + React for the single-rendering-worker
case. Neo's default worker count shows additional parallel capacity. React
builds a general component tree; Neo directly constructs HTML for this
page. These examples compare that tradeoff, not equivalent UI frameworks.
