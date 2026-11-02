# REPORT: dot product task

## Compile attempts

`attempts.log` contains 2 lines starting with "=== " followed by a time
(one `check`, one `build`), so **1 compile attempt** (a single check+build
cycle, both of which succeeded on the first try).

## Result

The final binary matches: `./dot 1000` prints `14967`, exactly the expected
value. Also spot-checked the n=1 edge case (`./dot 1` -> `0`, correct since
a[0] = 0 % 7 = 0).

## Program

```
fn main (n : i64{n >= 1}) -> i64
  = let a = arr(i in 0..n) i % 7 in
    let b = arr(i in 0..n) (i * 3) % 11 in
    sum(i in 0..n) a[i] * b[i]
```

## Diagnostics that led to fixes

None needed -- the program compiled and ran correctly on the very first
attempt. `neoc check` reported 7 obligations: 1 `checked` (the
`n >= 1` precondition, verified at the argv boundary per the README's
description of `main`'s special-cased runtime check) and 6 `proven`
statically (both moduli's divisor-nonzero obligations, both arrays'
`0 <= n` range obligations from the `arr` comprehensions, and both
`a[i]`/`b[i]` bounds obligations inside the `sum`). No unproven obligations
and no `check` annotations were required. This was expected: the pattern
(`arr(i in 0..n) ...` then `sum(i in 0..n) a[i] * b[i]`) is essentially the
same shape as the `stencil`/`sieve` examples in the README, where the loop
variable `i` ranging over `0..n` is automatically in bounds for arrays of
length `n`, and `%`'s divisor is a nonzero integer literal so the
division-by-zero obligation is trivially discharged.

## Where I got stuck

Nowhere -- this task did not require iteration. Reading the README's
"Language (textual projection)" section and the `sieve.neo`/`nbody.neo`
examples was enough to write a program that satisfied the checker
immediately: `let ... in`, `arr(i in lo..hi) e`, `sum(i in lo..hi) e`, and
plain indexing `a[i]` are all documented with a directly-applicable example
(`stencil.neo`'s `sum(i in 0..n) ys[i]` is essentially this task's return
expression with an extra multiply).

## README gaps / unclear points

- The README doesn't state outright that a loop variable `i` freshly bound
  by `arr(i in lo..hi)` or `sum(i in lo..hi)` is automatically known to
  satisfy `lo <= i < hi` for the purposes of discharging bounds obligations
  on arrays sized by the same expression as `hi`. It's implied by the
  `stencil.neo` example (`sum(i in 0..n) ys[i]` with `ys : Arr i64 n`) but
  never spelled out as a general rule; a one-line note next to the
  Fourier-Motzkin paragraph would remove the need to infer this from
  example pattern-matching.
- It's not obvious from the README alone whether `%` on `i64` follows
  Euclidean, truncated, or wrapping semantics for negative operands (the
  README only says "Integer arithmetic wraps"). It didn't matter for this
  task since all operands here are non-negative, but for a task involving
  negative moduli this would need to be discovered experimentally or from
  source, since it isn't documented.
- The "checked" vs "proven" vs "unproven" obligation statuses are
  explained implicitly through the `check` construct and the program
  boundary note ("main takes i64 arguments from argv; its refinements are
  checked at the program boundary"), but the JSON output's three-way status
  vocabulary itself (`checked` / `proven` / presumably `unproven`) is never
  listed exhaustively in one place -- I had to infer "checked" meant "proven
  by an inserted runtime check at the argv boundary" from context rather
  than from an explicit definition.

Overall, for a task this well-aligned with the documented examples, the
README plus the JSON diagnostics were sufficient with zero iteration.
