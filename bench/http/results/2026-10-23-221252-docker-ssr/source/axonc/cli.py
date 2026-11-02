"""axonc: build | check | graph

Diagnostics are JSON: an agent reads them, discharges or checks each
obligation, and resubmits. Builds are cached by program hash.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
import platform as host_platform
from . import syntax as S
from .graph import hash_program, program_hash
from .check import Checker, CheckError

HERE = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.path.join(os.path.dirname(HERE), "runtime")

def target_triple() -> str:
    """The triple clang itself would stamp on a module for this host."""
    return subprocess.check_output(["clang", "-print-target-triple"], text=True).strip()

def load(path: str):
    if sys.platform not in ("darwin", "linux"):
        raise SystemExit("Axon currently supports macOS and Linux")
    if sys.maxsize <= 2**32 or sys.byteorder != "little":
        raise SystemExit("Axon's platform bindings currently require a 64-bit little-endian host")
    if host_platform.machine() not in ("arm64", "aarch64"):
        raise SystemExit("The freestanding syscall runtime currently supports ARM64 macOS and Linux")
    platform = "macos" if sys.platform == "darwin" else "linux"
    names = ["core.ax", f"platform_{platform}.ax", "http.ax"]
    if platform == "linux": names.append("http_linux.ax")
    sources = [os.path.join(RUNTIME, name) for name in names] + [path]
    prog = S.Program([], [])
    for source in sources:
        try:
            part = S.parse(open(source).read())
        except S.SyntaxError_ as ex:
            emit_json({"ok": False, "errors": [{"kind": "syntax", "file": source, "pos": list(ex.pos), "msg": ex.msg}]})
            sys.exit(1)
        for f in part.fns: f.source = source
        prog.types.extend(part.types); prog.fns.extend(part.fns)
    fn_hashes = hash_program(prog)
    return prog, fn_hashes

def emit_json(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))

def check(prog, fn_hashes):
    ck = Checker(prog)
    try:
        ck.run()
    except CheckError as ex:
        return ck, {"ok": False, "errors": ex.errors, "obligations": ck.obligations}
    unproven = [o for o in ck.obligations if o["status"] in ("unproven", "unknown")]
    return ck, {"ok": not unproven, "program": program_hash(fn_hashes),
                "functions": {n: h for n, h in fn_hashes.items()},
                "obligations": ck.obligations,
                "summary": {"obligations": len(ck.obligations),
                            "proven": sum(o["status"] == "proven" for o in ck.obligations),
                            "runtime_checks": ck.runtime_checks,
                            "unproven": len(unproven)}}

def cmd_check(args):
    fns, fn_hashes = load(args.file)
    _, report = check(fns, fn_hashes)
    emit_json(report)
    sys.exit(0 if report["ok"] else 1)

def cmd_graph(args):
    fns, fn_hashes = load(args.file)
    nodes = hash_program.last_nodes
    emit_json({"program": program_hash(fn_hashes), "functions": fn_hashes, "nodes": len(nodes),
               "graph": nodes if args.full else {h: n["op"] for h, n in nodes.items()}})

def build(args, want_binary=True):
    from .llvm import LLVMGen
    fns, fn_hashes = load(args.file)
    ck, report = check(fns, fn_hashes)
    if not report["ok"] and not (args.allow_unproven and "errors" not in report):
        report["error"] = "unproven obligations" if "errors" not in report else "type errors"
        emit_json(report)
        sys.exit(1)
    from .fold import fold_program
    from .inline import inline_concat_calls
    report["folded_calls"] = fold_program(fns.fns) if os.environ.get("AXON_FOLD", "1") != "0" else 0
    report["inlined_calls"] = inline_concat_calls(fns.fns) if os.environ.get("AXON_INLINE", "1") != "0" else 0
    gen = LLVMGen(fns.fns, fn_hashes, target_triple(), assume=os.environ.get("AXON_ASSUME", "0") == "1",
                  vectorize=os.environ.get("AXON_VEC", "1") != "0",
                  ranges=os.environ.get("AXON_RANGE", "1") != "0")
    ir = gen.program()
    report["parallel_regions"] = gen.par_regions
    report["vector_sums"] = gen.vector_sums
    report["bounded_remainders"] = gen.bounded_remainders
    report["backend"] = "llvm-ir"
    phash = report["program"]
    outdir = os.path.join(os.path.dirname(os.path.abspath(args.file)), ".axon-build")
    os.makedirs(outdir, exist_ok=True)
    cpath = os.path.join(outdir, f"{phash[:16]}.ll")
    with open(cpath, "w") as fh: fh.write(ir)
    report["ir"] = cpath
    if args.emit_llvm:
        print(ir); return report
    # cache key covers the program graph, the runtime library source and the compiler itself
    import hashlib
    h = hashlib.sha256(target_triple().encode())
    for name in sorted(os.listdir(HERE)):
        if name.endswith(".py"): h.update(open(os.path.join(HERE, name), "rb").read())
    h.update(repr([(k, os.environ.get(k, "")) for k in ("AXON_ASSUME", "AXON_VEC", "AXON_FOLD", "AXON_INLINE", "AXON_RANGE")]).encode())
    rt_hash = h.hexdigest()[:8]
    binpath = os.path.join(outdir, f"{phash[:16]}-{rt_hash}.bin")
    out = args.output or os.path.splitext(os.path.basename(args.file))[0]
    t0 = time.time()
    if os.path.exists(binpath) and not args.no_cache:
        report["build"] = {"cache": "hit", "graph": phash[:16]}
    else:
        # Application and Axon runtime share one LLVM module. No C compilation.
        cmd = ["clang", "-O3", cpath, "-nostdlib"]
        if sys.platform == "darwin": cmd += ["-lSystem"]  # required by Apple's ARM64 loader; no function imports
        else: cmd += ["-static", "-no-pie", "-Wl,-e,_start", "-Wl,--no-undefined"]
        cmd += ["-o", binpath]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stderr); sys.exit(1)
        report["build"] = {"cache": "miss", "graph": phash[:16], "llvm_seconds": round(time.time() - t0, 2),
                           "warnings": r.stderr.strip()[:2000]}
    shutil.copy2(binpath, out)
    imports = subprocess.check_output(["nm", "-u", out], text=True).strip().splitlines()
    declared = {("_" if sys.platform == "darwin" else "") + f.name for f in fns.fns if f.external}
    unexpected = [line.strip() for line in imports if line.split()[-1] not in declared]
    if unexpected:
        raise SystemExit("compiler introduced undeclared runtime imports: " + ", ".join(unexpected))
    report["binary"] = out
    report["runtime"] = "Axon kernel syscalls; no libc function imports"
    report["loader_dependency"] = "libSystem (required by macOS ARM64)" if sys.platform == "darwin" else "none (static ELF)"
    report["undefined_symbols"] = imports
    return report

def cmd_build(args):
    report = build(args)
    if args.emit_llvm: return
    if args.report: emit_json(report)
    else:
        s = report["summary"]
        print(f"axonc: {report['binary']}  graph {report['program'][:16]}  "
              f"obligations {s['proven']}/{s['obligations']} proven, {s['runtime_checks']} runtime checks, "
              f"{len(report['parallel_regions'])} parallel regions, {len(report['vector_sums'])} vectorised sums, "
              f"{report['folded_calls']} calls folded, {report['inlined_calls']} inlined, build {report['build']['cache']}")

def main(argv=None):
    ap = argparse.ArgumentParser(prog="axonc")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("file"); b.add_argument("-o", "--output")
    b.add_argument("--emit-llvm", action="store_true", help="print the LLVM IR instead of building"); b.add_argument("--report", action="store_true")
    b.add_argument("--allow-unproven", action="store_true", help="compile anyway (unsafe; for experiments)")
    b.add_argument("--no-cache", action="store_true")
    b.set_defaults(fn=cmd_build)
    c = sub.add_parser("check"); c.add_argument("file"); c.set_defaults(fn=cmd_check)
    g = sub.add_parser("graph"); g.add_argument("file"); g.add_argument("--full", action="store_true"); g.set_defaults(fn=cmd_graph)
    args = ap.parse_args(argv)
    args.fn(args)

if __name__ == "__main__":
    main()
