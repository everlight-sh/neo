# Typed and dynamic JSON decoding on one x86-64 box: Neo, Rust serde, Bun, Zig, Go (2026-11-03)

This run measures Neo's JSON decoding before and after the changes in commits `5d329cc` and `32705eb`,
against Rust serde, Bun, Zig and Go. Every implementation takes part in the same interleaved rounds on one
machine.

**The typed decoder is now 1.78× faster than serde's typed structs on the small document and 1.31× faster
on the 1,000-order array.** Before the changes these ratios were 1.40× and 1.15×. **Dynamic JSON (`json_parse` and
accessors) is now 1.47× faster than Bun's `JSON.parse`**, up from 1.03×. The ranges are separate: Neo's
slowest run took 135.2 ms and Bun's fastest 181.8 ms.

In every case Neo was faster than every competitor in all 21 paired rounds, and every pair of ranges is
separate. The one row that did not move is the dynamic 1,000-order array (`orders_json`). It is 1.01× faster
(172.8 to 171.4 ms) and its ranges overlap with the old build's. Its time goes to parsing an array
of objects and materializing each element. That path was not changed here, because it scans with
`json_sequence_step` and `json_valid_take`.

## Results

Medians, with ranges in brackets, in milliseconds of complete-process wall time. "×" is the other
implementation's median divided by Neo's, so above 1.00× means Neo is faster. Every run's output was
checked against the case's checksum.

| Case | Neo before | **Neo after** | Rust serde typed | Rust `serde_json::Value` | Bun `JSON.parse` | Zig | Go `encoding/json` |
|---|---:|---:|---:|---:|---:|---:|---:|
| Small document ×1M, typed | 116.9 (116.5–121.3) | **92.1** (91.9–95.4) | 164.2 (162.7–187.0) · 1.78× | 323.5 (321.0–336.8) · 3.51× | — | typed + arena native 290.0 (287.4–294.1) · 3.15× | — |
| 1,000 orders ×1,000, typed | 80.9 (80.4–82.0) | **71.5** (71.2–72.0) | 93.3 (92.7–94.9) · 1.31× | — | — | typed + arena 196.0 (193.4–216.7) · 2.74× | — |
| Small document ×1M, dynamic | 181.0 (178.4–185.7) | **126.8** (124.7–135.2) | — | 308.2 (301.6–314.5) · 2.43× | 186.1 (181.8–193.3) · 1.47× | typed + arena native 292.2 (286.0–304.4) · 2.30×; `Value` 619.0 · 4.88× | 1,721.2 (1,676.3–1,794.8) · 13.57× |
| 1,000 orders ×1,000, dynamic | 172.8 (171.5–189.2) | **171.4** (168.9–183.4) | — | 346.4 (341.1–369.0) · 2.02× | — | `Value` + arena 407.6 (401.8–425.6) · 2.38×; `Value` 997.6 · 5.82× | — |

The table shows the faster Zig variant of each case. Every variant is in `summary.md`.

Against the targets:

| Target | Required | Result |
|---|---|---|
| Typed small document vs serde typed | ≥ 1.15× | 1.78×, ranges separate |
| Typed 1,000 orders vs serde typed | ≥ 1.15× | 1.31×, ranges separate |
| Dynamic small document vs Bun `JSON.parse` | ≥ 1.30×, ranges separate | 1.47×; Neo 124.7–135.2 ms, Bun 181.8–193.3 ms |
| Rust `Value`, Zig and Go comparisons | no regression | every ratio improved in the same run: on the dynamic document 1.70× → 2.43× against Rust `Value`, 9.51× → 13.57× against Go and 1.61× → 2.30× against the fastest Zig; the smallest change is the dynamic orders row, 2.00× → 2.02× against Rust `Value` |

Quartiles (25th / 50th / 75th percentile, ms):

| Case | Neo before | Neo after | Closest competitor |
|---|---|---|---|
| Typed small document | 116.7 / 116.9 / 117.1 | 92.0 / 92.1 / 93.0 | serde typed 162.9 / 164.2 / 166.2 |
| Typed 1,000 orders | 80.7 / 80.9 / 81.2 | 71.4 / 71.5 / 71.6 | serde typed 93.0 / 93.3 / 93.5 |
| Dynamic small document | 179.0 / 181.0 / 182.6 | 125.3 / 126.8 / 128.1 | Bun 183.4 / 186.1 / 187.8 |
| Dynamic 1,000 orders | 171.9 / 172.8 / 175.8 | 170.2 / 171.4 / 173.6 | Rust `Value` 343.5 / 346.4 / 353.4 |

The new build was faster than the old one in all 21 rounds of the first three cases and in 18 of 21 rounds of the
fourth.

Instructions and cycles, from `perf stat` in one run of each program (`counters.txt`):

