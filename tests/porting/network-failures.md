# Network stream: native compiler failures

Cases of the network stream (`tests/network.neo.toml`) that the native
compiler (`neoc` of `chore/remove-python`) gets wrong. Commands run from the
repository root with `NEO_ROOT` set to it, on x86_64 Linux.

No case is left out: every fixture and driver of the stream builds and passes
with the native compiler.
