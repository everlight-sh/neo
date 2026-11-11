# Runtime stream: native compiler failures

Cases of the runtime stream (`tests/runtime.neo.toml`) that the native
compiler (`neoc` of `chore/remove-python`) gets wrong. Each one is left out of
the manifest (or out of its driver) until the compiler is fixed. Commands run
from the repository root with `NEO_ROOT` set to it, on x86_64 Linux.

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
