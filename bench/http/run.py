#!/usr/bin/env python3
"""Legacy C-runtime harness. Use compare.py for the current Axon runtime.

HTTP hello-world comparison: start each server, verify responses, load it
with wrk (keep-alive), record throughput, latency and server CPU per request."""
import http.client, json, os, re, socket, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT = 18080
DURATION = os.environ.get("DURATION", "5s")
REPEATS = int(os.environ.get("REPEATS", "3"))
WRK_THREADS = os.environ.get("WRK_THREADS", "4")
HERE = os.path.dirname(os.path.abspath(__file__))

MODE = os.environ.get("MODE", "hello")          # hello | compute | ssr
# name -> (wrk connections, pipeline depth or 0, server core limit or 0, path)
SCENARIOS_HELLO = {
    "64 connections":                    (64, 0, 0, "/"),
    "256 connections":                   (256, 0, 0, "/"),
    "64 connections, 16 pipelined":      (64, 16, 0, "/"),
    "64 connections, server on 2 cores": (64, 0, 2, "/"),
}
SCENARIOS_COMPUTE = {
    "/smooth/10000, 64 connections":     (64, 0, 0, "/smooth/10000"),
    "/smooth/1000, 64 connections":      (64, 0, 0, "/smooth/1000"),
    "/smooth/10000, 64 connections, server on 2 cores": (64, 0, 2, "/smooth/10000"),
    "POST /nbody n=256 steps=4, 64 connections": (64, 0, 0, "POST:/nbody"),
}
NBODY_REF = -0.8864476943101309       # energy for n=100, steps=10 (Python reference); compared with 1e-9 tolerance
SCENARIOS_SSR = {
    "GET /page/50, 64 connections":     (64, 0, 0, "/page/50"),
    "GET /page/50, 64 connections, server on 2 cores": (64, 0, 2, "/page/50"),
}
SCENARIOS = {"compute": SCENARIOS_COMPUTE, "ssr": SCENARIOS_SSR}.get(MODE, SCENARIOS_HELLO)
RESULTS_FILE = {"compute": "RESULTS-http-compute.md", "ssr": "RESULTS-http-ssr.md"}.get(MODE, "RESULTS-http.md")
SSR_REFERENCE = open(os.path.join(ROOT, "bench", "react", "reference_50.html"), "rb").read() if MODE == "ssr" else b""
REFERENCE = {   # computed independently in Python (32 passes)
    "/smooth/1000":  b'{"n":1000,"passes":32,"checksum":499795029}',
    "/smooth/10000": b'{"n":10000,"passes":32,"checksum":4999217629}',
}
# how each server is pinned to N cores (None = cannot be pinned, skipped in that scenario)
CORE_LIMIT_ENV = {
    "Axon (kqueue workers)": "NEO_THREADS", "Axon (thread per conn)": None,
    "Rust (std threads)": None, "Rust (hyper + tokio)": "TOKIO_WORKER_THREADS", "Go (net/http)": "GOMAXPROCS",
    "Bun (Bun.serve)": "",        # "" = include unchanged: the JS handler already runs on one thread
    "Axon (hand-rendered)": "NEO_THREADS", "Rust (hyper, hand-rendered)": "TOKIO_WORKER_THREADS",
    "Go (net/http, hand-rendered)": "GOMAXPROCS", "Bun (React renderToString)": "", "Node (React renderToString)": "",
    "Node cluster (React, 10 workers)": "NODE_CLUSTER",
}

SERVERS = {
    "Axon (kqueue workers)": [os.path.join(ROOT, "bench", "axon_http"), str(PORT)],
    "Axon (thread per conn)": [os.path.join(ROOT, "bench", "axon_http"), str(PORT)],
    "Rust (std threads)":   [os.path.join(ROOT, "bench", "rust", "target", "release", "http_std"), str(PORT)],
    "Rust (hyper + tokio)": [os.path.join(ROOT, "bench", "rust", "target", "release", "http_hyper"), str(PORT)],
    "Go (net/http)":        [os.path.join(ROOT, "bench", "go", "http_bin"), str(PORT)],
    "Bun (Bun.serve)":      ["bun", "run", os.path.join(ROOT, "bench", "bun", "server.ts"), str(PORT)],
}
if MODE == "ssr":
    SERVERS = {
        "Axon (hand-rendered)":        SERVERS["Axon (kqueue workers)"],
        "Rust (hyper, hand-rendered)": SERVERS["Rust (hyper + tokio)"],
        "Go (net/http, hand-rendered)": SERVERS["Go (net/http)"],
        "Bun (React renderToString)":  ["bun", "run", os.path.join(ROOT, "bench", "react", "server.tsx"), str(PORT)],
        "Node (React renderToString)": ["node", os.path.join(ROOT, "bench", "react", "server_node.js"), str(PORT)],
        "Node cluster (React, 10 workers)": ["node", os.path.join(ROOT, "bench", "react", "server_node.js"), str(PORT)],
    }

