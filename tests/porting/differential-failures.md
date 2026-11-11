# Differential goldens: native compiler failures

Goldens under `compiler/tests/golden/` (frozen outputs of the Python reference
compiler, checked by `compiler/tests/golden.neo` through
`compiler/tests/differential.neo.toml`) that the native compiler gets wrong.
Each one keeps its reference golden, is listed in the `known-failures.txt`
beside it so the driver skips it, and has an entry here: the case, the
command, what differs and a short diff. Commands run from the repository root
with `NEO_ROOT` set to it, on x86_64 Linux.

None at present. On 2026-11-11 the native compiler of `chore/remove-python`
matched all 242 check goldens and 113 LLVM goldens, passed the live checks,
and the cancellation case printed 42.
