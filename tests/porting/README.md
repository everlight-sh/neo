# Porting the Python tests

The Python scripts in `tests/` are being replaced by native cases that
`neo test` runs. Each porting stream owns one manifest, registered in
`neo.toml`, and one failures file here:

| Stream | Manifest | Failures |
|---|---|---|
| Language, collections and JSON | `tests/language.neo.toml` | `language-failures.md` |
| Crypto, TLS, network and HTTP | `tests/network.neo.toml` | `network-failures.md` |
| Runtime, process and tooling | `tests/runtime.neo.toml` | `runtime-failures.md` |

Ported cases build with the native compiler under test, not the Python
reference compiler. A case the native compiler gets wrong is recorded in the
stream's failures file (the case, the command, what happened) and left out of
the manifest; compiler fixes come after the streams merge.
