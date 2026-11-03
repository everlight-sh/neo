# Job scripts and logs, in the order they ran

Each `NAME.sh` ran detached on the box as `sh NAME.sh > NAME.log`. `ab.py` interleaves variants
(order reversed every other round, one warm-up round) and prints medians and ranges of wall time.
Paths are on the benchmark box (`/root/...`).

| Job | What it measured |
|---|---|
| `build` | Built the Neo before binaries (`6e18e65`), Zig baseline and native, Rust, and the C prototypes. |
| `exp1` | C prototypes of the stencil and sieve phases (`prototypes/`) against Neo, Zig and Rust, THP madvise and never. |
| `exp2`, `exp3` | Sieve marking prototypes: prefetch distance, check-before-store, unrolling, huge-page advice, `perf stat`. |
| `exp4` | Stencil: `int` = interior specialization; `nt16` / `nt4` = plus non-temporal stores at 16 / 4 MiB (dropped). |
| `exp5` | `c0` = interior + scalar split + populate; `c16` = `c0` plus NT stores at 16 MiB; `np16` = `c16` without populate. |
| `exp6` | Sieve: `u` = strided unroll; `uc` = plus check-before-store at 64 bytes (both on top of `c16`). |
| `exp7` | Check-before-store threshold 8/16/32/64 bytes (`ucN`) on the sieve; `strided_flip` / `strided_random` downside. |
| `final` | Final candidate, all compute rows (`final-2c.json`), JSON rows, strided downside. Its sieve binary stored and loaded bools as bytes. |
| `exp9` | Sieve: byte loads/stores (`after`) vs `uc64` vs no populate; JSON doc ×1M with and without populate; JSON RSS and faults. |
| `final2` | Final code (bool loads back to `i1`): binary identity check against `final`, sieve rows (`final-2c-sieve.json`), sieve isolation (`final` / `bytes` / `uc64` / `u` / `c16` / `before`), strided downside. |
| `sieve3` | Sieve rows again with 15 rounds (`final-2c-sieve-b.json`). |
| `ci` | On a second 2c box (instance 65): `./neo test` (`ci-neo-test.log`) and the `.github/workflows/verify.yml` steps on `git archive` of the final commit. |
| `http-instr` | Same box: HTTP example before/after, user-space instructions per request and indicative req/s (server CPU 0, wrk on its SMT sibling). |

The experimental variants used temporary environment switches (`NEO_EXP_STREAM`, `NEO_EXP_CHECK`)
and a patched `vectorize.exp.py`; none of them remain in the compiler.
