# Porting the Python tests

The Python scripts in `tests/` and `compiler/tests/` were replaced by native
cases that `neo test` runs. The port is complete: every script was ported or
dropped, and the scripts are in the `v0.2.4` tag. Each porting stream owns
one manifest, registered in `neo.toml`, and one failures file here:

| Stream | Manifest | Failures |
|---|---|---|
| Language, collections and JSON | `tests/language.neo.toml` | `language-failures.md` |
| Crypto, TLS, network and HTTP | `tests/network.neo.toml` | `network-failures.md` |
| Runtime, process and tooling | `tests/runtime.neo.toml` | `runtime-failures.md` |
| Compiler differential goldens (check, LLVM, cancellation) | `compiler/tests/differential.neo.toml` | `differential-failures.md` |
| Compiler tooling (fmt, init, project, packages, build options, parse and module dumps, corpus) | `compiler/tests/tooling.neo.toml` | `tooling-failures.md` |

Ported cases build with the native compiler under test. Expected outputs that
came from the Python reference compiler or from Python oracles are frozen in
`tests/vectors/` and `compiler/tests/golden/`. Each manifest's comments name
the script a case replaces.

`tests/native_library_cache.py` and `tests/test_inline_cost.py` were dropped:
they tested machinery only the Python compiler had.

Every native compiler gap the port recorded was fixed on 2026-11-11, and its
cases are back in the manifests. The failures files stay for future gaps: a
case the native compiler gets wrong is recorded in its stream's file (the
case, the command, what happened) and left out of the manifest until the
compiler is fixed.
