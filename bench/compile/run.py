#!/usr/bin/env python3
"""Compile-time benchmark: Neo against Rust, Go and Zig on equivalent programs.

usage: run.py OUT.json ROUNDS

Every (program, implementation) pair is built three ways in each round:
  cold         every build cache the toolchain keeps is emptied first (Neo's
               .neo-build, Cargo's target directory, GOCACHE, Zig's local and
               global caches); downloaded dependency sources stay.
  noop         the same build again, nothing changed.
  incremental  one comment line appended to the program's main source file.
Rounds visit the pairs in a shuffled order (fixed seed), so slow drift on the
box spreads over every implementation. Wall time, child CPU time and peak RSS
come from GNU time. A Neo cold build also records its --report stage split.

Release builds are the ones the runtime benchmarks use: Neo's default (-O3),
Cargo's release profile (opt-level 3, one codegen unit, fat LTO), Zig
ReleaseFast, Go's only mode. Development builds are rows of their own: Neo
--dev, Cargo's dev profile, Zig Debug.

Environment:
  NEO_TREES   label=path,... Neo checkouts to compare (default after=$PWD's
              checkout); each builds its own copy of the Neo programs.
  NEO_DEV     labels of NEO_TREES that also get a --dev row (default: none).
  DEBUG       1 (default) adds Rust dev-profile and Zig Debug rows.
  SOURCES     the checkout holding bench/ sources for Rust, Go and Zig.
  WORK        scratch directory (default /root/cc).
  ONLY        comma-separated program names to run (default: all).
  LARGE_ROUNDS  rounds that include the large program (default 1).
  RESUME      1: keep the runs already in OUT.json and do only the rest.
"""
import json, os, random, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

E = os.environ.get
HERE = Path(__file__).resolve().parent
SOURCES = Path(E('SOURCES', str(HERE.parents[1])))
WORK = Path(E('WORK', '/root/cc'))
TREES = [tuple(item.split('=', 1)) for item in E('NEO_TREES', 'after=' + str(HERE.parents[1])).split(',')]
ENV = dict(os.environ, GOWORK='off', GOTOOLCHAIN='local', CGO_ENABLED='0', GOCACHE=str(WORK / 'gocache'),
           GOFLAGS='-trimpath', CARGO_TARGET_DIR=str(WORK / 'cargo-target'), CARGO_NET_OFFLINE='true')
ZIG_CACHES = ['--cache-dir', str(WORK / 'zig-local'), '--global-cache-dir', str(WORK / 'zig-global')]

# program -> {implementation: (cwd, build argv, main source edited for the incremental build, output)}
# Neo programs are relative to each Neo tree; the others to SOURCES.
NEO = {'hello': 'examples/hello.neo', 'http': 'examples/http.neo', 'json': 'examples/library_bench.neo',
       'nbody': 'examples/nbody.neo', 'https-client': 'bench/fetch/fetch.neo',
       'tls-fixture': 'tests/fixtures/language_tls.neo', 'large': 'compiler/src/main.neo'}
