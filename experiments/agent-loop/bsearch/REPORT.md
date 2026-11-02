# bsearch task report

**Compile attempts:** 5 (10 `=== ` lines in `attempts.log` / 2). 4 `check` calls, 1 `build` call. Everything after the first `check` compiled and proved clean; only one round of diagnostics (attempt 1) actually needed to be interpreted and fixed.

**Final binary matched expected outputs:** yes.

```
./bsearch 1000 2997  -> 999   (expected 999)
./bsearch 1000 2998  -> -1    (expected -1)
./bsearch 1000 0     -> 0     (expected 0)
```
Also spot-checked: n=1 edge cases, negative targets, and n=1000000 (largest index 999999) - all correct.

## What the diagnostics led to

The whole exercise came down to one nonobvious fact, discovered directly from
the JSON diagnostics rather than from the README: integer division is
completely opaque to the checker. My first draft computed the midpoint the
obvious way,

```
let mid = lo + (hi - lo) / 2 in ...
```

and every array access `a[mid]` came back `"status": "unproven"` with a
`normalised` goal built around a literal opaque atom
`<((hi - lo) / 2)>` and a counterexample where that atom is assigned an
arbitrary value unrelated to lo/hi (e.g. hi=0, lo=0, <(hi-lo)/2>=-1).
That counterexample was the "aha": the checker isn't failing to find a
clever bound, it genuinely carries zero facts about what a division
produces -- not even sign or magnitude relative to the operands. The only
obligation it does emit for division is the trivial divisor != 0 check
(and that one is auto-proven for a literal 2).

I isolated the problem with a two-line probe function,

```
fn midpoint (lo : i64{lo >= 0}, hi : i64{lo <= hi}) -> i64 {lo <= result, result <= hi}
  = lo + (hi - lo) / 2
```

which reproduced the same unproven postconditions with the same shape of
counterexample. The `fixes` field on that obligation was the second directly
useful diagnostic: it suggested "make the body's shape expose the fact
(loop invariant on the yielded state, if/else, let)". Combined with the
README's line that the checker knows facts from "both branches of an if",
that pointed at the fix: don't return the raw division result -- clamp it
through an if/else so the branches themselves, not the division, carry the
bound:

```
fn midpoint (lo : i64{lo >= 0}, hi : i64{lo <= hi}) -> i64 {lo <= result, result <= hi}
  = let m = lo + (hi - lo) / 2 in
    if m < lo then lo else if m > hi then hi else m
```

In the final else branch the checker has the negated conditions
m >= lo and m <= hi as hypotheses, so returning m there is trivially
in range -- the division's actual value is still unknown, but the clamp
makes the returned value's bounds provable regardless of what the division
produced. That one change took the probe from 2 unproven postconditions to
0, and the same pattern (call midpoint, rely on its return refinement)
then made every a[mid] bound in the real binary-search loop provable
immediately, with no further diagnostics needed. This is why attempts 2-4
in the log are all clean "ok": true -- attempt 2 validated the probe,
attempt 3 validated the full program, attempt 4 was the build's own
check pass.

The rest of the proof followed the patterns already shown in
examples/sieve.neo and examples/http.neo: a loop state with a typed
invariant (lo : i64{lo >= 0}, hi : i64{hi < n}), and the invariant
preserved by picking next expressions that keep lo/hi inside those
bounds on every branch. No `check` node was needed anywhere in the final
program -- the return-refinement of midpoint plus the loop invariants
were enough for the checker's Fourier-Motzkin pass to discharge every
a[mid] bound automatically.

One structural wrinkle worth noting for future tasks: `loop (s1 = i1, s2 =
i2, s3 = i3) ... next (e1, e2, e3) ...` requires each ei to be a
self-contained expression -- there is no way to compute a shared
subexpression (like mid) once and reuse it across the three next
components, short of restructuring the state into a record. I chose to just
repeat `let mid = midpoint(lo, hi) in ...` three times (once per state
component) rather than introduce a record type for the loop state; with
midpoint being cheap this is a non-issue, but it did make me consider a
`type St = { lo : i64, hi : i64, r : i64 }` design first before settling on
the simpler three-scalar version.

