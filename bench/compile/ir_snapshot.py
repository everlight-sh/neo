#!/usr/bin/env python3
"""The LLVM IR every corpus program lowers to, for comparing compilers or settings.

usage: ir_snapshot.py ROOT OUT.json [BASE.json]

Lowers examples/*.neo, tests/fixtures/*.neo, bench/core/*.neo, the HTTPS
client and the large program with ROOT's compiler (front end and IR only, no
clang) for each of TARGETS, and records the IR's SHA-256 and size, or the
digest of the rejection for programs that do not check. With BASE.json, it
lists the programs whose IR differs from that snapshot. NEO_INLINE_EXPANSION
and other NEO_* variables apply as in a build.

Environment: TARGETS (comma-separated; default x86_64-unknown-linux-gnu),
JOBS (parallel lowerings; default 2).
"""
import argparse, contextlib, glob, hashlib, io, json, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor


def one(root, path, target):
    """Lower one program in this process; print its JSON line."""
    sys.path.insert(0, root); os.environ['NEO_TARGET'] = target
    sys.setrecursionlimit(250000); threading.stack_size(512 << 20)
    out = {}
    def lower():
        from neoc import cli
        args = argparse.Namespace(file=path, output=None, emit_llvm=True, report=False, allow_unproven=False, no_cache=True,
                                  opt_level=None, library_cache=None, library_root=[], target=None)
        buffer = io.StringIO(); started = time.monotonic()
        try:
            with contextlib.redirect_stdout(buffer): cli.build(args)
            ir = buffer.getvalue()
            out.update(ir_sha=hashlib.sha256(ir.encode()).hexdigest(), ir_bytes=len(ir))
        except SystemExit:
            out.update(error_sha=hashlib.sha256(buffer.getvalue().encode()).hexdigest())
        out['seconds'] = round(time.monotonic() - started, 3)
    worker = threading.Thread(target=lower); worker.start(); worker.join()
    print(json.dumps(out))


def main():
    if sys.argv[1] == '--one': return one(*sys.argv[2:5])
    root, out_path = os.path.abspath(sys.argv[1]), sys.argv[2]
    files = sorted(glob.glob(root + '/examples/*.neo') + glob.glob(root + '/tests/fixtures/*.neo') + glob.glob(root + '/bench/core/*.neo')
                   + [root + '/bench/fetch/fetch.neo', root + '/compiler/src/main.neo'])
    targets = os.environ.get('TARGETS', 'x86_64-unknown-linux-gnu').split(',')
    def job(item):
        path, target = item
        r = subprocess.run([sys.executable, os.path.abspath(__file__), '--one', root, path, target], capture_output=True, text=True, cwd=root)
        try: result = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError): result = {'crash': r.stderr[-500:]}
        return os.path.relpath(path, root) + '@' + target, result
    with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as pool:
        snapshot = dict(pool.map(job, [(f, t) for f in files for t in targets]))
    with open(out_path, 'w') as file: json.dump(snapshot, file, indent=1, sort_keys=True)
    print(len(snapshot), 'programs x targets, front-end seconds', round(sum(r.get('seconds', 0) for r in snapshot.values()), 1))
    if len(sys.argv) > 3:
        with open(sys.argv[3]) as file: base = json.load(file)
        same = lambda r: {k: v for k, v in r.items() if k != 'seconds'}
        changed = sorted(k for k in snapshot if same(snapshot[k]) != same(base.get(k, {})))
        for k in changed: print('CHANGED', k, base.get(k, {}).get('ir_bytes'), snapshot[k].get('ir_bytes'))
        print(f'{len(snapshot) - len(changed)} unchanged, {len(changed)} changed')


if __name__ == '__main__':
    main()
