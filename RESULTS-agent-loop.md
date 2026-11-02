# Agent-in-the-loop experiment

Question: can a coding agent write Axon from the README and the compiler's
JSON diagnostics alone? Four tasks were given to four independent subagents
(Claude Sonnet) with the README, the example programs, and a logged compiler
wrapper. They were forbidden to read the compiler source. Every compiler
invocation is in `experiments/agent-loop/<task>/attempts.log`; each agent
wrote its own `REPORT.md`.

| Task | What it needs | Compile attempts | Correct | Runtime checks in final program |
|---|---|---|---|---|
| dot: sum of a[i]*b[i] over two generated arrays | arrays, comprehensions, bounds from ranges | 1 | yes | 0 |
| runs: count runs of equal bytes | u8, loop invariant `i >= 1` for `v[i-1]` | 1 | yes | 0 |
| bsearch: binary search with proven indexing | loop invariants on `lo`/`hi`, a fact about `(hi - lo) / 2` | 5 | yes | 0 |
| hist: 16-bucket histogram with in-place `set` | `set`, bounds on `v * 16 / 1000003` | 8 | yes | 1 `check` |

(An "attempt" is one check or build call; attempts.log counts twice that.)

## What the agents said

- The two first-try tasks credited the examples: `stencil.ax` shows a proof
  from a range plus a negated branch, `sieve.ax` shows loop invariants and
  `set`. The dot agent asked for one sentence the README lacked: that the
  variable of `arr(i in lo..hi)` and `sum(i in lo..hi)` carries `lo <= i < hi`
  as a fact.
- The bsearch agent found from a counterexample that integer division was
  completely opaque to the prover, isolated it with a two-line probe
  function, and worked around it by clamping the midpoint through an
  `if`/`else`, which the diagnostics' own `fixes` field had suggested
  ("make the body's shape expose the fact").
- The hist agent hit the same wall on `v * 16 / 1000003`, tried a narrower
  `check` upstream that did not propagate, and ended with the exact `check`
  the compiler suggested. It also hit two syntax rules the README did not
  state: a constant array size is written `Arr i64 (16)`, and an array
  parameter's size must be a variable.

## What changed because of it

Both slow tasks failed on one missing capability, so it was added: the
checker now knows, for `a / b` and `a % b` with a positive constant `b`, that
`b*q <= a < b*q + b`, `q >= 0` when `a >= 0`, and `-b < r < b` (`r >= 0` when
`a >= 0`). With that, the histogram agent's program proves every obligation
with its `check` removed (39 of 40 obligations proven, the last being the
argv boundary), and the binary-search midpoint `lo + (hi - lo) / 2` proves
`lo <= mid <= hi` directly. The README now states the comprehension-variable
fact, the constant-size syntax, and the parameter-size rule.

## Reading it

The diagnostics did their job: in every case where an agent iterated, the
counterexample identified the opaque term and the suggested fix was the one
eventually taken. The cost of iteration was concentrated in one prover gap,
not spread across the language. Four tasks and one model are a small sample,
and the tasks were chosen to exercise proofs, not I/O or records; a second
round should include the HTTP handler shape and a record-based task.
