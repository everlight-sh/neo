# Runtime stream: native compiler failures

Cases of the runtime stream (`tests/runtime.neo.toml`) that the native
compiler (`neoc` of `chore/remove-python`) gets wrong. Each one is left out of
the manifest (or out of its driver) until the compiler is fixed. Commands run
from the repository root with `NEO_ROOT` set to it, on x86_64 Linux.

None at present: the gaps first recorded here (the SSR escape bounds, an
unused explicit export dropped at link, no parallel dispatch) were fixed on
2026-11-11 by the fix/gaps-checker, fix/gaps-codegen and fix/gaps-parallel
merges, and their cases and checks are back.
