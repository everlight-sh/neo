# Usability and regression measurements

These measurements are recorded in the dated usability reports. Their drivers
were Python and were removed with the rest of the repository's Python. They
are still in the `v0.2.3` tag: `bench/usability/run.py`, `compute.py` and
`build_images.py`, and `bench/docker/build.py` and `compare.py`.

Run correctness first with `./neo test`. Build tools and benchmark competitors
are outside the Axon application images. The measurements were taken on native
ARM64 Linux, never under emulation, and never concurrently with tests,
compilation or other benchmarks.

The first driver checked equivalent JSON file processing and dynamic JSON parsing
against Rust/serde and Bun, then measured Axon collections, cold/warm builds,
durable notes CRUD and webhook delivery. Each measured process run retained output,
wall/CPU time and peak RSS. Application timings include storage/client overhead;
they do not estimate isolated server RSS or CPU. Files are fsynced by all JSON CLI
implementations. Five measured runs followed one warmup, with shuffled order.

The compute driver compared existing Axon/Rust/Go implementations with matching
inputs and worker budgets, verified checksums/energy, and retained all raw timings.
It used shorter representative sizes than the historical compute reports. Today
`./neo run --dev bench/run.neo -- compute` times the Neo side, and
`NEO_BENCH_COMPARE` adds comparison binaries.

The Docker HTTP driver additionally compared Axon SSR, Rust Hyper with
musl/glibc, Bun direct and Bun/React. It recorded throughput, latency, cgroup CPU,
working set, startup and image size; see `bench/docker/README.md`.

Raw results are retained under `bench/usability/results/` and `bench/http/results/`.
Only runs marked valid should be used. Timing changes between runs are expected
on a local VM; compare ranges and report losses as well as wins.

The image builder made scratch images for ARM64 and x86-64 and audited every
executable for undefined symbols, ELF interpreters and shared libraries. The
standalone application check ran the JSON CLI and both HTTP apps as UID 65532
with a read-only root, dropped capabilities, 256 MiB memory and a writable data
tmpfs. x86-64 execution on the ARM host was emulated and is correctness evidence
only. Build/compiler dependencies are never copied into these application images.