def wait_port(timeout=10.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.2).close(); return True
        except OSError:
            time.sleep(0.05)
    return False

def check_responses(name=""):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
    c.request("GET", "/"); r = c.getresponse(); body = r.read()
    assert r.status == 200 and body == b"Hello, World!", (r.status, body)
    c.request("GET", "/missing"); r = c.getresponse(); r.read()
    assert r.status == 404, r.status
    if MODE == "ssr":
        c.request("GET", "/page/50"); r = c.getresponse(); body = r.read()
        assert r.status == 200 and body == SSR_REFERENCE, (r.status, len(body), len(SSR_REFERENCE))
        assert r.getheader("Content-Type", "").startswith("text/html"), r.getheader("Content-Type")
        c.request("GET", "/page/0"); r = c.getresponse(); r.read(); assert r.status == 400, r.status
    if MODE == "compute":
        for path, want in REFERENCE.items():
            c.request("GET", path); r = c.getresponse(); body = r.read()
            assert r.status == 200 and body == want, (path, r.status, body)
            assert r.getheader("Content-Type", "").startswith("application/json"), r.getheader("Content-Type")
        c.request("GET", "/smooth/abc"); r = c.getresponse(); r.read()
        assert r.status == 400, r.status
        if any(path.startswith("POST:") for _, _, _, path in SCENARIOS.values()) and name != "Rust (std threads)":
            c.request("POST", "/nbody", body=b'{"n":100,"steps":10}', headers={"Content-Type": "application/json"})
            r = c.getresponse(); body = r.read()
            assert r.status == 200, (r.status, body)
            e = json.loads(body)["energy"]
            assert abs(e - NBODY_REF) < 1e-9, (body, NBODY_REF)
            c.request("POST", "/nbody", body=b'{"n":0}', headers={"Content-Type": "application/json"})
            r = c.getresponse(); r.read(); assert r.status == 400, r.status
    c.close()

def to_us(s: str) -> float:
    m = re.match(r"([\d.]+)(us|ms|s)", s)
    v, u = float(m.group(1)), m.group(2)
    return v * {"us": 1, "ms": 1e3, "s": 1e6}[u]

