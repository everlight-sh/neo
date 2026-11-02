#!/usr/bin/env python3
"""Build Axon, Rust and Go versions of each benchmark, verify identical output,
time N runs of each (wall clock of the whole process), write RESULTS.md."""
import os, statistics, subprocess, sys, time, platform, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(ROOT, "bench")
RUNS = int(os.environ.get("RUNS", "7"))

BENCHES = {
    "mandel":  {"args": ["3000", "3000", "2000"], "desc": "Mandelbrot escape-time sum, 3000x3000 grid, 2000 max iterations (compute-bound, uneven rows)",
                "extra": {"Rust (rayon, max_len 4)": "rust/target/release/mandel_tuned"}},
    "stencil": {"args": ["50000000", "20"],       "desc": "3-point i64 stencil, n=50M, 20 passes, then checksum (memory-bound; every index carries a proof obligation)",
                "extra": {}},
    "stencil_small": {"bin": "stencil", "args": ["1000000", "2000"], "desc": "Same stencil, n=1M (8MB, cache-resident), 2000 passes: compute-bound, so bounds checks and per-pass dispatch overhead show",
                "extra": {}},
    "nbody": {"args": ["16384", "10"], "desc": "N-body, 16384 bodies, 10 leapfrog steps, softening 0.01, prints total energy. Axon: records laid out struct-of-arrays by the compiler and an order-free `sum`; Rust and Go: idiomatic array-of-structs",
              "extra": {}, "tolerance": 1e-9},
}

def sh(cmd, cwd=None, env=None):
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(f"FAILED: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}\n"); sys.exit(1)
    return r

def build():
    bins = {}
    progs = sorted({spec.get("bin", name) for name, spec in BENCHES.items()})
    for prog in progs:
        out = os.path.join(BENCH, f"axon_{prog}")
        sh(["python3", "-m", "neoc", "build", f"examples/{prog}.neo", "-o", out], cwd=ROOT)
    sh(["cargo", "build", "--release", "--quiet"], cwd=os.path.join(BENCH, "rust"))
    goenv = dict(os.environ, GOTOOLCHAIN="local", GOWORK="off")
    for prog in progs:
        sh(["go", "build", "-o", f"{prog}_bin", f"./{prog}"], cwd=os.path.join(BENCH, "go"), env=goenv)
    for name, spec in BENCHES.items():
        prog = spec.get("bin", name)
        bins[(name, "Axon")] = os.path.join(BENCH, f"axon_{prog}")
        bins[(name, "Rust")] = os.path.join(BENCH, "rust", "target", "release", prog)
        bins[(name, "Go")] = os.path.join(BENCH, "go", f"{prog}_bin")
        for label, rel in spec["extra"].items():
            bins[(name, label)] = os.path.join(BENCH, rel)
    return bins

def timeit(binpath, args, tolerance=None):
    import resource
    times, cpus, outs = [], [], set()
    for _ in range(RUNS):
        c0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        t0 = time.perf_counter()
        r = subprocess.run([binpath, *args], capture_output=True, text=True)
        times.append(time.perf_counter() - t0)
        c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpus.append((c1.ru_utime - c0.ru_utime) + (c1.ru_stime - c0.ru_stime))
        if r.returncode != 0: sys.stderr.write(r.stderr); sys.exit(1)
        outs.add(r.stdout.strip())
    if len(outs) != 1:
        if tolerance is None: raise AssertionError(f"nondeterministic output from {binpath}: {outs}")
        vals = sorted(float(o) for o in outs)
        assert vals[-1] - vals[0] <= tolerance * max(1.0, abs(vals[0])), f"outputs differ beyond tolerance: {outs}"
    return times, sorted(outs)[0], cpus

def main():
    bins = build()
    versions = {
        "clang": sh(["clang", "--version"]).stdout.splitlines()[0],
        "rustc": sh(["rustc", "--version"]).stdout.strip(),
        "go": sh(["go", "version"], env=dict(os.environ, GOTOOLCHAIN="local", GOWORK="off")).stdout.strip(),
        "cpu": sh(["sysctl", "-n", "machdep.cpu.brand_string"]).stdout.strip(),
        "cores": os.cpu_count(),
    }
    rows, results = [], {}
    for name, spec in BENCHES.items():
        outs = {}
        langs = ["Axon", "Rust", "Go", *spec["extra"]]
        for lang in langs:
            times, out, cpus = timeit(bins[(name, lang)], spec["args"], spec.get("tolerance"))
            outs[lang] = out
            util = statistics.median(c / t for c, t in zip(cpus, times))
            results[(name, lang)] = (min(times), statistics.median(times), util)
            print(f"{name:14s} {lang:24s} min {min(times):.3f}s  median {statistics.median(times):.3f}s  cpu/wall {util:.1f}  out={out}", flush=True)
        tol = spec.get("tolerance")
        if tol is not None:
            vals = {k: float(v) for k, v in outs.items()}
            ref = vals["Rust"]
            if any(abs(v - ref) > tol * max(1.0, abs(ref)) for v in vals.values()):
                print(f"!! output differs beyond tolerance for {name}: {outs}")
        elif len(set(outs.values())) != 1:
            print(f"!! output differs for {name}: {outs}")
        results[(name, "outs")] = outs
        results[(name, "langs")] = langs
    lines = ["# Results", "",
             f"Machine: {versions['cpu']}, {versions['cores']} cores. {versions['clang']}; {versions['rustc']}; {versions['go']}.",
             f"Wall-clock time of the whole process, best of {RUNS} runs (median in parentheses). 'vs Rust' is Rust's best time divided by that row's best time (above 1.00x = faster than Rust). CPU/wall is total CPU seconds over wall seconds, i.e. how many cores the process kept busy; the machine has 8 performance and 2 efficiency cores.", ""]
    for name, spec in BENCHES.items():
        lines += [f"## {name}", "", spec["desc"] + f". Args: `{' '.join(spec['args'])}`.", "",
                  "| Language | Best | Median | vs Rust | CPU/wall |", "|---|---|---|---|---|"]
        rb = results[(name, "Rust")][0]
        for lang in results[(name, "langs")]:
            b, m, util = results[(name, lang)]
            lines.append(f"| {lang} | {b:.3f}s | ({m:.3f}s) | {rb / b:.2f}x | {util:.1f} |")
        outs = results[(name, "outs")]
        lines += ["", "Outputs: " + ", ".join(f"{k} = {v}" for k, v in outs.items()), ""]
    open(os.path.join(ROOT, "RESULTS.md"), "w").write("\n".join(lines))
    print("\nwrote RESULTS.md")

if __name__ == "__main__":
    main()
