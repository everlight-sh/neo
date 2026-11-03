# JSON decoding on one x86-64 box, 2026-11-03

Raw data for `RESULTS-json-x86-linux-2026-11-03.md`.

- `runs.json`: the measured run of `bench/json/x86.py` (2 warm-up and 21 measured rounds), every run's wall,
  user and system milliseconds. "Neo before" is commit `6e18e65`, "Neo after" is `32705eb`.
- `summary.md`: `python3 bench/json/summarize.py runs.json`.
- `reproduce.json`: the first run on the box (2 warm-up and 5 measured rounds), before any change. Both Neo
  entries in it were built from `6e18e65`, so "Neo before" and "Neo after" there are the same program.
- `counters.txt`: instructions and cycles of the four Neo programs, before and after.
- `meta.txt`: CPU, OS, toolchain versions and sha256 of the sources, binaries and harness files.
- `scripts/`: the box setup, the build of both trees and every competitor, and the measured run.
- `ci-steps.log`, `ci-neo-test.log`: every step of `.github/workflows/verify.yml` (`native-linux`) on the
  same box, from `git archive 32705eb`, and the full `./neo test` output.
