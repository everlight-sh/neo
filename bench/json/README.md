# Dynamic JSON comparison

The comparison in the dated JSON reports reran the unchanged dynamic JSON
workflow from the usability report against its preserved old Axon executable,
Rust/serde_json and Bun. It fully checked outputs at 10,000, 100,000 and
1,000,000 documents, shuffled implementations every round, used two warmups
and nine measurements, pinned every process to one CPU and recorded wall/CPU
time and peak RSS. Its driver, `run.py`, was Python. It was removed with the
rest of the repository's Python and is still in the `v0.2.4` tag.

To time the Neo side of the workload:

```sh
./neo run --dev bench/run.neo -- compute 9 bench/json/neo.toml
```

Rust and Bun source implementations are unchanged. Raw artifacts are retained in
`bench/json/results/`; only runs marked valid are used in the report. Keep the VM
free of concurrent test/build jobs while measuring.

The workload includes dynamic source construction, complete strict parsing, field
access/decoding, array length and destruction. The representation is indexed source
slices in Axon, serde_json::Value in Rust and JavaScript values in Bun. This is a
complete-workflow comparison; it is not a universal claim about all JSON schemas,
parser libraries or native x86 performance.

`profile_allocations.py`, also in the `v0.2.4` tag, separately instrumented the
generated LLVM IR to count Axon allocator calls. Instrumented executables were not
used for timing comparisons.

Correctness: `./neo test` includes the Unicode/escaped-key/duplicate-key/nested/
wide-object accessor corpus, constructor/update rejection for sealed records,
borrowed-record lifetime and empty/static array mutation checks, and all prior
application/runtime regressions. Linux binaries must still pass `nm -u` and
`readelf` checks with no shared libraries or interpreter.
