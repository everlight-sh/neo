"""Compare native and Python package commands on mirrored project trees."""

import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
APP = '[package]\nname = "app"\nversion = "0.1.0"\nentry = "src/main.neo"\n'
CORE = '[package]\nname = "core"\nversion = "1.0.0-dev.2"\n'
UTIL = 'package = { name = "utils", version = "2.5.0", entry = "src/lib.ax" }\n'
CORE_SPEC = 'path = "../Core é🦊"\nversion = "1.0.0-dev.2"\n'
MAIN = 'import "pkg:helper" as h\nfn main() -> i64 = h::answer()\n'


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode() if isinstance(content, str) else content)


def setup(base):
    app = base / 'app'
    core = base / 'Core é🦊'
    utils = base / 'utils'
    write(app / 'neo.toml', APP + '[dependencies]\n'
          'helper = { path = "../utils", version = "2.5.0" }\n'
          '[dependencies.core]\n' + CORE_SPEC)
    write(app / 'src/main.neo', MAIN)
    write(core / 'neo.toml', CORE)
    write(core / 'src/lib.neo', 'fn base_value() -> i64 = 40\n')
    write(core / 'a/x.neo', b'\xff\x00' * 65537)
    write(core / 'a.neo', 'fn other() -> i64 = 1\n')
    write(core / 'nested/neo.toml', 'ignored nested manifest')
    write(core / '.neo', 'ignored suffix-only filename')
    write(core / 'target/ignore.neo', 'ignored directory')
    (core / 'node_modules').symlink_to('target', target_is_directory=True)
    write(utils / 'axon.toml', UTIL + 'dependencies.core.path = "../core-link"\n'
          'dependencies.core.version = "1.0.0-dev.2"\n')
    write(utils / 'src/lib.ax', 'import "pkg:core" as c\nfn answer() -> i64 = c::base_value()+2\n')
    (base / 'core-link').symlink_to(core.name, target_is_directory=True)
    return app


def short_file_limit():
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (2048, 2048))


def snapshot(path):
    return {str(child.relative_to(path)): (stat.S_IMODE(child.stat().st_mode),
                                           child.read_bytes() if child.is_file() else None)
            for child in sorted(path.rglob('*'))}


class Pair:
    def __init__(self, root, neoc):
        self.python = setup(root / 'python')
        self.native = setup(root / 'native')
        empty_path = root / 'empty-path'
        empty_path.mkdir()
        self.env = {'PATH': str(empty_path), 'NEOC': str(neoc)}

    def run(self, launcher, action, root, env, *args, cwd=None, **options):
        return subprocess.run([ROOT / launcher, 'pkg', action, *args], cwd=cwd or root, env=env,
                              capture_output=True, text=True, timeout=300, umask=0o027, **options)

    def both(self, action, *args, error=None, cwd=None):
        old = self.run('neoc.sh', action, self.python, os.environ, *args,
                       cwd=self.python / cwd if cwd else None)
        new = self.run('neo', action, self.native, self.env, *args,
                       cwd=self.native / cwd if cwd else None)
        if error is None:
            assert (old.returncode, new.returncode, new.stdout, new.stderr) == (0, 0, old.stdout, ''), (old, new)
        else:
            assert old.returncode == new.returncode == 1, (old, new)
            assert error in old.stdout + old.stderr and error in new.stderr, (old, new)
        return new

    def each(self, callback):
        for app in (self.python, self.native):
            callback(app)


