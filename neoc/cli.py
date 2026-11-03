"""neoc: build | check | graph

Diagnostics are JSON: an agent reads them, discharges or checks each
obligation, and resubmits. Builds are cached by program hash.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
import platform as host_platform
from . import legacy, quick, syntax as S
from .graph import hash_program, program_hash
from .check import Checker, CheckError
from .elaborate import ElaborationError

HERE = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.path.join(os.path.dirname(HERE), "runtime")
DIAGNOSTIC_FORMAT = 'json'
# The most IR lines forced inlining may grow one function to (0: unbounded).
INLINE_EXPANSION = 262144

def target_triple() -> str:
    """The triple clang itself would stamp on a module for this host."""
    return os.environ.get('NEO_TARGET') or subprocess.check_output(["clang", "-print-target-triple"], text=True).strip()

def load(path: str, overlays=None, target=None):
    if sys.platform not in ("darwin", "linux"):
        raise SystemExit("Neo currently supports macOS and Linux")
    if sys.maxsize <= 2**32 or sys.byteorder != "little":
        raise SystemExit("Neo's platform bindings currently require a 64-bit little-endian host")
    target = target or target_triple()
    platform = 'linux' if 'linux' in target else 'macos' if 'apple' in target else ''
    arch = target.split('-')[0]
    if not platform or arch not in ('arm64', 'aarch64', 'x86_64') or platform == 'macos' and arch == 'x86_64':
        raise SystemExit('Supported targets: ARM64 macOS/Linux and x86-64 Linux')
    binding = 'linux_x86_64' if platform == 'linux' and arch == 'x86_64' else platform
    names = ["core.neo", f"platform_{binding}.neo", "http.neo", "handles.neo"]
    if platform == "linux": names += ["http_linux.neo", "http_uring.neo"]
    from .modules import sources, SourceError
    try: prog = sources(path, [os.path.join(RUNTIME, name) for name in names],overlays)
    except SourceError as ex:
        emit_json({"ok": False, "errors": [ex.diagnostic]}); sys.exit(1)
    fn_hashes = hash_program(prog)
    return prog, fn_hashes

def emit_json(obj):
    if DIAGNOSTIC_FORMAT=='human':
        from .diagnostics import human
        print(human(obj))
    else:print(json.dumps(obj, indent=2, ensure_ascii=False))

def check(prog, fn_hashes,require_main=True,precompiled=None):
    ck = Checker(prog,require_main=require_main,precompiled=precompiled)
    # Reports name functions as written; the module prefix stays internal.
    shown = {f.name: getattr(f,'display_name',f.name) for f in prog.fns}
    def named(): return [{**o, "fn": shown.get(o["fn"], o["fn"])} for o in ck.obligations]
    try:
        ck.run()
    except CheckError as ex:
        return ck, {"ok": False, "errors": ex.errors, "obligations": named()}
    unproven = [o for o in ck.obligations if o["status"] in ("unproven", "unknown")]
    return ck, {"ok": not unproven, "program": program_hash(fn_hashes),
                "functions": {n: h for n, h in fn_hashes.items()},
                "obligations": named(),
                "summary": {"obligations": len(ck.obligations),
                            "proven": sum(o["status"] == "proven" for o in ck.obligations),
                            "runtime_checks": ck.runtime_checks,
                            "unproven": len(unproven)}}

def cmd_check(args):
    fns, fn_hashes = load(args.file)
    _, report = check(fns, fn_hashes,require_main=not args.library)
    emit_json(report)
    sys.exit(0 if report["ok"] else 1)

def cmd_graph(args):
    fns, fn_hashes = load(args.file)
    nodes = hash_program.last_nodes
    emit_json({"program": program_hash(fn_hashes), "functions": fn_hashes, "nodes": len(nodes),
               "graph": nodes if args.full else {h: n["op"] for h, n in nodes.items()}})

def build(args, want_binary=True):
    from .llvm import LLVMGen
    from . import linear
    started = time.monotonic()
    # Taken before anything the full cache key reads, so a record never
    # outlives what built its binary.
    quick_key = quick.key(args.file, getattr(args, 'dev', False), getattr(args, 'opt_level', None), args.allow_unproven)
    # The dev profile trades run time for build time: LLVM -O1 and no policy
    # inlining (constant-argument and small pure helpers); `inline fn` stays.
    profile = 'dev' if getattr(args, 'dev', False) else 'release'
    opt_level = str(getattr(args, 'opt_level', None) or os.environ.get('NEO_OPT_LEVEL', '1' if profile == 'dev' else '3'))
    inline_budget = int(os.environ.get('NEO_INLINE_BUDGET', '160'))
    inline_expansion = int(os.environ.get('NEO_INLINE_EXPANSION', str(INLINE_EXPANSION)))
    if opt_level not in ('0','1','2','3') or not 0 <= inline_budget <= 10000 or inline_expansion < 0:
        raise ValueError('optimization level must be 0..3; NEO_INLINE_BUDGET must be 0..10000; NEO_INLINE_EXPANSION must be >= 0')
    optimization = {'profile':profile, 'level':int(opt_level), 'inline_budget':inline_budget, 'inline_expansion':inline_expansion}
    library_cache = getattr(args,'library_cache',None)
    library_roots = [os.path.realpath(root) for root in [RUNTIME,os.path.join(os.path.dirname(HERE),'stdlib'),*getattr(args,'library_root',[])]] if library_cache else []
    optimization['library_roots'] = library_roots
    target = target_triple()
    h = hashlib.sha256(target.encode())
    h.update(subprocess.check_output(['clang','--version']))
    for name in sorted(os.listdir(HERE)):
        if name.endswith('.py'): h.update(open(os.path.join(HERE,name),'rb').read())
    h.update(repr([(k,os.environ.get(k,'')) for k in ('NEO_ASSUME','NEO_VEC','NEO_FOLD','NEO_INLINE','NEO_RANGE','NEO_SWITCH','NEO_UNIQUE','NEO_ALLOC_STATS','NEO_FRAME_POINTERS')]).encode())
    h.update(str(args.allow_unproven).encode())
    library_salt=h.copy()
    library_salt.update(repr({'profile':profile,'inline_budget':inline_budget,'inline_expansion':inline_expansion,'library_roots':library_roots}).encode())
    h.update(repr(optimization).encode())
    fns, fn_hashes = load(args.file,target=target)
    parse_seconds = time.monotonic() - started
    for path,text in sorted(fns.sources.items()): h.update(path.encode()); h.update(text.encode())
    # Module prefixes come from the nearest package manifest and appear in symbols.
    h.update(repr(sorted(fns.module_prefixes.items())).encode())
    cache_key = h.hexdigest()
    outdir = os.path.join(os.path.dirname(os.path.abspath(args.file)), legacy.build_dir(args.file))
    def remember(report):
        entry = quick.resolved(args.file)
        if library_cache or quick.folder(entry) != outdir: return
        # A record only saves time later; failing to write one never fails a build.
        try: quick.remember(quick_key, entry, fns, cache_key, report)
        except (OSError, KeyError, TypeError, ValueError): pass
    os.makedirs(outdir, exist_ok=True)
    metadata = os.path.join(outdir, cache_key+'.json')
    binpath = os.path.join(outdir, cache_key+'.bin')
    out = args.output or os.path.splitext(os.path.basename(args.file))[0]
    if not args.no_cache and not args.emit_llvm and os.path.exists(metadata) and os.path.exists(binpath):
        try:
            cached = json.load(open(metadata))
            if cached['binary_sha256'] == hashlib.sha256(open(binpath,'rb').read()).hexdigest():
                cached['build'] = {'cache':'hit','graph':cached['program'][:16], 'total_seconds':round(time.monotonic()-started,4)}
                cached['binary'] = out; publish(binpath,out); remember(cached); return cached
        except (OSError,ValueError,KeyError): pass
    stage = time.monotonic()
    prepared=None
    if library_cache and not args.emit_llvm:
        if args.allow_unproven:raise ValueError('native library caching requires fully checked code')
        from . import native_libraries
        from .elaborate import prepare
        prepare(fns)
        library_identity,library_names=native_libraries.library_identity(fns,library_roots,library_salt.digest())
        if not args.no_cache:prepared=native_libraries.lookup(library_cache,library_identity,library_names)
        for fn in fns.fns:fn.native_library=fn.name in library_names
    proving = linear.SPENT[0]
    ck, report = check(fns, fn_hashes,precompiled=prepared['capabilities'] if prepared else None)
    check_seconds = time.monotonic() - stage
    prove_seconds = linear.SPENT[0] - proving
    if not report["ok"] and not (args.allow_unproven and "errors" not in report):
        report["error"] = "unproven obligations" if "errors" not in report else "type errors"
        emit_json(report)
        sys.exit(1)
    from .fold import fold_program
    from .inline import inline_concat_calls, push_html_escapes
    stage = time.monotonic()
    report["folded_calls"] = fold_program(fns.fns) if os.environ.get("NEO_FOLD", "1") != "0" else 0
    report["inlined_calls"] = inline_concat_calls(fns.fns) if os.environ.get("NEO_INLINE", "1") != "0" else 0
    report["escape_rewrites"] = push_html_escapes(fns.fns) if os.environ.get("NEO_INLINE", "1") != "0" else 0
    optimize_seconds = time.monotonic() - stage
    stage = time.monotonic()
    gen = LLVMGen(fns.fns, fn_hashes, target, assume=os.environ.get("NEO_ASSUME", "0") == "1",
                  vectorize=os.environ.get("NEO_VEC", "1") != "0",
                  ranges=os.environ.get("NEO_RANGE", "1") != "0",
                  literal_inline=os.environ.get("NEO_INLINE", "1") != "0" and profile == 'release', inline_budget=inline_budget,library_roots=library_roots,
                  switches=os.environ.get("NEO_SWITCH", "1") != "0", unique_flags=os.environ.get("NEO_UNIQUE", "1") != "0",
                  inline_expansion=inline_expansion)
    ir = gen.program()
    # prove_seconds is the part of check_seconds spent deciding obligations.
    report['build_stages'] = {'parse_seconds':round(parse_seconds,4), 'check_seconds':round(check_seconds,4), 'prove_seconds':round(prove_seconds,4),
                             'optimize_seconds':round(optimize_seconds,4), 'lower_seconds':round(time.monotonic()-stage,4)}
    report['optimization'] = optimization
    report['omitted_internal_functions'] = gen.omitted_functions
    report["parallel_regions"] = gen.par_regions
    report["vector_sums"] = gen.vector_sums
    report["vector_arrays"] = gen.vector_arrays
    report["bounded_remainders"] = gen.bounded_remainders
    report["switches"] = gen.switches or []
    report['overflow_checks'] = gen.overflow_checks
    report['literal_inlined_functions'] = sorted(gen.literal_inlined)
    # Calls inside loops/comprehensions whose callee exceeded NEO_INLINE_BUDGET
    # and so lost forced inlining; `inline fn` forces it regardless.
    report['inline_budget_misses'] = gen.inline_budget_misses
    report['forced_inline_functions'] = sorted(getattr(f,'display_name',f.name) for f in fns.fns if f.name in gen.forced_inline)
    if gen.inline_ignored: report['inline_ignored'] = gen.inline_ignored
    # Policy-inlined callees that would have grown a function past
    # NEO_INLINE_EXPANSION IR lines; they stay ordinary calls.
    if gen.inline_cut: report['inline_expansion_cuts'] = gen.inline_cut
    report["backend"] = "llvm-ir"
    library_objects=[]
    if library_cache and not args.emit_llvm:
        from .native_libraries import apply
        if prepared:
            library_ir,library_objects,library_report=native_libraries.merge(gen,prepared['folder'],prepared['key'],prepared['data'])
            library_report['prechecked_obligations']=prepared['checked_obligations']
            library_report['prechecked_runtime_checks']=prepared['checked_runtime_checks']
        else:
            library_ir,library_objects,library_report=apply(gen,library_cache,target,force=args.no_cache)
            native_libraries.publish_index(library_cache,library_identity,library_names,library_report,ck)
        report['native_libraries']=library_report
        if library_ir is not None:ir=library_ir
    phash = report["program"]
    # Keep diagnostic/profiling IR matched to the target and optimization flags,
    # including when different variants of the same graph are built concurrently.
    cpath = os.path.join(outdir, f"{cache_key[:16]}.ll")
    ir_stage=cpath+'.'+str(os.getpid())+'.tmp'
    with open(ir_stage, "w") as fh: fh.write(ir)
    os.replace(ir_stage,cpath)
    report["ir"] = cpath
    if args.emit_llvm:
        print(ir); return report
    # cache key covers the program graph, the runtime library source and the compiler itself
    t0 = time.monotonic()
    # Application and Neo runtime share one LLVM module. No C compilation.
    # Compiling and linking run as two clang invocations so reports can tell
    # LLVM's time from the linker's; the binary is the same as from one.
    flags = ['--target='+target, '-O'+opt_level]
    compile_flags = ['-ffunction-sections', '-fdata-sections']
    # AArch64's default outlined CAS dispatch calls compiler-rt helpers. Emit
    # direct architectural atomics instead; freestanding programs link no CRT.
    if target.startswith(('arm64','aarch64')):compile_flags += ['-mno-outline-atomics']
    # x86-64: start every loop on a 32-byte boundary (LLVM's default is 16).
    # Identical machine code for the sieve's marking loop measured 411-457 ms
    # on an EPYC-Genoa depending only on where LLVM happened to place it;
    # with 32-byte loop alignment every placement ran at the fast end.
    if target.startswith('x86_64'):compile_flags += ['-falign-loops=32']
    object_stage=binpath+'.'+str(os.getpid())+'.o'
    compiled = subprocess.run(["clang", *flags, *compile_flags, '-c', cpath, '-o', object_stage], capture_output=True, text=True)
    if compiled.returncode != 0:
        if os.path.exists(object_stage):os.unlink(object_stage)
        emit_json({'ok':False,'errors':[{'kind':'link','msg':compiled.stderr}]});sys.exit(1)
    t1 = time.monotonic()
    cmd = ["clang", *flags, object_stage, *library_objects, "-nostdlib"]
    if 'apple' in target: cmd += ["-lSystem", "-Wl,-dead_strip"]  # required by Apple's ARM64 loader; no function imports
    else:
        cmd += ["-static", "-no-pie", "-Wl,-e,_start", "-Wl,--no-undefined", "-Wl,--gc-sections"]
        if target.split('-')[0] != host_platform.machine().replace('arm64','aarch64'): cmd += ['-fuse-ld=lld']
    # Explicit exports remain ABI roots even when no local call reaches them.
    for function in fns.fns:
        if function.exported and not function.external and not (bool(function.source) and os.path.realpath(function.source).startswith(os.path.realpath(RUNTIME)+os.sep)):
            symbol=('_' if 'apple' in target else '')+function.name
            cmd += ['-Wl,-u,'+symbol]
    binary_stage=binpath+'.'+str(os.getpid())+'.building'
    cmd += ["-o", binary_stage]
    r = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(object_stage)
    if r.returncode != 0:
        if os.path.exists(binary_stage):os.unlink(binary_stage)
        emit_json({'ok':False,'errors':[{'kind':'link','msg':r.stderr}]});sys.exit(1)
    os.replace(binary_stage,binpath)
    t2 = time.monotonic()
    # llvm_seconds covers both invocations, as it did when they were one.
    report["build"] = {"cache": "miss", "graph": phash[:16], "llvm_seconds": round(t2 - t0, 4),
                       "compile_seconds": round(t1 - t0, 4), "link_seconds": round(t2 - t1, 4),
                       "warnings": (compiled.stderr + r.stderr).strip()[:2000]}
    imports = subprocess.check_output(["nm", "-u", binpath], text=True).strip().splitlines()
    declared = {("_" if 'apple' in target else "") + f.name for f in fns.fns if f.external}
    unexpected = [line.strip() for line in imports if line.split()[-1] not in declared]
    if unexpected:
        raise SystemExit("compiler introduced undeclared runtime imports: " + ", ".join(unexpected))
    report["binary"] = out
    report["runtime"] = "Neo kernel syscalls; no libc function imports"
    report["loader_dependency"] = "libSystem (required by macOS ARM64)" if 'apple' in target else "none (static ELF)"
    report["undefined_symbols"] = imports
    report['binary_sha256'] = hashlib.sha256(open(binpath,'rb').read()).hexdigest()
    report['cache_key'] = cache_key
    report['sources'] = {p:hashlib.sha256(t.encode()).hexdigest() for p,t in fns.sources.items()}
    report['build']['total_seconds'] = round(time.monotonic()-started,4)
    metadata_stage=metadata+'.'+str(os.getpid())+'.tmp'
    with open(metadata_stage,'w') as file: json.dump(report,file)
    os.replace(metadata_stage,metadata)
    publish(binpath,out)
    remember(report)
    return report

publish = quick.publish

def cmd_build(args):
    report = build(args)
    if args.emit_llvm: return
    if args.report: emit_json(report)
    else:
        s = report["summary"]
        print(f"neoc: {report['binary']}  graph {report['program'][:16]}  "
              f"obligations {s['proven']}/{s['obligations']} proven, {s['runtime_checks']} runtime checks, "
              f"{len(report['parallel_regions'])} parallel regions, {len(report['vector_sums'])} vectorised sums, "
              f"{report['folded_calls']} calls folded, {report['inlined_calls']} inlined, build {report['build']['cache']}")
        dependency=report.get('native_libraries',{})
        if 'prechecked_obligations' in dependency:
            print(f"neoc: native libraries {dependency['cache']}: {dependency['prechecked_obligations']} prechecked obligations, {dependency['prechecked_runtime_checks']} embedded runtime checks")

def main(argv=None):
    """Run the CLI on a thread with a large stack. Every compiler pass recurses
    over expression depth, and an interpreter's else-if dispatch over hundreds
    of opcodes nests that deep (CPython's default limit stops near 110 arms)."""
    import threading
    outcome = {}
    def run():
        try: command(argv)
        except BaseException as exc: outcome['error'] = exc
    try:
        previous = threading.stack_size(512 << 20)
    except (ValueError, RuntimeError):
        return command(argv)
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 250000))
    try:
        worker = threading.Thread(target=run, name='neoc', daemon=True); worker.start()
    finally: threading.stack_size(previous)
    worker.join()
    if 'error' in outcome: raise outcome['error']

