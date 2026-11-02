# Dynamic JSON comparison

`run.py` reruns the unchanged dynamic JSON workflow from the usability report,
against its preserved old Axon executable, Rust/serde_json and Bun. It fully checks
outputs at 10,000, 100,000 and 1,000,000 documents, shuffles implementations every
round, uses two warmups and nine measurements, pins every process to one CPU and
records wall/CPU time and peak RSS. Run on native ARM64 Linux with the benchmark
toolchain installed:

```sh
python3 bench/json/run.py --repeats 9 --baseline /axon/.kernel-build/json-opt/baseline/library
```

The baseline path and its `library_bench.neo` source are preserved before edits.
The driver asserts that today's workload source is byte-for-byte identical. Rust
and Bun source implementations are unchanged. Raw artifacts are retained in
`bench/json/results/`; only runs marked valid are used in the report. Keep the VM
free of concurrent test/build jobs while measuring.

The workload includes dynamic source construction, complete strict parsing, field
access/decoding, array length and destruction. The representation is indexed source
slices in Axon, serde_json::Value in Rust and JavaScript values in Bun. This is a
complete-workflow comparison; it is not a universal claim about all JSON schemas,
parser libraries or native x86 performance.

`profile_allocations.py` separately instruments generated LLVM IR to count Axon
allocator calls. It links with the same standalone flags and checks the checksum.
Instrumented executables are not used for timing comparisons.

Correctness: `./neo test` includes the Unicode/escaped-key/duplicate-key/nested/
wide-object accessor corpus, constructor/update rejection for sealed records,
borrowed-record lifetime and empty/static array mutation checks, parser fuzzing,
and all prior application/runtime regressions. Extended malformed-input runs also
exercise optimization switches disabled. Linux binaries must still pass `nm -u`
and `readelf` checks with no shared libraries or interpreter.
