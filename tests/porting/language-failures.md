# Language stream: native compiler gaps

Cases from the language scripts that the Python compiler handled and the
native compiler (`neoc` of `chore/remove-python`) does not. They are left out
of `tests/language.neo.toml`. Commands run from the repository root with
`NEO_ROOT` set to it, on x86_64 Linux.

None at present: the six gaps first recorded here (switch lowering, push
growth of nested and record arrays, an unknown function-value capability, a
length coupling erased by a function value, check facts for postconditions,
JSON writer growth) were fixed on 2026-11-11 by the fix/gaps-checker and
fix/gaps-codegen merges, and their cases are back in the manifest.
