# Language stream: native compiler gaps

Cases from the language scripts that the Python compiler handled and the
native compiler (`neoc` of `chore/remove-python`) does not. They are left out
of `tests/language.neo.toml`. Commands run from the repository root with
`NEO_ROOT` set to it, on x86_64 Linux.

## 1. Else-if chains are not lowered to a switch

- Scripts: `opcode_vm.py` (one `switch i64` with at least 39 cases in `step`),
  `deep_dispatch.py` (a 300-case switch in the build report),
  `test_switch_dispatch.py` (40-arm chains, match on fields and bytes, grouped
  arms, chains that switch on the first scalar only).
- Command: `neoc build tests/fixtures/opcode_vm.neo --emit-llvm`, then look at
  the function after `; fn __m…_step`.
- What happened: `step` has 39 `icmp eq` comparisons and no `switch`. The
  module's only `switch` is the width dispatch inside the runtime helper
  `@neo.bytes.read`. `deep_dispatch.neo` has 341 `icmp eq` and the same single
  runtime `switch`. `neoc build --report` has no `switches` field to check
  against.
- Ported anyway: both fixtures' results (the `opcode-vm` and `deep-dispatch`
  cases) and the 300-arm proof. Only the lowering check is missing.

## 3. Function-value types accept an unknown capability

- Script: `test_callbacks.py`, `test_effect_function_values`.
- Command: `neoc check` on
  `type Box={call:Effect<bogus>(i64)->unit} fn main()->i64=0`
- What happened: `(ok)`, exit 0. The Python checker rejected `bogus` as an
  unknown capability.

## 4. A function value erases a length coupling between parameters

- Script: `test_callbacks.py`, `test_function_values_reject_unsafe_contracts`.
- Command: `neoc check` on
  `fn f(n:i64,a:Arr u8 n)->i64=len(a) fn main()->i64=let g=function(f) in g(3,"a")`
- What happened: `(ok)`, exit 0, and the built program prints 1. `f`
  requires `len(a) == n`, but the value `g` accepts `g(3,"a")`. The checker does reject the related case where two
  array parameters share a length (`function values require independent
  lengths and no owned parameters or refinements`). A scalar length
  parameter is not caught. This is a soundness gap: code called through `g`
  can rely on a length that was never checked.

## 5. A postcondition is not proven after `check`

- Script: `test_ambient_paths.py` (all cases built on
  `F = fn f(x : i64) -> i64 {result > x, result < 5} = check x < 4 in x + 1`).
- Command: `neoc check` on
  `fn f(x : i64) -> i64 {result < 5} = check x < 4 in x + 1 fn main() -> i64 = 0`
- What happened: `(unproven <file> 1:30 postcondition)`, exit 1. The fact
  established by `check x < 4` is not available when the postcondition is
  proven. Writing `f` as `if x < 4 then x + 1 else check false in 0` also
  leaves the postcondition unproven. So:
  - the script's "still proven" cases (a fact dominated by the call, the same
    condition again, a short-circuit operand) cannot be built;
  - its "must not prove" cases are rejected, but at `f`'s postcondition, not
    at the out-of-bounds index they are about.
- Ported anyway, as the `ambient-paths-*` cases:
  - the original report (a precondition met on one branch only), rejected at
    the index;
  - the clamped-result postconditions;
  - comprehension lengths that are not path conditions.

