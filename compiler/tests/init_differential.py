"""Compare native and Python project initialization on an isolated tree."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]


def run(command, root, env, **options):
    return subprocess.run(command, cwd=root, env=env, capture_output=True, text=True,
                          timeout=180, umask=0o027, **options)


def snapshot(root):
    entries = {'': ('directory', stat.S_IMODE(root.stat().st_mode))}
    for path in sorted(root.rglob('*')):
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            entry = ('symlink', os.readlink(path))
        elif path.is_dir():
            entry = ('directory', mode)
        else:
            entry = ('file', mode, path.read_bytes())
        entries[str(path.relative_to(root))] = entry
    return entries


def check_project(native, reference, native_root, reference_root, env, args, path):
    old = run([*reference, *args], reference_root, os.environ)
    new = run([*native, *args], native_root, env)
    assert (old.returncode, new.returncode, new.stderr) == (0, 0, ''), (old, new)
    assert old.stdout == f'Created {(reference_root / path).resolve()}\n', old
    assert new.stdout == f'Created {(native_root / path).resolve()}\n', new
    assert snapshot(native_root) == snapshot(reference_root)


def short_file_limit():
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (50, 50))


def compare(neoc, root):
    no_tools = root / 'empty-path'
    native_root = root / 'native'
    reference_root = root / 'reference'
    for path in (no_tools, native_root, reference_root):
        path.mkdir()
    env = {'PATH': str(no_tools), 'NEOC': str(neoc)}
    native = [ROOT / 'neo', 'init']
    reference = [ROOT / 'neoc.sh', 'init']

    for project in (native_root, reference_root):
        (project / '42 Café+🦊').mkdir()
        (project / 'Actual Target').mkdir()
        (project / 'alias').symlink_to('Actual Target', target_is_directory=True)
    for args, path in (
        (['Sample_app-2'], 'Sample_app-2'),
        (['./nested//more/Example/'], 'nested/more/Example'),
        (['42 Café+🦊'], '42 Café+🦊'),
        (['alias'], 'alias'),
        (['--', '-dash'], '-dash'),
    ):
        check_project(native, reference, native_root, reference_root, env, args, path)

    for project in (native_root, reference_root):
        (project / 'cwd').mkdir()
        (project / 'occupied').mkdir()
        (project / 'occupied/.keep').write_text('keep me')
        (project / 'regular').write_text('keep me too')
        (project / 'dangling').symlink_to('missing')
    check_project(native, reference, native_root / 'cwd', reference_root / 'cwd', env, ['.'], '.')
    for name in ('Sample_app-2', 'occupied', 'regular', 'dangling'):
        before = snapshot(native_root)
        old = run([*reference, name], reference_root, os.environ)
        new = run([*native, name], native_root, env)
        assert old.returncode == new.returncode == 1 and not new.stdout, (old, new)
        if name in ('Sample_app-2', 'occupied'):
            assert 'init requires an empty directory' in new.stderr, new
        assert snapshot(native_root) == before

    rollback = run([*native, 'rollback'], native_root, env, preexec_fn=short_file_limit)
    assert rollback.returncode == 1 and 'neo.toml' in rollback.stderr and 'write failed' in rollback.stderr, rollback
    assert not (native_root / 'rollback').exists()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run([*native, 'race'], native_root, env), range(2)))
    assert sorted(r.returncode for r in results) == [0, 1], results
    expected = run([*reference, 'race'], reference_root, os.environ)
    assert expected.returncode == 0, expected
    assert snapshot(native_root) == snapshot(reference_root)

    for args in ([], ['first', 'second']):
        result = run([*native, *args], native_root, env)
        assert result.returncode == 2 and 'neo init PATH' in result.stderr, result

    toolchain = root / 'toolchain'
    toolchain.mkdir()
    for name in ('clang', 'ld', 'ld.lld', 'as'):
        tool = shutil.which(name)
        if tool:
            (toolchain / name).symlink_to(tool)
    greeting = run([ROOT / 'neo', 'run'], native_root / 'Sample_app-2', {**env, 'PATH': str(toolchain)})
    assert (greeting.returncode, greeting.stdout, greeting.stderr) == (0, 'Hello, Neo!\n', ''), greeting


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('neoc', type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix='neo-init-diff-') as temporary:
        compare(args.neoc.resolve(), Path(temporary))
    print('Native init matched the reference project files, modes and resolved paths; the starter ran without Python')


if __name__ == '__main__':
    main()
