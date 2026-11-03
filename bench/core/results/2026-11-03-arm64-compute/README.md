# Raw data for RESULTS-compute-arm64-linux-2026-11-03.md

`python3 scripts/summarize.py arm64-scaleway/final.json` prints every median and min–max range.

## arm64-scaleway/

Scaleway BASIC2-A4C-8G, Neoverse-N1, 4 vCPUs. Every `*.json` file comes from
`bench/core/compute_compare.py`. Each `*.log` is the console output of the matching job in
`scripts/arm64-jobs/`.

| File | Contents |
|---|---|
| `baseline-main.json` | main (6e18e65) against Rust, Go and Bun, 9 rounds |
| `dev1.json` | branch against main, Rust and Go, 7 rounds |
| `final.json` | the committed tree against main, Rust, Go and Bun, 9 rounds. This is the headline. `final.log` confirms the final executables are byte-identical to `dev1`'s. |
| `final-sha256.txt` | hashes of every executable measured in `final.json` |
| `lanes.json` | mandel lane-group sweep: `gN` = N groups of 2 lanes; `w8` = 8 lanes in one group |
| `chunks.json` | parallel chunks per thread: 8 (current), 16, 32 |
| `tune.json` | `-mtune=neoverse-n1`, `-mtune=neoverse-v1`, `-mcpu=neoverse-n1` |
| `fma-align.json` | `-ffp-contract=fast` (no effect on `.ll` input), `-falign-loops=32` and `=64` |
| `fma-contract.json` | IR `contract` flags on f64 add/sub/mul |
| `neo-test-dev.log` | `./neo test` on the branch, before the experiment hooks were removed (same IR) |

## Variant builds

The variant builds used environment hooks in an experiment copy of the compiler:

- `NEO_SUM_LANES`, `NEO_SUM_WIDTH` and `NEO_ARRAY_WIDTH` in `neoc/vectorize.py`
- `NEO_CLANG_FLAGS` in `neoc/cli.py`

The hooks were removed before commit; the committed compiler emits the same IR as the hooked one with
the variables unset. The scripts in `scripts/` and `scripts/arm64-jobs/` show the exact commands.

## x86-vultr/

Vultr `voc-c-2c-4gb-50s-amd`, EPYC-Milan, 2 vCPUs. `x86-compute.json` holds main, final and the
width variants against Rust and Go, 7 rounds (`scripts/build_x86.sh`, `scripts/x86_measure.sh`):

- `w2`: `NEO_SUM_WIDTH=2`
- `k4w2`: `NEO_SUM_LANES=4 NEO_SUM_WIDTH=2`
- `aw2`: `NEO_ARRAY_WIDTH=2`

`sha256.txt` shows which executables are identical. `machine.txt` is `lscpu` and the OS release.
