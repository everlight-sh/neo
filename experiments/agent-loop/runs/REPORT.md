# REPORT: runs.neo

## Result

- Compile attempts: 1 (2 "=== " timestamped lines in attempts.log: one `check`, one `build`, both on the first and only try).
- Final binary matched expected output: **yes**.
  - `./runs 1000` -> `334` (expected 334)
  - `./runs 10` -> `4` (expected 4)

## Approach

Two functions:

```
fn count_runs (v : Arr u8 n) -> i64 {result >= 1}
  = loop (count : i64{count >= 1} = 1, i : i64{i >= 1} = 1)
      while i < n
      next (if v[i] != v[i-1] then count + 1 else count, i + 1)
      yield count

fn main (n : i64{n >= 1}) -> i64
  = let v = arr(i in 0..n) u8((i / 3) % 5) in
    count_runs(v)
```

The array size `n` was left implicit, bound from `v`'s type (`Arr u8 n`), following the
pattern in `examples/sieve.neo`'s `mark` function, rather than threading `n` as a second
explicit parameter. The run count is a loop starting at `i = 1, count = 1` (the first
element is always the start of a run) that walks forward and bumps `count` whenever
`v[i] != v[i-1]`.

The key requirement called out in the task -- proving `v[i-1]` in range -- fell out
directly from the loop's own invariant. Declaring the loop state as
`i : i64{i >= 1} = 1` and gating the body with `while i < n` gives the checker
`1 <= i < n` as a fact inside the loop body, from which both `0 <= i < len(v)` and
`0 <= i-1 < len(v)` are linear consequences that Fourier-Motzkin discharges without
help. No `check` node was needed anywhere in the program.

## Diagnostics that led to fixes

None were needed -- `neoc check` reported all 11 obligations proven (10 proven + 1
"checked" boundary condition for `n >= 1` at argv parsing, which is inherent to `main`
taking arguments from argv, not something the program body needs to prove) on the very
first attempt, and `neoc build` succeeded immediately after. No iteration was required
for this program.

The only thing worth noting from the `check` output as a "diagnostic that confirmed the
design was right": obligation ids 3 and 4 in the JSON were exactly the two bounds
obligations the task predicted (`0 <= i && i < len(v)` and `0 <= (i-1) && (i-1) < len(v)`),
and both came back `"status": "proven"` with the invariant `i >= 1` (from the loop state
refinement) doing the work -- confirming that putting the lower bound directly in the
loop-state refinement, rather than e.g. trying to derive it from an `if i == 0` branch
guard or a `check`, was the right call.

## Where I got stuck

Nowhere -- this task went through cleanly on the first compile/build pass. I attribute
this mostly to `examples/sieve.neo` and `examples/stencil.neo` already demonstrating the
two techniques this program needed: (1) `stencil.neo`'s comment explicitly says
`xs[i-1]` and `xs[i+1]` obligations are discharged from range facts plus branch
conditions, which pointed directly at using a loop invariant (`i >= 1`) as the range
fact instead of an `if i == 0` branch guard; (2) `sieve.neo`'s `mark` function showed
that an array parameter's size variable (`n` in `Arr T n`) can be used directly without
redeclaring it, which is what let `count_runs` take just `v : Arr u8 n` and use `n` in
the `while i < n` condition.

## What was missing or unclear in the README

- The README's loop-invariant feature is only described in one dense sentence near the
  end of the "Language" section ("A loop state may carry an invariant, `loop (i :
  i64{i >= 0} = 0, ...)`: the checker proves it holds initially and is preserved by
  `next`, and uses it as a fact inside the loop.") rather than shown as a full worked
  example the way `stencil.neo`/`sieve.neo` are referenced elsewhere in the README. I had
  to infer the exact placement of the refinement (`count : i64{count >= 1} = 1`,
  refinement attached to the *state name*, not the initial value or the `next` clause)
  from that one sentence alone; a short literal code snippet analogous to the top-level
  `stencil`/`main` example, showing a loop state with an explicit invariant end-to-end
  (declaration, `next`, and how it is used as a fact inside the loop body for an index
  computation), would have removed the need to guess at the syntax before the first
  compile.
- It is not documented whether `!=` is a supported binary operator -- none of the five
  example programs use it (only `==` appears, in `stencil.neo`'s `if i == 0 || i + 1 ==
  n`). I used `!=` on a hunch since it's a common operator and it compiled fine, but a
  reader relying only on the README's expression list (`let ... in`, `if ... then ...
  else`, `sum`, `arr`, `loop`, `check`, `len`, casts, `sqrt`, byte strings/literals,
  record syntax) would not know `!=`, `<`, `>=`, `&&`, `||`, etc. are available as
  operators at all -- these are only discoverable by seeing them used in example bodies
  (`stencil.neo`, `mandel.neo`) rather than being listed as part of the grammar in the
  README itself. A short "operators" line (arithmetic, comparison, boolean) would make
  this fully self-contained instead of relying on inference from examples.
- The distinction between an array's implicit size variable (bound from a parameter's
  `Arr T n` type, as in `sieve.neo`'s `mark`) versus an explicit `i64` size parameter
  used to build new arrays (as in `sieve.neo`'s `count_primes`, which takes `n : i64` and
  builds `Arr bool (n+1)`) is demonstrated by example but never stated as a general rule
  ("a function may either bind an array's size implicitly from an `Arr T n` parameter,
  or take an explicit `i64` parameter and use it in array-size expressions"). This is a
  minor point since the examples do disambiguate it, but a one-line rule statement would
  have saved the moment of hesitation over whether `count_runs` needed its own `n : i64`
  parameter in addition to `v : Arr u8 n`.

Overall this was a clean, unremarkable success: the task's own hint ("comparing v[i]
with v[i-1] requires proving i-1 is in range") pointed straight at the loop-invariant
mechanism `stencil.neo` already documents, and the program compiled, built and ran to the
expected output on the first try.
