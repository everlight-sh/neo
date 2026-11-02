# REPORT: hist.neo

## Result

- Compile attempts: 8 (16 `=== ` lines in `attempts.log` / 2).
- Final binary matched expected output: **yes**. `./hist 100000` prints
  `6259`, matching the spec exactly. Cross-checked against an independent
  Python re-implementation for n = 1, 16, 100000, 1000003 and all four
  outputs matched (`1`, `3`, `6259`, `62501`).
- One `check` node was needed (see below); everything else is statically
  proven, no other runtime checks beyond the mandatory argv-boundary check
  on `n >= 1`.

## Attempt-by-attempt log and which diagnostics led to a fix

1. **Syntax error, `Arr i64 16` as a return type**
   (`expected 'IDENT', got '16'`). The grammar for `Arr T <size>` apparently
   wants the size slot to be an identifier or a parenthesized expression, not
   a bare integer literal directly after the element type. Fix: wrote it as
   `Arr i64 (16)`. The diagnostic (a plain parser error with a position) was
   enough to spot the problem; nothing in the README explicitly says a bare
   literal size needs parens, I inferred it from the parse position pointing
   right at the `16`.

2. **Same syntax error again, this time on a helper function's parameter
   type** `max16 (h : Arr i64 16)`. Same fix (`Arr i64 (16)`), applied
   because the diagnostic pointed at the same column pattern.

3. **Type error: `array parameter sizes must be variables`.** This is the
   diagnostic that actually explained the rule the syntax error only hinted
   at: an array *parameter*'s size must be a fresh variable name (as in every
   example, `Arr T n`), not a constant, because the size is meant to be
   bound generically at the call site. Since I only needed the max-of-16
   computed once, right where the histogram is built, I dropped the separate
   `max16` function entirely and inlined the 16-way max chain directly into
   `main`, right after `let h = build_hist(n) in`, so `h`'s type stays the
   concrete `Arr i64 (16)` from `build_hist`'s return type instead of being
   re-abstracted over a generic size variable. All 16 literal-index bounds
   checks (`h[0]` through `h[15]`) then discharged trivially as `proven`
   (e.g. `0 <= 15 && 15 < len(h)` normalises to a constant `-15 <= 0 && 0 <=
   0`), since the size is a known constant in that scope.

4. **The real obligation: `set(h, b, h[b] + 1)` with
   `b = v * 16 / 1000003` unproven.** The JSON gave a `"bounds"` obligation
   `0 <= b && b < len(h)`, normalised to a single opaque atom
   `⟨((v * 16) / 1000003)⟩` with no known bounds at all, and a
   counterexample assigning that atom `-1`. This was the direct, actionable
   signal: the checker treats a non-linear compound expression (multiply
   then divide by two different constants applied to a variable that
   itself came from a `%`) as one opaque unbounded term -- it does not
   decompose it and does not know anything about the range of `%`'s result
   even though `i * 2654435761 >= 0` is linearly provable (product of a
   non-negative loop-invariant variable and a positive constant) and the
   modulus is a positive constant. The `"fixes"` field in the JSON
   explicitly suggested `check 0 <= b && b < len(h) in ...`, which is what I
   used, and it was accepted immediately (that specific obligation's status
   became `"checked"`, `ok: true`, `summary.unproven: 0`).

   I first tried a smaller, more "principled" intermediate step -- checking
   only `0 <= v && v < 1000003` right after computing `v = (...) % 1000003`,
   hoping the checker would then chain that fact through the subsequent
   `v * 16 / 1000003` automatically. It did not: the `b` obligation was
   still unproven with the same opaque-atom counterexample. Only checking
   the exact goal at the exact use site (`0 <= b && b < 16`, matching the
   obligation's own stated goal) worked. So the `check` node's proven fact
   does not get algebraically propagated through further arithmetic on the
   checked value in this compiler version -- you have to check the composite
   expression's bound directly at (or before) the point it's used as an
   index, not a component further upstream.

5. After that, `check` succeeded twice more (once with noisy output because
   I piped the wrapper's mixed stdout through a JSON parser and it choked on
   the `=== ` framing lines the wrapper itself prints -- my own tooling
   mistake, not a compiler issue -- so I reran the same command cleanly to
   file, which shows up as an extra logged attempt with identical content).

6. `build` succeeded on the first try after `check` passed:
   `obligations 39/41 proven, 2 runtime checks, 1 parallel regions, build
   miss`. The binary ran and printed the expected `6259` for n = 100000.

## Where I got stuck and why

The only real sticking point was step 4: proving the bucket index is in
`0..16`. I expected (per the task hint about "products and remainders")
that the checker might automatically know `0 <= (a % m) < m` for a
non-negative dividend and positive constant modulus, the way it
automatically knows `x * y >= 0` for non-negative `x, y`. It does not: the
only automatic fact attached to `/` and `%` is the divisor-nonzero side
condition (visible as separate `"kind": "division"` obligations that just
prove `1000003 != 0`), not any bound on the quotient or remainder. Once you
combine a `%` result with a further `*` and `/` by different constants
(exactly what "bucket = v * 16 / 1000003" requires), the whole expression
becomes a single opaque term to the linear (Fourier-Motzkin) solver, matching
the README's own statement that "non-linear index arithmetic ... needs a
check." My first attempt to work around this by checking an upstream fact
about `v` alone and letting it "flow through" the arithmetic did not work --
only checking the final composite bound at the actual index site did. This
cost two of the eight attempts (one to discover the opaque-atom bounds
obligation, one to discover that checking `v`'s range doesn't help and only
checking `b`'s range directly does).

## What was missing or unclear in the README

- The README's paragraph on what the checker knows "about opaque terms"
  lists `x * y >= 0` for non-negative factors and `sum ... >= 0`, but says
  nothing about `%` or `/`. It would have saved a wasted attempt to state
  explicitly (as the obligation JSON eventually made clear) that `%` and
  `/` carry *no* automatic bound facts beyond "divisor != 0" -- only the
  side-condition is proven automatically, never a bound on the result.
- The syntax for a *constant* array size (`Arr i64 16` as opposed to the
  variable-bound `Arr T n` shown throughout the README) is not documented
  at all. The README's grammar blurb only shows `Arr T n`, `Arr u8 (n + m)`,
  and `Arr u8 _`; it never shows a bare integer size, and it doesn't mention
  that a literal size needs parentheses in a return type, or that function
  *parameters* cannot have a literal/fixed size at all ("array parameter
  sizes must be variables" only appears as a diagnostic, not in the
  reference). I had to discover both facts by trial and error; once the
  diagnostics told me directly, correcting for them was immediate.
- The semantics of `check p in e` are not spelled out. It's listed as an
  expression form with no explanation of whether the asserted predicate `p`
  is (a) proven statically like every other obligation, (b) trusted
  outright, or (c) compiled into an actual runtime trap. It turns out to be
  (c): the JSON obligation for a `check` gets `"status": "checked"` (not
  `"proven"`) and increments `summary.runtime_checks`, i.e. it's an
  explicit, requested runtime assertion -- the one deliberate exception to
  "never a silent runtime check" mentioned in passing in the design
  overview but never connected back to the `check` syntax in the language
  reference section. It would help to say this plainly next to `check p in
  e` in the expression list, and to state whether a proven `check` fact
  is available to the solver for *later*, further-derived expressions (in
  my testing, it was not -- it only discharges obligations whose goal is
  exactly what was checked, not obligations built from further arithmetic
  on the checked value).