## Where I got stuck, and for how long

The only real stall was attempt 1: staring at the first JSON output and
figuring out why `0 <= mid && mid < len(a)` was unproven when it looked
"obviously" true from lo <= hi, lo >= 0, hi < n. It took reading the
normalised field closely (it renders the division as an opaque bracketed
term, not as an arithmetic expression the solver reasons about) and the
counterexample (which assigns that opaque term a value with no relation to
hi - lo) to realize the checker isn't a general nonlinear-arithmetic
solver -- division results are black boxes with no derived facts at all,
matching the README's line "Non-linear index arithmetic beyond that needs a
check." I initially assumed `check p in e` would let me assert
`0 <= mid && mid < n` as a trusted fact, but that would contradict "an
unproven obligation is a compile error, never a silent runtime check" --
check still has to be discharged by the same prover, so it wouldn't have
helped as a bare assertion around the division. Once I tested the if/else
clamp trick on the two-line probe function and saw it turn both
postconditions from unproven to proven, the rest assembled quickly with
zero unproven obligations from that point on.

## What was missing or unclear in the README

- The README says the checker knows "x * y >= 0 when both factors are
  non-negative" and "both branches of an if" as facts about opaque terms,
  but it never says (or hints) that division is totally opaque -- not even
  sign-preserving or magnitude-bounding facts are known about it. This is
  the single most important fact for writing any bisection/binary-search
  style code in Axon, and it's not stated anywhere; I only found it by
  reading a counterexample. A one-line note ("division results carry no
  facts at all; wrap them in a guard/clamp if you need a provable bound")
  would have saved the first failed attempt entirely.
- The "few facts about opaque terms" list doesn't actually say how to
  recover a fact when a term is opaque -- the if/branch clamp trick I used
  isn't documented as a pattern anywhere in the README or the five example
  programs (none of them clamp a value through if/else purely to expose a
  bound to the checker; stencil.neo's `if i == 0 || i + 1 == n` is a
  boundary guard, not a clamp-for-provability idiom). It was the "fixes"
  field in the JSON diagnostic, not the README, that pointed me at it. It
  would help to have one worked example of "opaque value + if/else clamp"
  in examples/ or the README, since this is presumably the general
  technique for any non-linear index arithmetic (not just division:
  multiplication by a non-constant, mod by a variable, etc. would likely
  hit the same wall).
- It's not documented whether `check p in e` requires p to be proven by
  the same prover (as I ended up assuming and confirmed I didn't need), or
  whether it's an unchecked trusted assertion. The one sentence describing
  it ("check p in e" in the expression list) gives no semantics at all --
  neither what happens if p is false, nor whether check can prove things
  the ambient context can't. I never actually needed check in the final
  program, but I spent time reasoning about whether it was a viable escape
  hatch before concluding (from "Proofs replace checks" and "never a silent
  runtime check") that it almost certainly isn't a bare assertion. A
  one-line clarification here would remove that uncertainty.
- Whether `let` bindings can carry their own refinement annotation (like
  loop state, e.g. `let mid : i64{lo <= mid, mid <= hi} = ... in ...`) is
  never stated one way or the other. I ended up not needing it (the helper
  function + return refinement approach worked, and is arguably cleaner
  anyway), but I would have tried it first if the README had said whether
  the syntax exists.
- Multi-variable `loop` state syntax is documented only by example, and it
  is not addressed whether a shared subexpression can be factored out
  across the next (...) argument list, or whether a record is the
  intended way to bundle related loop state. This is a minor style
  question rather than a blocker (I resolved it by repeating the shared
  subexpression), but a sentence on the intended idiom would help.
