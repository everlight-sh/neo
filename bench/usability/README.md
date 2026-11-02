# Usability and regression measurements

Run correctness first with `./neo test`. Build tools and benchmark competitors
are outside the Axon application images. Benchmarks require native ARM64 Linux;
the drivers refuse an explicit emulation runner. Do not run timing measurements
concurrently with tests, compilation or other benchmark drivers.

From the repository in a Linux environment with Python 3.11+, Clang, binutils,
GNU time, taskset, Rust/Cargo, Go and Bun installed:

```sh
python3 bench/usability/run.py --repeats 5
python3 bench/usability/compute.py
```

The first driver checks equivalent JSON file processing and dynamic JSON parsing
against Rust/serde and Bun, then measures Axon collections, cold/warm builds,
durable notes CRUD and webhook delivery. Each measured process run retains output,
wall/CPU time and peak RSS. Application timings include storage/client overhead;
they do not estimate isolated server RSS or CPU. Files are fsynced by all JSON CLI
implementations. Five measured runs follow one warmup, with shuffled order.

The compute driver compares existing Axon/Rust/Go implementations with matching
inputs and worker budgets, verifies checksums/energy, and retains all raw timings.
It uses shorter representative sizes than the historical compute reports.

The existing Docker HTTP driver additionally compares Axon SSR, Rust Hyper with
musl/glibc, Bun direct and Bun/React. It records throughput, latency, cgroup CPU,
working set, startup and image size. Use the Docker socket from a dedicated Linux
load container on CPUs 4–7, with servers restricted to CPU 0 or CPUs 0–3:

```sh
python3 bench/docker/build.py
# In that load container, with BENCH_NETWORK naming its Docker bridge:
python3 bench/docker/compare.py --repeats 5 --duration 5s --warmup 3s \
  --report /axon/RESULTS-usability-http-linux-2026-10-24.md
```

Raw results are retained under `bench/usability/results/` and `bench/http/results/`.
Only runs marked valid should be used. Preserve reports alongside their raw run
directory before regenerating a report. Timing changes between runs are expected
on this local VM; compare ranges and report losses as well as wins.

`build_images.py` builds scratch images for ARM64 and x86-64 and audits every
executable for undefined symbols, ELF interpreters and shared libraries. Run
`tests/standalone_apps.py --arch arm64` (then `x86_64`) from a Linux tools container
with the Docker socket mounted. It exercises the JSON CLI and both HTTP apps as
UID 65532 with a read-only root, dropped capabilities, 256 MiB memory and a writable
data tmpfs. x86-64 execution on the ARM host is emulated and is correctness evidence
only. Build/compiler dependencies are never copied into these application images.
