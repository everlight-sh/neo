# Prepared-library inlining budgets

This describes the Python reference compiler, which is in the `v0.2.4` tag
and no longer in the repository. The native compiler's `--library-cache`
links a prepared object of the dependency closure; it keeps no inlining hints
and applies none of these budgets.

The reference compiler prepares dependency objects and retains
pre-optimization LLVM bodies as application optimization hints. Checked return-alias facts are retained across
warm builds. Application code is checked and compiled for each application;
prepared objects contain dependency code.

Inlining uses two distinct limits:

- The lowered body-size limit controls which small-source helpers are eligible
  for forced inlining. Generic ownership and cleanup can make a short source
  function much larger in LLVM IR.
- A caller expansion budget limits transitive forced calls, including repeated
  calls. An expensive edge receives a call-site `noinline` attribute. The same
  helper can still inline in other callers. Explicit `inline` requests remain
  mandatory; the budget is a heuristic for forced expansion, not a bound on all
  subsequent LLVM optimization or on a function's original size.

The dependency-object budget is capped at 32,768 IR lines for pure functions
and 8,192 for effectful functions and generated helpers. The larger pure
budget preserves inlining through validated JSON indexing loops. The smaller
effectful budget limits expansion in I/O loops. Cold preparation can take
longer for large dependency graphs. Warm builds reuse the compiled object. The
application uses its configured expansion budget. Its hints precede object-local
call constraints as well as LLVM optimization, so an object budget cannot leak
into application specialization. Object input and hint input both participate in
the cache key; their files and checksums are validated on reuse.

Previously, exceeding a budget removed a helper's forced-inlining attribute
globally. A large runtime caller could therefore change unrelated JSON,
escaping and hashing code. Applying the object budget again to application
hints also prevented useful specialization in larger application functions.
Caller-local constraints and separate pre-budget hints avoid these interactions
without raising the object budget or adding framework-specific compiler rules.

`tests/test_inline_cost.py` checked independent callers, transitive expansion,
explicit requests, metadata placement, LLVM backend behavior and the separate
object/application budgets. `tests/native_library_cache.py` exercised actual
cold/warm compilation, deterministic binaries, optimization hints, dependency
invalidation, ownership facts, effects, corruption repair and async callbacks.
Both tested Python-only machinery and were dropped rather than ported.