def command(argv=None):
    global DIAGNOSTIC_FORMAT
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv[:1]==['run']:
        at=2 if argv[1:2]==['--dev'] else 1
        if argv[at:at+1]==['--']:argv.insert(at,'__project__')
    ap = argparse.ArgumentParser(prog="neo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("file",nargs='?'); b.add_argument("-o", "--output")
    b.add_argument('--target',help='LLVM target triple; e.g. x86_64-unknown-linux-gnu')
    b.add_argument("--emit-llvm", action="store_true", help="print the LLVM IR instead of building"); b.add_argument("--report", action="store_true")
    b.add_argument("--allow-unproven", action="store_true", help="compile anyway (unsafe; for experiments)")
    b.add_argument("--no-cache", action="store_true")
    b.add_argument('--opt-level',choices=['0','1','2','3'],default=None,help='LLVM optimization level (default 3, or NEO_OPT_LEVEL)')
    b.add_argument('--dev',action='store_true',help='fast development build: LLVM -O1 unless --opt-level, no policy inlining')
    b.add_argument('--library-cache',help='content-addressed directory for statically linked checked native libraries')
    b.add_argument('--library-root',action='append',default=[],help='dependency source directory to precompile (repeatable)')
    b.set_defaults(fn=cmd_build)
    c = sub.add_parser("check"); c.add_argument("file"); c.add_argument('--library',action='store_true'); c.set_defaults(fn=cmd_check)
    g = sub.add_parser("graph"); g.add_argument("file"); g.add_argument("--full", action="store_true"); g.set_defaults(fn=cmd_graph)
    from . import project
    r=sub.add_parser('run');r.add_argument('--dev',action='store_true',help='build with the dev profile');r.add_argument('file',nargs='?');r.add_argument('arguments',nargs=argparse.REMAINDER);r.set_defaults(fn=project.run)
    t=sub.add_parser('test');t.add_argument('path',nargs='?',default='.');t.add_argument('--unit-only',action='store_true');t.set_defaults(fn=project.test)
    f=sub.add_parser('fmt');f.add_argument('paths',nargs='*');f.add_argument('--check',action='store_true');f.set_defaults(fn=project.fmt)
    i=sub.add_parser('init');i.add_argument('path');i.set_defaults(fn=project.init)
    from . import packages
    p=sub.add_parser('pkg');p.add_argument('action',choices=['lock','verify','vendor']);p.add_argument('path',nargs='?',default='.');p.set_defaults(fn=packages.command)
    v=sub.add_parser('version');v.set_defaults(fn=lambda args: print('Neo '+packages.VERSION))
    from . import lsp
    l=sub.add_parser('lsp');l.set_defaults(fn=lsp.command)
    from . import release
    rel=sub.add_parser('release');rel.add_argument('-o','--output',required=True);rel.set_defaults(fn=release.command)
    from . import doctor
    sub.add_parser('doctor',help='check that this machine can build Neo programs').set_defaults(fn=doctor.command)
    for parser in (b,c,g):parser.add_argument('--diagnostic-format',choices=['json','human'],default='json')
    args = ap.parse_args(argv)
    DIAGNOSTIC_FORMAT=getattr(args,'diagnostic_format','json')
    try:
        if getattr(args,'target',None):os.environ['NEO_TARGET']=args.target
        if args.cmd=='build':args.file=project.entry(args.file)
        args.fn(args)
    except (OSError,ValueError,RecursionError) as exc:
        emit_json({'ok':False,'errors':[{'kind':'tool','msg':str(exc)}]});raise SystemExit(1)
    except ElaborationError as exc:
        emit_json({'ok':False,'errors':exc.errors});raise SystemExit(1)

if __name__ == "__main__":
    main()