def wrk(conc: int, depth: int = 0, path: str = "/"):
    cmd = ["wrk", f"-t{WRK_THREADS}", f"-c{conc}", f"-d{DURATION}", "--latency"]
    if depth: cmd += ["-s", os.path.join(HERE, "pipeline.lua")]
    if path.startswith("POST:"):
        cmd += ["-s", os.path.join(HERE, "post_nbody.lua")]; path = path[5:]
    cmd.append(f"http://127.0.0.1:{PORT}{path}")
    if depth: cmd += ["--", str(depth)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    rps = float(re.search(r"Requests/sec:\s+([\d.]+)", out).group(1))
    reqs = int(re.search(r"(\d+) requests in", out).group(1))
    p50 = to_us(re.search(r"\s50%\s+(\S+)", out).group(1))
    p99 = to_us(re.search(r"\s99%\s+(\S+)", out).group(1))
    non2xx = re.search(r"Non-2xx or 3xx responses:\s+(\d+)", out)
    errs = re.search(r"Socket errors: connect (\d+), read (\d+), write (\d+), timeout (\d+)", out)
    return {"rps": rps, "requests": reqs, "p50_us": p50, "p99_us": p99,
            "non2xx": int(non2xx.group(1)) if non2xx else 0,
            "errors": sum(int(x) for x in errs.groups()) if errs else 0}

def cpu_seconds(pid: int) -> float:
    t = subprocess.run(["ps", "-p", str(pid), "-o", "time="], capture_output=True, text=True).stdout.strip()
    parts = t.split(":")                       # [[HH:]MM:]SS.ss
    return sum(float(p) * 60 ** i for i, p in enumerate(reversed(parts)))

def main():
    results = {}
    for scen, (conc, depth, cores, path) in SCENARIOS.items():
        print(f"--- {scen}")
        for name, cmd in SERVERS.items():
            env = dict(os.environ)
            if "thread per conn" in name: env["NEO_SERVE"] = "threads"
            if cores:
                var = CORE_LIMIT_ENV[name]
                if var is None: continue
                if var: env[var] = str(cores)
            if path.startswith("POST:") and name == "Rust (std threads)": continue   # the toy server has no POST route
            if name == "Node cluster (React, 10 workers)" and not cores: env["NODE_CLUSTER"] = "10"
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
            try:
                if not wait_port(): print(f"{name}: did not start"); continue
                check_responses(name)
                wrk(conc, depth, path)                                # warm-up
                cpu0 = cpu_seconds(proc.pid); total_reqs = 0
                runs = []
                for _ in range(REPEATS):
                    r = wrk(conc, depth, path); total_reqs += r["requests"]; runs.append(r)
                runs.sort(key=lambda r: r["rps"])
                med = runs[len(runs) // 2]
                med = dict(med, best_rps=runs[-1]["rps"], non2xx=sum(r["non2xx"] for r in runs), errors=sum(r["errors"] for r in runs))
                cpu = cpu_seconds(proc.pid) - cpu0
                med["cpu_us"] = 1e6 * cpu / max(total_reqs, 1)
                if name.startswith("Node cluster"): med["cpu_us"] = float("nan")   # workers are children; not measured
                results[(scen, name)] = med
                print(f"{name:22s} median {med['rps']:>8.0f} req/s (best {med['best_rps']:>8.0f})  p50 {med['p50_us']:>6.0f}us  "
                      f"p99 {med['p99_us']:>6.0f}us  cpu/req {med['cpu_us']:>5.1f}us  non2xx {med['non2xx']} errors {med['errors']}", flush=True)
            finally:
                proc.terminate()
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
            time.sleep(0.5)
    cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    wrkv = subprocess.run(["wrk", "--version"], capture_output=True, text=True); wrkv = (wrkv.stdout + wrkv.stderr).splitlines()[0]
    title = {"compute": "# HTTP results: compute endpoint", "ssr": "# HTTP results: server-side rendering"}.get(MODE, "# HTTP results")
    lines = [title, "",
             f"Machine: {cpu}, {os.cpu_count()} cores. Load generator: {wrkv}, {WRK_THREADS} threads, keep-alive, "
             f"running on the same machine as the server (they share the cores). Each cell is the median of {REPEATS} runs of {DURATION} "
             f"(best run in parentheses); latencies are from the median run.", "",
             ("Every server answers `GET /page/N` with the product-catalog page of bench/react/page.tsx (N rows, HTML-escaped notes, "
              "a computed total). Bun and Node render it with React 19's `renderToString`; Axon, Rust and Go hand-render the same HTML. "
              "Every server's `/page/50` was compared byte-for-byte with React's output before measuring. "
              if MODE == "ssr" else
              "Every server answers `GET /smooth/N` with 32 passes of a 3-point i64 stencil over an N-element synthetic signal and a JSON body "
              "`{\"n\":N,\"passes\":32,\"checksum\":C}`; bodies were checked byte-for-byte against a Python reference before each run. "
              if MODE == "compute" else
              "Every server answers `GET /` with `200 Hello, World!` and anything else with 404. ")
             + "Axon and Rust-std send three headers; hyper, Go and Bun also add `Date`. "
             "Axon's two rows are the same binary: `NEO_SERVE=threads` selects one blocking thread per connection; "
             "the default runs one kqueue event loop per core.", ""]
    notes = {"64 connections, 16 pipelined": "Each connection sends 16 requests per write (TechEmpower plaintext convention); "
                                             "measures the HTTP layer with the kernel mostly out of the way.",
             "GET /page/50, 64 connections, server on 2 cores": "Server limited to 2 workers (NEO_THREADS / TOKIO_WORKER_THREADS / GOMAXPROCS / NODE_CLUSTER); "
                                                  "Bun and single-process Node run unchanged (one thread already).",
             "/smooth/10000, 64 connections, server on 2 cores": "Server limited to 2 worker threads (NEO_THREADS / TOKIO_WORKER_THREADS / GOMAXPROCS); "
                                                  "thread-per-connection servers cannot be pinned and are omitted; Bun runs unchanged (single-threaded already).",
             "64 connections, server on 2 cores": "Server limited to 2 worker threads (NEO_THREADS / TOKIO_WORKER_THREADS / GOMAXPROCS) "
                                                  "so the server, not the load generator, is the bottleneck; thread-per-connection servers cannot be pinned and are omitted. "
                                                  "Bun runs unchanged because its handler is single-threaded already."}
    for scen in SCENARIOS:
        lines += [f"## {scen}", ""]
        if scen in notes: lines += [notes[scen], ""]
        lines += ["| Server | Requests/s | p50 | p99 | non-2xx | socket errors | server CPU per request |", "|---|---|---|---|---|---|---|"]
        for name in SERVERS:
            if (scen, name) not in results: continue
            r = results[(scen, name)]
            cpu = "n/a" if r['cpu_us'] != r['cpu_us'] else f"{r['cpu_us']:.1f} µs"
            lines.append(f"| {name} | {r['rps']:,.0f} ({r['best_rps']:,.0f}) | {r['p50_us']:.0f} µs | {r['p99_us']:.0f} µs | {r['non2xx']} | {r['errors']} | {cpu} |")
        lines.append("")
    open(os.path.join(ROOT, RESULTS_FILE), "w").write("\n".join(lines))
    print(f"\nwrote {RESULTS_FILE}")

if __name__ == "__main__":
    main()