| Program | Instructions before → after | Cycles before → after |
|---|---:|---:|
| `document_decoder` (typed small document) | 2,700M → 2,077M (−23%) | 480M → 379M |
| `orders_decoder` (typed orders) | 1,923M → 1,482M (−23%) | 332M → 288M |
| `library_bench 0` (dynamic small document) | 4,013M → 2,847M (−29%) | 740M → 516M |
| `orders_json` (dynamic orders) | 3,987M → 3,948M (−1%) | 699–727M → 693–696M (five runs each) |

The first cycle reading for the new `orders_json` was 770M. Five more alternating runs measured
693–696M for the new build and 699–727M for the old one, so that first reading was noise.

## What changed

All the changes are in `stdlib/json.neo`. There are no compiler or prover changes. The new scanners are
written so that the checker proves their indexes and arithmetic. Each word load is guarded by a bounds
test such as `start>=0 && start<=n-8`, and each loop's condition bounds its index. The overflow checks that remain in
the hot paths are a few additions on positions.

- **Keys.** A key's first eight bytes are loaded as one word. The existing escape mask then finds the first
  quote, backslash, control byte or non-ASCII byte. Keys of up to seven bytes end in that word.
- **Integers.** One word gives the number of leading digits through a non-digit mask and `tzcnt`.
  - The object index only needs the end of the number. Before, it shared the field decoder's value path. That path
    accumulated the value with checked multiplications, and LLVM cannot remove those because a trap is a side effect.
  - The typed decoder reads an integer below 10^7 entirely from that word, including the byte after the
    digits. It converts the digits with parallel pairs and groups (`json_digits_value`), which has no runtime checks.
- **UTF-8 in strings.** `json_utf8_word` checks a two- to four-byte sequence with one four-byte load and one
  mask for the lead and continuation bits. It then rules out overlong forms, surrogates and code points above U+10FFFF.
  `json_string_scan` alternates the plain word scan with runs of such sequences. An escape, a control byte, or an
  ill-formed or truncated sequence still goes to the byte-by-byte validator. The postcondition `result<=4` is
  proven, so the position update in the run is proven too.
- **Lookups.** `json_get` and the other accessors used to scan every wider key for escapes. Now a wider key whose
  first byte is neither a backslash nor the name's first byte is rejected at once.
- **Array counts.** A member array with no string or nested container counts its commas
  (`json_valid_count`). Refinements on the loop state (`i>=1`, `-1<=commas<i`) prove its increments.
- **Field names.** Each decoder name that a plain key can spell is stored as a zero-padded word, and every
  other name as -1, which no key word equals. A short key is matched with one comparison per name. Before,
  the same loop also tested each name's length and carried the byte comparison for long names.
- **Span writes.** The four writes per member are now spelled out in the walk's loop instead of in a helper
  call. The existing set-only analysis then proves the buffer unique, so each write no longer checks the reference count.

One finding along the way: a word scan can lose to a byte loop on very short tokens. In a first version, the
integer path scanned digits a word at a time and then converted them. It cut 5% of the typed orders'
instructions but no cycles, because IPC fell from 5.87 to 5.44. The orders' integers have one or two digits.
Before, a predicted byte compare found their end. Now the end depends on a chain of a load, a mask and `tzcnt`. The final version
decides such integers from the word it has already loaded.

## Correctness

- Every measured run's output was checked against the independent checksum: 513500000 for the documents and
  34327000 for the orders.
- The new test `tests/json_scan_utf8.py` covers UTF-8 sequences and integers at every word and end-of-source offset:
  - The sequences include valid ones of every width and boundary, and overlong, surrogate, out-of-range, stray,
    truncated and broken sequences. The integers are 1 to 20 digits, signed, with leading zeros, fractions and exponents.
  - They appear in keys, values and arrays, with 0 to 12 bytes before them and 0 to 9 after.
  - `json_parse` is checked against Python's strict decoder on 10,800 documents. The prepared field decoder is checked
    against `json_parse`/`json_get` on 9,733 decodes.
  - Two deliberately injected bugs both made it fail: accepting the overlong lead byte C0, and accepting `1E5` as an integer.
- The existing JSON tests pass on the final tree and on the intermediate commit `5d329cc`. These are `json_accessors`,
  `json_field_decoder`, `json_key_words`, `json_object_encoder`, `json_scan_words`, `json_serialization`,
  `json_token_growth`, `json_tokens`, `json_views`, `json_writer` and `json_writer_growth`. `usability_smoke` passes too.
- The full CI suite ran on the same box: `./neo test` plus every other step of `.github/workflows/verify.yml`.
  See the CI section below.

## Method

`bench/json/x86.py` drives the run. The per-run numbers are in `runs.json`.

- **Timing:** complete-process wall time from fork to exit, including launch, the work, output and exit. This
  is the headline report's method. User and system CPU come from `wait4`.
- **Placement:** every process runs under `taskset -c 1` with `NEO_THREADS`, `GOMAXPROCS`, `RAYON_NUM_THREADS`
  and `ZIG_THREADS` set to 1. The box's two vCPUs are SMT siblings of one core. CPU 0 serves the system
  and the Python driver, which only waits while a process runs.
