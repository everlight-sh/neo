# Raw data for RESULTS-thin-rows-linux-2026-11-03.md

"Before" is v0.1.2 (`5a5d3f2`); "after" is that commit plus this change. `meta.txt` in each machine folder
lists the CPU, kernel, THP settings, toolchains, and the SHA-256 of every source tarball and executable.
`patch4.tgz` is the committed change; the earlier patches are intermediate overlays. The compute executables
are byte-identical between the `collapse-ab*` and `final*` runs.

`python3 scripts/table.py FILE [THP]` prints the before/after/best-other table for any compute JSON;
`scripts/rng.py` (compute-margins JSON) and `scripts/ranges.py` (compute_compare JSON) print every median with
its min–max range.

## x86-vultr/

Vultr `voc-c-4c-8gb-75s-amd`, AMD EPYC-Rome, 4 vCPUs.

| File | Contents |
|---|---|
| `final.json` | `bench/compute-margins/run.py`, 7 rounds, 1 and 4 workers, THP madvise and never: after, before, Zig, Zig native, Rust (`scripts/final-x86.sh`) |
| `collapse-ab.json` | the same harness, 9 rounds, 1, 2 and 4 workers, on the huge-page change alone |
| `https-ab.log` | `scripts/ab-https.sh` (5 interleaved rounds of GET /1m), then `scripts/oneshot-ab.sh` and `scripts/prof-ab.sh` |
| `fetch-final/`, `fetch-main/` | `bench/fetch/run.py --schemes https` on the final tree (5 rounds) and on main (3 rounds), separate runs |
| `ci.log` | the `verify.yml` steps on the final tree (`scripts/ci.sh`) |

## arm64-scaleway/

Scaleway `BASIC2-A4C-8G`, Neoverse-N1, 4 vCPUs.

| File | Contents |
|---|---|
| `final-madvise.json`, `final-never.json` | `bench/core/compute_compare.py`, 7 rounds, 1 and 4 workers: after, before, Rust, Go (`scripts/final-arm.sh`) |
| `collapse-ab-madvise.json`, `collapse-ab-never.json` | the same, on the huge-page change alone |
| `https-ab.log` | `scripts/ab-https.sh`, 5 interleaved rounds of GET /1m |
| `hello-ab.log` | `scripts/hello-ab.sh`, 5 interleaved rounds of GET /hello (new, resumed, kept-alive) |
| `oneshot-ab.log` | `scripts/oneshot-ab.sh`, 400 interleaved one-request processes of each client |
| `fetch-final/`, `fetch-main/` | `bench/fetch/run.py --schemes https` on the final tree (5 rounds) and on main (3 rounds), separate runs |
| `cbs.log` | the check-before-store sieve experiment (`scripts/arm-cbs.sh`), not in the change |
| `ci.log` | the `verify.yml` steps on the final tree (`scripts/ci.sh`) |

As run, `final-arm.sh` printed ranges with `rng.py`, which reads the compute-margins format and failed on
these files after they were written. The copy here calls `ranges.py`.
