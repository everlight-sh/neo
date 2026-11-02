# React-style TSX compiled to Neo

This example takes the **same TSX components** through two renderers:

```text
page.tsx -> example translator -> ordinary .neo functions -> neoc -> native HTTP server
    |
    +----> Bun + React renderToStaticMarkup (reference implementation)
```

`page.tsx` contains `Page`, `Card`, and `Badge`. Components have typed props,
nested children, conditions, template strings, text, and attributes. Props are
supplied on each HTTP request, so this is server-side rendering rather than a
collection of prerendered files. `/page/13` deliberately includes script-like
text, quotes, and Unicode to demonstrate escaping.

Everything is local to this example. **No Neo syntax, compiler, or runtime
changes are involved.** `compile.ts` uses TypeScript's AST as a build tool and
emits functions such as `jsx_Card(title, children)`. String props are escaped
where they enter HTML; already rendered children are composed without escaping
them again. `html.neo` supplies ordinary Neo HTML helpers and `server.neo`
supplies routing and props. The build combines these into one Neo source file.

The translator coalesces static HTML, escapes literals during the build,
expands small component trees so children can join the parent output directly,
and shares repeated unconditional escaped props and formatted numbers within
one render. Numeric output is already HTML-safe. Template string fragments
are escaped separately, avoiding an intermediate unescaped string. Component
expansion is bounded by depth and call count; large trees retain function calls.
Conditional work stays inside its selected branch. There is no cross-request
memoization or response cache. Set `NEO_JSX_OPT=0` when building to reproduce
the original translator output for differential testing.

