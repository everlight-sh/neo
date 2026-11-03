# Raw data for RESULTS-https-copies-linux-2026-11-03.md

"Before" is v0.1.3 (`bdabf90`). "After" is that commit plus this change. In each machine folder, `meta.txt` lists
the CPU, kernel, toolchains, and the SHA-256 of both source tarballs and both `fetch.neo` executables.
`fetch_main` is the executable `bench/fetch/run.py` built from main; `fetch_new` was built with
`./neo build bench/fetch/fetch.neo --no-cache`.

`scripts/setup.sh` installs the toolchains with `bench/core/results/2026-11-03-arm64-compute/scripts/setup.sh`,
then unpacks both trees. `scripts/all.sh` ran the first part of the round in order: `fetch.sh`, `ab.sh` (/1m, then
/64k), `prof.sh`, `oneshot.sh`, `meta.sh` and `ci.sh`. `keep-ab.sh`, `account.sh` and `tests.sh` ran afterwards
on the same boxes.

- `python3 scripts/medians.py ab-1m.log` prints each client's median p50 and range from `ab.sh`.
- `python3 scripts/keep-medians.py keep-ab.log` prints the medians from `keep-ab.sh`.

In `ab.sh` names, `s-` is HTTPS and `p-` plain HTTP. `main` and `new` are the two Neo clients. `new`, `keep` and
`res` are a new connection, kept-alive and resumed.

## x86-vultr/

Vultr `voc-c-2c-4gb-50s-amd`, AMD EPYC-Milan, 2 vCPUs.

## arm64-scaleway/

Scaleway `BASIC2-A2C-4G`, Neoverse-N1, 2 vCPUs.

## Files in each machine folder

| File | Contents |
|---|---|
| `ab-1m.log` | `scripts/ab.sh /1m 1048576 100`, 7 interleaved rounds, HTTPS and HTTP, every client |
| `ab-64k.log` | `scripts/ab.sh /64k 65536 400`, 5 interleaved rounds |
| `keep-ab.log` | `scripts/keep-ab.sh 15`: kept-alive HTTPS /1m under `perf stat`, main and new alternating |
| `keep-ab-noperf.log` | (AArch64 only) `PERF=0 scripts/keep-ab.sh 15`: the same without `perf stat` |
| `account.log` | `scripts/account.sh 12`: wall time against client and server CPU time, kept-alive HTTPS /1m |
| `prof.log` | `scripts/prof.sh`: `perf stat` and `perf record` of 200 kept-alive HTTPS /1m, main and new |
| `oneshot.log` | `scripts/oneshot.sh`: 400 interleaved one-request processes (GET /hello over HTTPS) |
| `fetch-main/`, `fetch-new/` | `bench/fetch/run.py` on main (3 rounds) and on this tree (5 rounds), separate runs (`scripts/fetch.sh`) |
| `fetch.log` | the output of `scripts/fetch.sh` |
| `tests.log` | `scripts/tests.sh`: the unit tests and language suites this change touches |
| `ci.log` | the `verify.yml` steps on this tree (`scripts/ci.sh`) |
| `meta.txt` | machine, toolchains, source and executable hashes (`scripts/meta.sh`) |
