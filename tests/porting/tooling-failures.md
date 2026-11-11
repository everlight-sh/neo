# Tooling goldens: native compiler failures

Cases of `compiler/tests/tooling.neo.toml` (the native drivers that replace
`compiler/tests/*_differential.py`, `ast_dump.py`, `modules_dump.py`,
`differential.py` and `modules_differential.py`) where the native compiler
differs from the frozen output of the Python reference. Each one keeps its
reference golden, is listed in the `skip.txt` beside it so the driver does not
compare it, and has an entry here: the case, the command, what differs and a
short diff. Commands run with `NEO_ROOT` set to the repository root, on
x86_64 Linux.

None at present. On 2026-11-11 the native compiler of `chore/remove-python`
(e6881b1, Neo 0.2.3) matched every golden the reference produced: the 19
formatter samples, the init tree, 521 parse dumps, 76 module graphs, 12
package-import graphs, 24 package-command steps with 2 vendor trees, and the
release, LSP, graph and HTTP outputs. All skip lists are empty.

Not differences, recorded for reviewers:

- `project_differential.py` fails against the reference on this branch
  because the native wording of a skipped integration hook changed on purpose
  ("skipped integration hook must-not-run.py; only .toml manifests of native
  cases run"). `compiler/tests/project.neo` checks the new wording.
- `tests/fixtures/deep_dispatch.neo` is not among the parse goldens: the Python
  parser overflows its recursion limit on it. `corpus.neo parse` still parses
  it natively (with the 64 MiB stack `neo` sets).
- 44 repository files do not parse standalone with `neoc parse` (natively or
  in the reference) because they use record types from their imports;
  `corpus.neo parse` loads them with `neoc modules` instead. Two fixtures,
  `tests/fixtures/test_borrow_parameters/move_and_borrow.neo` and
  `tests/fixtures/test_inline_budget/cold_inline.neo`, are meant to fail and
  must keep failing with their diagnostics.
- The repository is not fmt-clean: `neoc fmt --check` would change 479 of the
  495 `.neo` files (2026-11-11). `corpus.neo fmt` only checks that formatting
  a copy of each file is idempotent.