OTHER = {
    'hello': {'Rust': ('bench/compile/rust', ['cargo', 'build', '--release', '--offline', '-p', 'hello'], 'bench/compile/rust/hello/src/main.rs'),
              'Go': ('bench/compile/go', ['go', 'build', '-o', '{out}', './hello'], 'bench/compile/go/hello/main.go'),
              'Zig': ('bench/compile/zig', ['zig', 'build-exe', '-OReleaseFast', 'hello.zig', '-femit-bin={out}'], 'bench/compile/zig/hello.zig')},
    # http@0.1.0: the hyper dependency tree has an `http` crate of its own.
    'http': {'Rust': ('bench/compile/rust', ['cargo', 'build', '--release', '--offline', '-p', 'http@0.1.0'], 'bench/rust/src/http_hyper.rs'),
             'Go': ('bench/go', ['go', 'build', '-o', '{out}', './http'], 'bench/go/http/main.go'),
             'Zig': ('bench/zig', ['zig', 'build-exe', '-OReleaseFast', 'http_std.zig', '-femit-bin={out}'], 'bench/zig/http_std.zig')},
    'json': {'Rust': ('bench/compile/rust', ['cargo', 'build', '--release', '--offline', '-p', 'json'], 'bench/rust/src/usability.rs'),
             'Go': ('bench/core', ['go', 'build', '-o', '{out}', 'json.go'], 'bench/core/json.go'),
             'Zig': ('bench/zig', ['zig', 'build-exe', '-OReleaseFast', 'json.zig', '-femit-bin={out}'], 'bench/zig/json.zig')},
    'nbody': {'Rust': ('bench/compile/rust', ['cargo', 'build', '--release', '--offline', '-p', 'nbody'], 'bench/rust/src/nbody.rs'),
              'Go': ('bench/go', ['go', 'build', '-o', '{out}', './nbody'], 'bench/go/nbody/main.go'),
              'Zig': ('bench/zig', ['zig', 'build-exe', '-OReleaseFast', 'nbody.zig', '-femit-bin={out}'], 'bench/zig/nbody.zig')},
    'https-client': {'Rust': ('bench/compile/rust', ['cargo', 'build', '--release', '--offline', '-p', 'fetch'], 'bench/fetch/rust/src/main.rs'),
                     'Go': ('bench/fetch/go', ['go', 'build', '-o', '{out}', './client'], 'bench/fetch/go/client/main.go'),
                     'Zig': ('bench/compile/zig', ['zig', 'build-exe', '-OReleaseFast', 'fetch.zig', '-femit-bin={out}'], 'bench/compile/zig/fetch.zig')},
}
# Rust binary names by package, for the size of what was built.
RUST_BIN = {'hello': 'hello', 'http': 'http_hyper', 'json': 'usability', 'nbody': 'nbody', 'fetch': 'fetch-client'}
COMMENT = {'.neo': '; compile-time benchmark edit\n', '.rs': '// compile-time benchmark edit\n',
           '.go': '// compile-time benchmark edit\n', '.zig': '// compile-time benchmark edit\n'}


def cases():
    only = set(filter(None, E('ONLY', '').split(',')))
    dev = set(filter(None, E('NEO_DEV', '').split(',')))
    out = []
    for program, path in NEO.items():
        for label, tree in TREES:
            for profile in ([], ['--dev']) if label in dev else ([],):
                out.append({'program': program, 'impl': 'Neo ' + label + (' dev' if profile else ''), 'cwd': tree,
                            'source': str(Path(tree) / path), 'argv': ['./neo', 'build', path, '-o', '{out}', '--report', *profile],
                            'cache': [str(Path(tree) / Path(path).parent / '.neo-build')]})
        for impl, (cwd, argv, source) in OTHER.get(program, {}).items():
            if not (SOURCES / source).exists(): continue
            cache = {'Rust': [ENV['CARGO_TARGET_DIR']], 'Go': [ENV['GOCACHE']], 'Zig': [str(WORK / 'zig-local'), str(WORK / 'zig-global')]}[impl]
            variants = [(impl, argv)]
            if E('DEBUG', '1') == '1' and impl == 'Rust': variants.append(('Rust debug', [a for a in argv if a != '--release']))
            if E('DEBUG', '1') == '1' and impl == 'Zig': variants.append(('Zig Debug', ['-ODebug' if a == '-OReleaseFast' else a for a in argv]))
            for name, variant in variants:
                built = None
                if impl == 'Rust':
                    package = variant[variant.index('-p') + 1].split('@')[0]
                    built = str(Path(ENV['CARGO_TARGET_DIR']) / ('release' if '--release' in variant else 'debug') / RUST_BIN[package])
                out.append({'program': program, 'impl': name, 'cwd': str(SOURCES / cwd), 'source': str(SOURCES / source),
                            'argv': variant + (ZIG_CACHES if impl == 'Zig' else []), 'cache': cache, 'built': built})
    return [c for c in out if not only or c['program'] in only]


