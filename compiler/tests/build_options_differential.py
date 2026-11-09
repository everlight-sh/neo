"""Compare native experimental builds, optimizer reports, and prepared objects with Python."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]


def build(driver, environment, source, binary, *options, success=True):
    result = subprocess.run([driver, 'build', source, '-o', binary, '--dev', *options],
                            cwd=ROOT, env=environment, capture_output=True, timeout=600)
    assert (result.returncode == 0) == success, (driver, source, result.stdout[-3000:], result.stderr[-3000:])
    return json.loads(result.stdout) if '--report' in options else None


def execute(binary, *args):
    return subprocess.check_output([binary, *args], env={'PATH': '/nonexistent'}, timeout=30)


def report(drivers, root):
    source = root / 'report.neo'
    source.write_text('fn main(n:i64)->i64=2*n+1\n')
    for driver, environment in drivers:
        for level in ('0', '2'):
            binary = root / 'report-bin'
            result = build(driver, environment, source, binary, '--opt-level', level, '--report')
            assert result['ok'] and result['backend'] == 'llvm-ir'
            assert result['optimization']['level'] == int(level)
            assert result['binary_sha256'] == hashlib.sha256(binary.read_bytes()).hexdigest()
            assert result['sources'][str(source)] == hashlib.sha256(source.read_bytes()).hexdigest()
            assert all(result['build_stages'][key] > 0 for key in ('parse_seconds', 'check_seconds', 'lower_seconds'))
            assert all(result['build'][key] > 0 for key in ('compile_seconds', 'link_seconds'))
            if driver == drivers[0][0]:
                assert isinstance(result['optimization']['llvm_passes'], dict)
            assert execute(binary, '21') == b'43\n'
    print('Native and reference reports matched output, source and binary digests, and build stage schema.', flush=True)


def experimental(drivers, root):
    programs = (
        ('bounds', 'fn main(n:i64)->i64=i64("abc"[n])', '1', b'98\n'),
        ('division', 'fn main(n:i64)->i64=42/n', '2', b'21\n'),
        ('precondition', 'fn f(n:i64{n>0})->i64=n\nfn main(n:i64)->i64=f(n)', '9', b'9\n'),
    )
    for name, text, arg, expected in programs:
        source, binary = root / f'{name}.neo', root / name
        source.write_text(text + '\n')
        for driver, environment in drivers:
            build(driver, environment, source, binary, success=False)
            build(driver, environment, source, binary, '--allow-unproven')
            assert execute(binary, arg) == expected
    rejected = (
        'fn main()->i64=true',
        'import "std:io"\neffect(net) fn main()->i64=print_out("bad").value',
        'resource type Item={count:i64} drop dispose\neffect fn dispose(move item:Item)->unit=noop()\n'
        'effect fn main()->i64=using item=Item {count=1} in let done=dispose(item) in item.count',
    )
    for text in rejected:
        source = root / 'invalid.neo'
        source.write_text(text + '\n')
        for driver, environment in drivers:
            build(driver, environment, source, root / 'invalid', '--allow-unproven', success=False)
    print('Both compilers accepted experimental proof failures and still rejected type, effect, and ownership errors.', flush=True)


def prepared(drivers, root):
    for index, (driver, environment) in enumerate(drivers):
        base = root / f'cache-{index}'
        base.mkdir()
        dependency = base / 'dep.neo'
        dependency.write_text('fn inc(n:i64)->i64=n+1\n')
        one, two = base / 'one.neo', base / 'two.neo'
        one.write_text('import "dep.neo"\nfn main(n:i64)->i64=inc(n)\n')
        two.write_text('import "dep.neo"\nfn main(n:i64)->i64=inc(n)+delta()\n'
                       'fn delta()->i64=10\nfn marker()->Arr u8 _="APPLICATION_SENTINEL"\n')

        def checked(source, expected):
            # The reference also has a whole-program cache. Each iteration
            # exercises its prepared objects independently of that cache.
            shutil.rmtree(base / '.neo-build', ignore_errors=True)
            binary = source.with_suffix('.out')
            result = build(driver, environment, source, binary, '--report', '--library-cache',
                           base / 'objects', '--library-root', dependency)
            assert execute(binary, '41') == expected
            return result['native_libraries'], result['binary_sha256']

        first, cold = checked(one, b'42\n')
        again, warm = checked(one, b'42\n')
        across, _ = checked(two, b'52\n')
        assert cold == warm and first['cache'] == 'miss' and again['cache'] == across['cache'] == 'hit'
        assert first['key'] == across['key']
        artifacts = Path(first['directory'])
        for name in ('library.ll', 'library.o'):
            assert b'APPLICATION_SENTINEL' not in (artifacts / name).read_bytes()
        (artifacts / 'library.o').write_bytes(b'corrupt')
        repaired, _ = checked(two, b'52\n')
        assert repaired['cache'] == 'miss' and repaired['key'] == first['key']
        dependency.write_text('fn inc(n:i64)->i64=n+2\n')
        changed, _ = checked(two, b'53\n')
        assert changed['cache'] == 'miss' and changed['key'] != first['key']
    print('Both prepared caches reused dependencies across apps, repaired corruption, and invalidated changed sources.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('neoc', type=Path)
    parser.add_argument('--native-root', type=Path, default=ROOT)
    parser.add_argument('--case', choices=('report', 'experimental', 'prepared'), action='append')
    args = parser.parse_args()
    with TemporaryDirectory(prefix='neo-build-options-') as tmp:
        root = Path(tmp)
        tools = root / 'toolchain'
        tools.mkdir()
        for name in ('clang', 'ld', 'ld.lld'):
            path = shutil.which(name)
            if path:
                (tools / name).symlink_to(path)
        drivers = [(args.neoc.resolve(), {'PATH': str(tools), 'NEO_ROOT': str(args.native_root.resolve()),
                                          'NEO_OPT_LEVEL': '0'}),
                   (ROOT / 'neoc.sh', {**os.environ, 'NEO_OPT_LEVEL': '0', 'NEO_INLINE': '0', 'NEO_FOLD': '0'})]
        for name in args.case or ('report', 'experimental', 'prepared'):
            globals()[name](drivers, root)


if __name__ == '__main__':
    main()