This does **not** execute React or arbitrary JavaScript inside Neo. It is a
small, explicit React-compatible TSX subset. Actual React runs only in the
reference server and tests. [React's `renderToStaticMarkup`](https://react.dev/reference/react-dom/server/renderToStaticMarkup)
produces non-interactive HTML that cannot be hydrated; that is the comparison
target here.

## Run

From this directory:

```sh
bun install --frozen-lockfile
bun run build
NEO_THREADS=1 ../../.kernel-build/jsx-ssr/server 8092
```

In another terminal in this directory:

```sh
bun run react 8093
```

Open [Neo](http://localhost:8092/) and [React](http://localhost:8093/).
Both accept `/`, `/page/1` through `/page/1000`, and query strings. Even counts
show the badge. The route passes `name`, `count`, and `featured` to `Page`.
There is no page cache. Invalid counts return 400, missing routes 404, and
non-GET methods 405.

Generated files are in `.kernel-build/jsx-ssr/` at the repository root:
`components.neo` is the component output; `server.neo` is the complete source;
`server` is the native executable. `bun run build /absolute/output/path` chooses
another binary path. The final executable never reads the TSX or JavaScript.

Bun and TypeScript are build tools, and Python/LLVM remain Neo's build tools.
On ARM64 Linux the executable is static with no libc, JavaScript engine,
interpreter, or shared libraries; it still uses kernel syscalls. On ARM64 macOS
there are zero undefined function imports, but the OS loader still requires
libSystem/dyld. This example preserves the existing runtime guarantees.

## Deliberate subset

- Synchronous function components with one destructured argument and inline,
  required prop types: `string`, `number`, `boolean`, or `ReactNode`.
- A single return expression; nested components and `children`; fragments.
- String literals, template strings, nonnegative integer literals and props,
  boolean props, `null`, integer comparisons, ternaries, and boolean `&&`.
  `number` means **nonnegative safe integers**, not JavaScript floating-point
  numbers. This demo only supplies counts 1..1000. There is no arithmetic or
  JavaScript coercion in the translator.
- A fixed set of simple HTML tags (listed in `compile.ts`), plus `br` and `hr`.
  Attributes: `id`, `className`, `title`, `lang`, `role`, `data-*`, and `aria-*`;
  values must be strings or nonnegative integers. Text and attributes use
  React-compatible escaping. Common XML and numeric character entities work.

Unsupported input produces a source-located build error: hooks, effects,
state, async functions, event handlers, styles, spreads, arbitrary function
calls, JavaScript imports, loops, arrays, component recursion, raw HTML, and
other HTML tags/attributes. No hydration, Suspense, React Server Components,
React package compatibility, or general React semantics are promised. The
prototype covers the supplied page; new constructs should come with parity
tests before extending the whitelist. React text-only elements such as
`title` should contain one text expression, as in this example.

For full React compatibility, a separate JavaScript renderer would still be
needed. This prototype demonstrates a way to reuse simple component source
while keeping the deployed Neo server native and independent of React.

## Verify

```sh
bun test
cd ../..
python3 tests/jsx_ssr_smoke.py --binary .kernel-build/jsx-ssr/server
```

The smoke test compares **all 1,000 valid counts byte for byte against actual
React rendering of the same TSX file**, then checks routing, escaping, Unicode,
keep-alive, 100 concurrent requests and 129 ordered pipelined responses. It
runs with one and four Neo workers, and also checks the Bun/React HTTP server.
`nm` audits imports; on Linux, `readelf` also audits the interpreter and shared
library lists. As root on Linux, add `--empty-root` to repeat the test in a
chroot containing only the generated executable.

The earlier catalog benchmark measures the separate hand-written
[Neo SSR example](../README-ssr.md), **not this TSX translator**; its numbers
should not be attributed to this prototype.

## Benchmark the shared TSX page

From the repository root, after building the example:

```sh
python3 bench/http/compare_jsx_ssr.py --neo .kernel-build/jsx-ssr/server
```

The benchmark compares one Neo rendering worker against one Bun/React
rendering worker in production mode. It measures the normal page at one and
64 connections, then the conditional badge and escaping/Unicode variants at
64 connections. Each comparison gets a two-second warm-up and three measured
five-second runs. It verifies all 1,000 valid inputs before every comparison
and preserves per-run logs, CPU/memory samples, source/binary hashes and the
React reference bodies. Reports are written to `RESULTS-jsx-ssr-<platform>-<date>.md`;
raw data goes under `bench/http/results/*-jsx-ssr/`.

The count prop changes text and conditionals, not the number of components.
These are small page variants; this benchmark does not establish performance
for large React trees, arbitrary React code, or hydration.

To include a fresh comparison with a saved original binary, add
`--baseline /absolute/path/to/original-binary --report /absolute/report.md`.
The original generated source must be saved at
`.kernel-build/jsx-ssr/baseline-server.neo` for the source manifest. Reports
include baseline/optimized comparisons alongside Bun/React. Keep the initial
report and raw measurements when making later optimization comparisons.

For rendering without HTTP, generate a binary containing both translator
variants and run the separate checksum workload:

```sh
cd examples/jsx-ssr
bun run build-render-bench.ts
cd ../..
python3 bench/http/compare_jsx_render.py
```

It cycles through all 1,000 prop values and checksums every byte of every
rendered document. Both native variants share one executable, selected by
an argument; React renders the same source and encodes UTF-8. Results include
process startup and checksum work, so they measure a rendering workload,
not isolated function-call time. Five rounds shuffle the three implementations.

Measured results on the native M1 Pro are in the
[optimized HTTP report](../../RESULTS-jsx-ssr-optimized-macos-2026-10-23.md) and
[rendering workload report](../../RESULTS-jsx-render-macos-2026-10-23.md).
The [original HTTP report](../../RESULTS-jsx-ssr-macos-2026-10-23.md) remains
available. The optimized HTTP report includes a fresh original-binary
comparison and records an invalid attempt with one timeout and its clean rerun.

For runtime Docker images compared with Rust and Bun under CPU/memory limits,
see the [container benchmark](../../bench/docker/README.md).
The [Linux epoll report](../../RESULTS-http-epoll-docker-linux-2026-10-24.md)
includes fresh Rust/Bun results and both Neo HTTP backends.