def compare(pair):
    pair.both('verify', error='missing or invalid neo.lock')
    lock = pair.both('lock', 'src/main.neo', cwd='src/..')
    assert json.loads(lock.stdout)['packages'] == 3
    old = pair.python / 'neo.lock'
    new = pair.native / 'neo.lock'
    initial = old.read_bytes()
    assert new.read_bytes() == initial
    assert stat.S_IMODE(old.stat().st_mode) == stat.S_IMODE(new.stat().st_mode) == 0o640
    pair.both('lock')
    assert new.read_bytes() == initial
    # Exchange the two lockfiles explicitly before verifying and vendoring.
    old.write_bytes(new.read_bytes())
    new.write_bytes(initial)
    pair.both('verify', '..', cwd='src')

    pair.each(lambda app: write(app / 'src/main.neo', '; root sources may change\n'))
    pair.both('verify')
    pair.each(lambda app: write(app / 'neo.toml', (app / 'neo.toml').read_text() + 'note = "only lock checks extra fields"\n'))
    pair.both('verify')
    pair.both('lock', error='requires only path and exact version')
    pair.each(lambda app: write(app / 'neo.toml', (app / 'neo.toml').read_text().split('note =')[0]))
    pair.each(lambda app: write(app.parent / 'Core é🦊/a.neo', 'changed'))
    pair.both('verify', error='locked source changed')
    pair.both('vendor', error='locked source changed')
    assert old.read_bytes() == new.read_bytes() == initial
    assert not (pair.native / '.neo').exists()
    pair.each(lambda app: write(app.parent / 'Core é🦊/a.neo', 'fn other() -> i64 = 1\n'))

    for value, diagnostic in (
        (b'{', 'missing or invalid neo.lock'),
        (b'{"format": 7}', 'unsupported package lock format'),
        (initial.replace(b'"sha256": "', b'"sha256": "X', 1),
         'invalid locked source hash'),
        (initial.replace(b'"path": "."', b'"path": "../utils"'), 'locked root must be the current project'),
    ):
        pair.each(lambda app: (app / 'neo.lock').write_bytes(value))
        pair.both('verify', error=diagnostic)
    pair.each(lambda app: (app / 'neo.lock').write_bytes(initial))

    def foreign_lock(app):
        file = app / 'neo.lock'
        value = json.loads(file.read_bytes())
        value['extra'] = {'z': ['quote"\t', '🚀'], 'a': {}}
        value['packages']['utils@2.5.0']['extra'] = True
        file.write_text(json.dumps(value, ensure_ascii=False))
    pair.each(foreign_lock)
    foreign = new.read_bytes()
    failed = pair.run('neo', 'vendor', pair.native, pair.env, preexec_fn=short_file_limit)
    assert failed.returncode == 1 and 'write failed' in failed.stderr, failed
    assert new.read_bytes() == foreign and not list((pair.native / '.neo/vendor').iterdir())
    pair.both('vendor')
    vendored = new.read_bytes()
    assert vendored == old.read_bytes()
    assert snapshot(pair.native / '.neo/vendor') == snapshot(pair.python / '.neo/vendor')
    for path in ('utils', 'Core é🦊'):
        pair.each(lambda app: shutil.rmtree(app.parent / path))
    pair.both('verify')
    pair.both('vendor')
    assert new.read_bytes() == old.read_bytes() == vendored
    write(pair.native / 'src/main.neo', MAIN)
    checked = subprocess.run([ROOT / 'neoc.sh', 'check', 'src/main.neo'], cwd=pair.native,
                             capture_output=True, text=True, timeout=300)
    assert checked.returncode == 0, checked
    pair.each(lambda app: write(next((app / '.neo/vendor').glob('core-*/a.neo')), 'tampered'))
    pair.both('verify', error='locked source changed')


def errors(pair):
    core = lambda app: app.parent / 'Core é🦊'
    for transform, diagnostic in (
        (lambda app: write(core(app) / 'neo.toml', CORE.replace('1.0.0-dev.2', '1.1.0')), 'version mismatch'),
        (lambda app: write(core(app) / 'neo.toml', CORE + '[dependencies.app]\npath = "../app"\nversion = "0.1.0"\n'),
         'cyclic package dependencies'),
        (lambda app: write(core(app) / 'neo.toml', CORE.replace('"core"', '42')), 'invalid package name'),
    ):
        pair.each(transform)
        pair.both('lock', error=diagnostic)
    pair.each(lambda app: write(core(app) / 'neo.toml', CORE))
    pair.each(lambda app: (core(app) / 'alias.txt').symlink_to('a.neo'))
    pair.both('lock', error='package symlinks are not supported')
    pair.each(lambda app: (core(app) / 'alias.txt').unlink())

    # A second canonical source root with the same identity cannot enter the graph.
    pair.each(lambda app: shutil.copytree(core(app), app.parent / 'duplicate', symlinks=True))
    pair.each(lambda app: write(app / 'neo.toml', (app / 'neo.toml').read_text() +
                                '[dependencies.duplicate]\npath="../duplicate"\nversion="1.0.0-dev.2"\n'))
    pair.both('lock', error='multiple source roots')
    pair.each(lambda app: write(app / 'neo.toml', (app / 'neo.toml').read_text().split('[dependencies.duplicate]')[0]))

    # Keep the pre-existing legacy lock name when the canonical name is absent.
    pair.each(lambda app: (app / 'neo.toml').rename(app / 'axon.toml'))
    pair.each(lambda app: write(app / 'axon.lock', '{}'))
    pair.both('lock')
    assert not (pair.native / 'neo.lock').exists()
    old = pair.python / 'axon.lock'
    new = pair.native / 'axon.lock'
    assert old.read_bytes() == new.read_bytes()
    data = json.loads(new.read_bytes())
    core_item = data['packages']['core@1.0.0-dev.2']
    vendor_path = '.neo/vendor/core-1.0.0-dev.2-' + core_item['sha256'][:12]
    pair.each(lambda app: write(app / vendor_path / 'extra.neo', 'wrong hash'))
    before = new.read_bytes()
    pair.both('vendor', error='existing vendor source changed')
    assert old.read_bytes() == new.read_bytes() == before
    assert not list((pair.native / '.neo/vendor').glob('.stage-*'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('neoc', type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix='neo-pkg-diff-') as temporary:
        root = Path(temporary)
        compare(Pair(root / 'compare', args.neoc.resolve()))
        errors(Pair(root / 'errors', args.neoc.resolve()))
    print('Native package commands matched Python lock bytes, vendor trees and rejection cases with Python off PATH')


if __name__ == '__main__':
    main()
