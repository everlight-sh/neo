"""Compare native neo fmt with the Python formatter on an isolated tree."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from neoc.formatter import formatted  # noqa: E402
from neoc.syntax import SyntaxError_  # noqa: E402

SAMPLES = {
    'a/nested.ax': '\tfn main () -> i64=1+2   # comment  \n\n\n',
    'a.neo': 'fn id<T>(x:T)->T=x ; keep this\nfn main()->i64=id::<i64>(-7)+9\n',
    'b file.neo': ' \t fn main () -> Arr u8 _ = "a  b\\n\\x2A"   \n',
    'multiline.neo': 'fn main()->Arr u8 _="a\nb"\n\n\n',
    'guard.neo': 'fn main()->i64=1 . . 2\n',
    'comments.neo': ' \t; a comment with "quote" and non-breaking space\xa0\n\n\n\nfn f() -> i64=3#end\n',
    'operators.neo': 'fn main()->i64=if !(2<3)||false then -7 else 1+ -2\n'
                     'fn g()->f64=1.4e-3+2.0E+4\n'
                     'fn f(x:i64)->i64=let z=arr(i in 0 .. 2) i in sum(i in 0..2) z [i]+x\n',
    'unicode.neo': 'fn café () -> i64=3\nfn main () -> i64=café ()\n',
    'clean-crlf.neo': 'fn main() -> i64 = 42\r\n',
    'dirty-crlf.neo': 'fn main()->i64=42\r\n',
    'legacy.ax': 'fn main()->i64=42\n',
    'node_modules/ignored.neo': 'fn main()->i64=1\n',
    'node_modules target/format.neo': 'fn main()->i64=7\n',
    'target/ignored.neo': 'fn main()->i64=2\n',
    '.neo-build/ignored.neo': 'fn main()->i64=3\n',
    '.axon-build/ignored.ax': 'fn main()->i64=4\n',
    '.axon/ignored.neo': 'fn main()->i64=5\n',
    '.kernel-build/ignored.neo': 'fn main()->i64=6\n',
    'notes.txt': 'fn main()->i64=42\n',
}
EXCLUDED = {'.neo-build', '.axon-build', '.axon', '.kernel-build', 'node_modules', 'target'}


def run(command, root, env):
    return subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=300)


def files(root):
    return {str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.rglob('*') if path.is_file()}


def content(root):
    return {path: data for path, (data, _) in files(root).items()}


def setup(root):
    for name, source in SAMPLES.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(source.encode())
    (root / 'linked.neo').symlink_to('a.neo')
    (root / 'linked-directory').symlink_to('a', target_is_directory=True)


def compare(native, reference, root, env):
    native_root = root / 'native'
    reference_root = root / 'reference'
    for project in (native_root, reference_root):
        setup(project)

    before = files(native_root)
    old = run([*reference, '--check'], reference_root, os.environ)
    new = run([*native, '--check'], native_root, env)
    assert old.returncode == new.returncode == 1 and old.stdout == new.stdout and not new.stderr, (old, new)
    assert files(native_root) == before, 'check changed file contents or mtimes'
    assert 'a/nested.ax\na.neo\n' in new.stdout
    assert all(not EXCLUDED.intersection(Path(path).parts) for path in new.stdout.splitlines())

    old = run(reference, reference_root, os.environ)
    new = run(native, native_root, env)
    assert old.returncode == new.returncode == 0 and old.stdout == new.stdout and not new.stderr, (old, new)
    assert content(native_root) == content(reference_root)
    assert (native_root / 'linked.neo').is_symlink()
    assert (native_root / 'clean-crlf.neo').read_bytes() == SAMPLES['clean-crlf.neo'].encode()
    assert (native_root / 'multiline.neo').read_bytes() == SAMPLES['multiline.neo'].encode()
    assert (native_root / 'guard.neo').read_bytes() == SAMPLES['guard.neo'].encode()
    for check in ([], ['--check']):
        state = files(native_root)
        again = run([*native, *check], native_root, env)
        assert (again.returncode, again.stdout, again.stderr) == (0, '', ''), again
        assert files(native_root) == state, 'clean files were rewritten'

    for project in (native_root, reference_root):
        for path in ('notes.txt', 'extra.neo', '-dash.neo'):
            (project / path).write_text('fn main ()->i64=  42\n')
    for options in (['--check'], []):
        paths = [*options, './notes.txt', 'extra.neo', '--', '-dash.neo']
        old = run([*reference, *paths], reference_root, os.environ)
        new = run([*native, *paths], native_root, env)
        assert (old.returncode, old.stdout) == (new.returncode, new.stdout) and not new.stderr, (old, new)
        assert content(native_root) == content(reference_root)

    bad = native_root / 'bad.neo'
    bad.write_text('fn main() -> i64 = @\n')
    state = files(native_root)
    for options in (['--check'], []):
        rejected = run([*native, *options, 'bad.neo'], native_root, env)
        assert rejected.returncode == 1 and 'bad.neo:1:' in rejected.stderr and not rejected.stdout, rejected
        assert files(native_root) == state


def compare_corpus(native, root, env):
    expected = {}
    for directory in ('compiler/src', 'runtime', 'stdlib', 'tests/fixtures', 'examples'):
        for path in (ROOT / directory).rglob('*'):
            if path.suffix not in ('.neo', '.ax') or not path.is_file() or EXCLUDED.intersection(path.parts):
                continue
            try:
                source = path.read_text()
                result = formatted(source)
            except (SyntaxError_, ValueError):
                continue
            relative = path.relative_to(ROOT)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
            expected[str(relative)] = result.encode() if result != source else path.read_bytes()
    result = run(native, root, env)
    assert result.returncode == 0, result
    actual = content(root)
    differences = sorted(path for path, data in expected.items() if actual.get(path) != data)
    assert not differences, differences
    print(f'{len(expected)} repository sources matched the Python formatter')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('neoc', type=Path)
    parser.add_argument('--corpus', action='store_true')
    args = parser.parse_args()
    with TemporaryDirectory(prefix='neo-fmt-diff-') as temporary:
        root = Path(temporary)
        tools = root / 'empty-path'
        tools.mkdir()
        env = {'PATH': str(tools), 'NEOC': str(args.neoc.resolve())}
        native = [ROOT / 'neo', 'fmt']
        compare(native, [ROOT / 'neoc.sh', 'fmt'], root, env)
        if args.corpus:
            corpus = root / 'corpus'
            corpus.mkdir()
            compare_corpus(native, corpus, env)
    print('Native formatting and --check matched the reference with an empty PATH')


if __name__ == '__main__':
    main()
