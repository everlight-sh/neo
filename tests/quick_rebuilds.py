#!/usr/bin/env python3
"""Unchanged rebuilds answered without parsing (neoc/quick.py), and every way
a recorded build stops matching: edited imports, retargeted import links, a
new package manifest, other flags, targets, variables, compiler sources or
clang, a damaged cached binary, and package imports, which never use it."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def neo(*argv, root=ROOT, env=None):
    r = subprocess.run([sys.executable, '-m', 'neoc', *map(str, argv)], cwd=root, env={**os.environ, **(env or {})},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    return r


def build(source, output, *flags, root=ROOT, env=None):
    """(cache, quick, report) of one `neo build --report`."""
    report = json.loads(neo('build', source, '-o', output, '--report', *flags, root=root, env=env).stdout)
    return report['build']['cache'], report['build'].get('quick', False), report


def run(binary, *argv):
    return subprocess.run([str(binary), *argv], capture_output=True, text=True, check=True).stdout


def cross_target():
    """A target other than the host's that this machine can link, or None."""
    if not shutil.which('ld.lld'): return None
    machine = platform.machine().replace('arm64', 'aarch64')
    return 'x86_64-unknown-linux-gnu' if machine == 'aarch64' else 'aarch64-unknown-linux-gnu'


def main():
    with tempfile.TemporaryDirectory(prefix='neo-quick-') as temporary:
        folder = Path(temporary)
        (folder/'a.neo').write_text('fn answer()->i64=1\n')
        (folder/'b.neo').write_text('fn answer()->i64=2\n')
        (folder/'lib.neo').symlink_to('a.neo')
        source = folder/'main.neo'
        source.write_text('import "lib.neo"\nfn main(n:i64)->i64=n*10+answer()\n')
        app = folder/'app'

        assert build(source, app)[:2] == ('miss', False)
        cache, fast, report = build(source, app)
        assert (cache, fast) == ('hit', True) and run(app, '7') == '71\n'
        # The same answer as the full path's hit, apart from timing and the marker.
        slow = build(source, app, env={'NEO_QUICK': '0'})
        assert slow[:2] == ('hit', False)
        for r in (report, slow[2]): r['build'].pop('total_seconds'); r['build'].pop('quick', None)
        assert report == slow[2]
        line = neo('build', source, '-o', app).stdout
        assert line == neo('build', source, '-o', app, env={'NEO_QUICK': '0'}).stdout and line.rstrip().endswith('build hit')
        other = folder/'elsewhere'/'app'
        assert build(source, other)[:2] == ('hit', True) and other.read_bytes() == app.read_bytes()

        # An imported file changes.
        (folder/'a.neo').write_text('fn answer()->i64=3\n')
        assert build(source, app)[:2] == ('miss', False) and run(app, '7') == '73\n'
        assert build(source, app)[:2] == ('hit', True)

        # A different file takes the imported name.
        (folder/'lib.neo').unlink(); (folder/'lib.neo').symlink_to('b.neo')
        assert build(source, app)[:2] == ('miss', False) and run(app, '7') == '72\n'
        (folder/'lib.neo').unlink(); (folder/'lib.neo').symlink_to('a.neo')
        assert build(source, app)[:2] == ('hit', False) and run(app, '7') == '73\n'
        assert build(source, app)[:2] == ('hit', True)

        # A package manifest appears above the modules, then changes; it names their symbols.
        (folder/'neo.toml').write_text('[package]\nname="demo"\nversion="0.1.0"\n')
        assert build(source, app)[:2] == ('miss', False) and run(app, '7') == '73\n'
        assert build(source, app)[:2] == ('hit', True)
        (folder/'neo.toml').write_text('[package]\nname="renamed"\nversion="0.1.0"\n')
        assert build(source, app)[:2] == ('miss', False)
        (folder/'neo.toml').unlink()
        assert build(source, app)[:2] == ('hit', False)

        # Flags and variables that change code each keep their own record.
        release = app.read_bytes()
        for flags, env in ((['--dev'], None), (['--opt-level', '1'], None), ([], {'NEO_INLINE_BUDGET': '100'}), ([], {'NEO_FOLD': '0'})):
            variant = folder/'variant'
            assert build(source, variant, *flags, env=env)[:2] == ('miss', False), (flags, env)
            assert build(source, variant, *flags, env=env)[:2] == ('hit', True), (flags, env)
            assert run(variant, '7') == '73\n'
        assert build(source, app)[:2] == ('hit', True) and app.read_bytes() == release
        target = cross_target()
        if target:
            cross = folder/'cross'
            assert build(source, cross, '--target', target)[:2] == ('miss', False)
            assert build(source, cross, '--target', target)[:2] == ('hit', True) and cross.read_bytes() != release

        # A damaged cached binary is never published.
        cache_key = build(source, app)[2]['cache_key']
        cached = folder/'.neo-build'/(cache_key + '.bin')
        cached.write_bytes(b'not the binary')
        assert build(source, app)[:2] == ('miss', False) and run(app, '7') == '73\n'

        # Another clang on PATH, then the same one changed in place.
        tools = folder/'tools'; tools.mkdir()
        wrapper = tools/'clang'
        wrapper.write_text('#!/bin/sh\nexec ' + shutil.which('clang') + ' "$@"\n'); wrapper.chmod(0o755)
        path = {'PATH': str(tools) + os.pathsep + os.environ['PATH']}
        assert build(source, app, env=path)[1] is False
        assert build(source, app, env=path)[:2] == ('hit', True)
        wrapper.write_text(wrapper.read_text() + '# changed\n')
        assert build(source, app, env=path)[1] is False

        # Compiler sources change.
        compiler = folder/'compiler'
        for part in ('neoc', 'runtime', 'stdlib'): shutil.copytree(ROOT/part, compiler/part, ignore=shutil.ignore_patterns('__pycache__'))
        assert build(source, app, root=compiler)[:2] == ('miss', False)
        assert build(source, app, root=compiler)[:2] == ('hit', True)
        fold = compiler/'neoc/fold.py'; original = fold.read_text()
        fold.write_text(original + '# changed\n')
        assert build(source, app, root=compiler)[:2] == ('miss', False)
        fold.write_text(original)
        assert build(source, app, root=compiler)[:2] == ('hit', True) and run(app, '7') == '73\n'

        # `neo run` uses the same record.
        first = subprocess.run([sys.executable, '-m', 'neoc', 'run', str(source), '5'], cwd=ROOT, capture_output=True, text=True)
        second = subprocess.run([sys.executable, '-m', 'neoc', 'run', str(source), '5'], cwd=ROOT, capture_output=True, text=True)
        assert first.stdout == second.stdout == '53\n' and 'neo: build hit' in second.stderr, (first, second)

        # Package imports always take the full path.
        library = folder/'library'; package = folder/'package'
        for p in (library, package): (p/'src').mkdir(parents=True)
        (library/'neo.toml').write_text('[package]\nname="math"\nversion="1.2.3"\nentry="src/lib.neo"\n')
        (library/'src/lib.neo').write_text('fn answer() -> i64 = 42\n')
        (package/'neo.toml').write_text('[package]\nname="app"\nversion="0.1.0"\n[dependencies]\nmath={path="../library",version="1.2.3"}\n')
        (package/'src/main.neo').write_text('import "pkg:math" as math\nfn main() -> i64 = math::answer()\n')
        neo('pkg', 'lock', package)
        assert build(package/'src/main.neo', folder/'packaged')[:2] == ('miss', False)
        assert build(package/'src/main.neo', folder/'packaged')[:2] == ('hit', False)
        assert run(folder/'packaged') == '42\n'
    print('PASS quick rebuilds: hits match the full path; edits, import links, manifests, flags, targets, variables, '
          'clang, compiler sources and damaged binaries all rebuild; package imports take the full path')


if __name__ == '__main__':
    main()