- **Rounds:** 2 warm-up rounds, then 21 measured rounds. Each round runs every variant of a case once, in an order
  shuffled with seed 20261103.
- **Workloads:** the existing programs, unchanged.
  - Typed small document: `bench/core/document_decoder.neo` against `bench/rust` `typed_json doc-typed` and
    `doc-value`, and `bench/zig/json.zig` `doc-typed-arena`.
  - Typed orders: `bench/core/orders_decoder.neo 1000 1000` against `typed_json orders-typed` and Zig
    `orders-typed-arena`.
  - Dynamic small document: `examples/library_bench.neo 0` against Bun `bench/usability/bun.ts parse`, Rust
    `usability parse`, Go `bench/core/json.go`, and Zig `doc-value` and `doc-typed-arena`.
  - Dynamic orders: `bench/core/orders_json.neo 1000 1000` against `typed_json orders-value` and Zig
    `orders-value` and `orders-value-arena`.
  - Every document workload builds a fresh document each iteration. The order workloads build the array once and decode it 1,000 times.
- **Reproduction:** a first run of 5 measured rounds on the same box, before any change (`reproduce.json`), gave the
  same ordering as the earlier reports. Neo was 1.40× ahead of serde typed on the document, 1.15× on the orders, and
  1.03× ahead of Bun.

## Machine and toolchains

The run used one temporary Vultr `voc-c-2c-4gb-50s-amd`, instance 51, in Amsterdam. It was created for this
work and destroyed afterwards; see the box section below.

| | |
|---|---|
| CPU | AMD EPYC-Genoa, 2 vCPUs = 1 core × 2 SMT threads. L2 is 1 MiB, L3 is 32 MiB. |
| OS | Ubuntu 24.04.5 LTS, Linux 6.8.0-146-generic. THP is `madvise`. |
| Neo before | Commit `6e18e65`, packed with `git archive` (`base.tgz`, sha256 `917fdd31…`). |
| Neo after | The working tree packed just before the commits (`head.tgz`, sha256 `cc018390…`). Its `stdlib/json.neo` is byte-identical to commit `32705eb` (sha256 `cd94b9ef…`), and the compiler is unchanged. Both trees were built with `./neo build … --no-cache` and clang 18.1.3. |
| Rust | rustc 1.99.1 (`58cf8f9c3`) and cargo 1.99.1, `cargo build --release --locked`, with `[profile.release]` opt-level 3, codegen-units 1, lto "fat". |
| Go | go1.25.14, `GOWORK=off GOTOOLCHAIN=local CGO_ENABLED=0 go build`. |
| Bun | 1.4.4 (`38afee6c8`). |
| Zig | 0.17.0, `zig build -Doptimize=ReleaseFast`, once with `-Dcpu=baseline` and once native. |
| Driver | Python 3.12.3. |

The competitor sources are unchanged from `6e18e65`. `meta.txt` has the sha256 of every binary and harness
file.

## CI

Every step of the `native-linux` job in `.github/workflows/verify.yml` was run on the same box after the
benchmark, from `git archive 32705eb`. The box had the workflow's apt packages, the pinned Bun 1.3.13 and
`bun install --frozen-lockfile` in `examples/jsx-ssr`. All steps passed:

| Step | Result |
|---|---|
| `./neo test` | exit 0 in 802 s; 132 PASS lines, `neo test: 37 native cases, 0 failed`, Bun tests 31 pass, 0 fail |
| Empty-root runtime audit (`examples/http.neo`, `tests/freestanding_linux_smoke.py`) | exit 0, `ALL OK` |
| Reproducible compiler bundle (two `./neo release`, `cmp`) | exit 0; both archives sha256 `abe7fb1c…`, 101 files |
| Empty-root language, crypto and TLS (`tests/language_freestanding.py`) | exit 0 |

The full logs are `ci-steps.log` and `ci-neo-test.log` in the results folder. The workflow also runs on
`ubuntu-24.04-arm`; that leg was not run for this work. The JSON change is target-independent Neo source,
and no compiler code changed.

## Box

One box was used: the Vultr `voc-c-2c-4gb-50s-amd` in Amsterdam that ran the benchmark and CI. It was
destroyed at 2026-11-03 00:28 UTC, once the raw data and logs were copied off it. The provider's read-only
instance list afterwards no longer contained it. The other instances in that list belong to unrelated work.

## Reproduce

On a fresh Ubuntu 24.04 x86-64 box, with `base.tgz` (`git archive 6e18e65`) and `head.tgz` (this tree) in
`/root`:

```
sh bench/json/results/2026-11-03-vultr/scripts/setup.sh
sh bench/json/results/2026-11-03-vultr/scripts/build.sh
sh bench/json/results/2026-11-03-vultr/scripts/run.sh
python3 bench/json/summarize.py /root/final/runs.json
```
