# Runtime stream: native compiler failures

Cases of the runtime stream (`tests/runtime.neo.toml`) that the native
compiler (`neoc` of `chore/remove-python`) gets wrong. Each one is left out of
the manifest (or out of its driver) until the compiler is fixed. Commands run
from the repository root with `NEO_ROOT` set to it, on x86_64 Linux.

## ssr_smoke: examples/ssr.neo does not build (unproven bounds)

- Script: `tests/ssr_smoke.py`. Case: `ssr-exact-pages-and-pipelining`
  (driver `tests/drivers/ssr_smoke.neo`, stdout `SSR OK\n`, timeout 300),
  not in the manifest.
- Command: `neoc build . examples/ssr.neo -o ssr`
- What happens: the checker cannot prove `buf[k]` in bounds in `escape`
  (`arr(k in 0..total) buf[k]`, where `total` sums `esc_width` over the
  input and `buf` has length `6 * n`), so the build fails. The Python
  compiler proved it.
- Error: `(unproven <root>/examples/ssr.neo 47:27 bounds)`, exit 1.
- With `--allow-unproven` (driver flag changed in a box-only copy) the
  driver passes at 1 and 4 workers: exact pages, routing, 400/404/405,
  100 concurrent requests and 129 pipelined pages. To enable the case once
  the compiler proves it, add:

  ```toml
  [[test]]
  name = "ssr-exact-pages-and-pipelining"
  file = "drivers/ssr_smoke.neo"
  stdout = "SSR OK\n"
  timeout = 300
  ```

## jsx_ssr_smoke: the TSX->Neo server does not build (unproven bounds)

- Script: `tests/jsx_ssr_smoke.py`. Case: `jsx-ssr-react-identical-pages`
  (driver `tests/drivers/jsx_ssr_smoke.neo`, stdout `JSX SSR OK\n`,
  timeout 600), not in the manifest.
- Command: `neoc build . tests/fixtures/jsx_ssr_server.neo -o server`
  (the fixture is the frozen output of `examples/jsx-ssr/compile.neo` for
  `page.tsx` with `html.neo` and `server.neo`).
- What happens: the same `escape` helper (from `examples/jsx-ssr/html.neo`)
  fails to prove `buf[k]` in bounds.
- Error: `(unproven <root>/tests/fixtures/jsx_ssr_server.neo 49:27 bounds)`,
  exit 1.
- With `--allow-unproven` the driver passes: all 1000 pages equal React's
  `renderToStaticMarkup` output (frozen digests) at 1 and 4 workers.

## native_sections: an unused explicit export is dropped

- Script: `tests/native_sections.py`. Case: `native-sections-library-cache`
  (in the manifest without this check).
- Command: `neoc build . main.neo -o whole` (and the same with
  `--library-cache cache --library-root lib`), where `lib/functions.neo` is
  `fn twice(x:i64) -> i64 = x*2` / `export fn public_entry(x:i64) -> i64 = x+17`
  and `main.neo` imports it and calls only `twice`; then `nm whole`.
- What happens: both binaries build and print 42 for 21, but `nm` lists no
  `public_entry`; the only symbol from the library is the internal
  `neo.fn.__m<hash>_twice`. The Python compiler kept unused `export`
  functions through section collection. The driver
  `tests/drivers/native_sections.neo` keeps the build, run and static audit
  and leaves out the `nm` export check.