def timed(case, out):
    argv = [a.replace('{out}', out) for a in case['argv']]
    with tempfile.NamedTemporaryFile('r', suffix='.time') as stats:
        started = time.perf_counter()
        r = subprocess.run(['/usr/bin/time', '-f', '%e %U %S %M', '-o', stats.name, *argv], cwd=case['cwd'], env=ENV,
                           capture_output=True, text=True)
        wall = time.perf_counter() - started
        fields = stats.read().split()[-4:]
    if r.returncode != 0:
        raise SystemExit(f"build failed: {case['impl']} {case['program']}\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    row = {'wall': round(wall, 4), 'cpu': round(float(fields[1]) + float(fields[2]), 3), 'rss_kb': int(fields[3])}
    if case['impl'].startswith('Neo'):
        report = json.loads(r.stdout)
        row['stages'] = report.get('build_stages', {})
        row['build'] = {k: v for k, v in report.get('build', {}).items() if k != 'warnings'}
    return row


def run_case(case, round_no):
    out = str(WORK / 'bin' / (case['impl'].replace(' ', '-') + '-' + case['program']))
    for cache in case['cache']: shutil.rmtree(cache, ignore_errors=True)
    rows = {'cold': timed(case, out), 'noop': timed(case, out)}
    source = Path(case['source']); original = source.read_bytes()
    try:
        source.write_bytes(original + COMMENT[source.suffix].encode())
        rows['incremental'] = timed(case, out)
    finally:
        source.write_bytes(original)
    built = case.get('built') or out
    rows['binary_bytes'] = os.path.getsize(built) if os.path.exists(built) else None
    return rows


def versions():
    def first(argv):
        try: return subprocess.run(argv, capture_output=True, text=True, env=ENV).stdout.strip().splitlines()[0]
        except (OSError, IndexError): return None
    trees = {}
    for label, tree in TREES:
        trees[label] = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=tree, capture_output=True, text=True).stdout.strip() or None
    return {'neo_trees': trees, 'clang': first(['clang', '--version']), 'python': first(['python3', '--version']),
            'rustc': first(['rustc', '--version']), 'cargo': first(['cargo', '--version']), 'go': first(['go', 'version']),
            'zig': first(['zig', 'version']), 'kernel': first(['uname', '-r']),
            'cpu': next((l.split(':', 1)[1].strip() for l in open('/proc/cpuinfo') if l.startswith('model name')), None),
            'cpus': os.cpu_count()}


def main():
    out_path, rounds = sys.argv[1], int(sys.argv[2])
    large_rounds = int(E('LARGE_ROUNDS', '1'))
    (WORK / 'bin').mkdir(parents=True, exist_ok=True)
    result = {'method': __doc__, 'versions': versions(), 'runs': []}
    if E('RESUME') == '1' and Path(out_path).exists(): result = json.loads(Path(out_path).read_text())
    done = {(r['round'], r['program'], r['impl']) for r in result['runs']}
    rng = random.Random(20261103)
    for round_no in range(rounds):
        todo = [c for c in cases() if c['program'] != 'large' or round_no < large_rounds]
        rng.shuffle(todo)
        for case in todo:
            if (round_no, case['program'], case['impl']) in done: continue
            rows = run_case(case, round_no)
            result['runs'].append({'round': round_no, 'program': case['program'], 'impl': case['impl'], **rows})
            print(f"round {round_no} {case['program']:13s} {case['impl']:14s} cold {rows['cold']['wall']:8.2f}s noop {rows['noop']['wall']:7.2f}s "
                  f"incremental {rows['incremental']['wall']:8.2f}s", flush=True)
            Path(out_path).write_text(json.dumps(result, indent=1))
    print('COMPILE-BENCH-DONE')


if __name__ == '__main__':
    main()
