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

## nbody_worker_smoke / kernel_runtime_smoke: no parallel dispatch

- Script: `tests/nbody_worker_smoke.py` (also the parallel parts of
  `kernel_runtime_smoke.py` and the analysis tested by
  `test_worker_safety.py`).
- Command: `neoc build . examples/nbody.neo -o nbody --report` and
  `neoc build . examples/nbody.neo -o nbody --emit-llvm`.
- What happens: the report has no `parallel_regions` key (the Python script
  asserts every region uses the `ax_par_for_shared` dispatcher), the IR has
  no `ax_par_for` call (the same holds for `examples/mandel.neo`,
  `examples/stencil.neo` and `tests/fixtures/parallel_runtime.neo`), and
  with `NEO_THREADS=4` the program never calls `clone`. Results are correct; the work is serial.
- The ported cases check numerics at `NEO_THREADS` 1 and 4, the static audit
  and that a seccomp filter making `clone` fail with `EAGAIN` changes
  nothing; the dispatcher assertion is left out until the native compiler
  emits parallel regions.
