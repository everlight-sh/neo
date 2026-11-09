"""Compare native and Python package imports in local and vendored builds."""

import argparse
import difflib
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import modules_dump

ROOT = Path(__file__).resolve().parents[2]
MAIN = '''import "pkg:common" as math
import "pkg:common/bonus" as bonus
import "pkg:bridge" as bridge
import "pkg:bridge/more/delta" as deep
import "local.neo" as local
fn main() -> i64 = math::value()+bonus::amount()+bridge::joined()+deep::offset()+local::value()
'''


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def project(root):
    app = root / 'app'
    write(app / 'neo.toml', '''[package]
name="app"
version="0.1.0"
entry="src/main.neo"
[dependencies]
common={path="../modern",version="1.0.0"}
bridge={path="../bridge",version="2.0.0"}
''')
    write(app / 'src/main.neo', MAIN)
    write(app / 'src/local.neo', 'import "pkg:bridge" as b\nfn value() -> i64 = b::joined()+1\n')
    write(root / 'modern/neo.toml', '[package]\nname="modern"\nversion="1.0.0"\n')
    write(root / 'modern/src/lib.neo', 'fn value() -> i64 = 7\n')
    write(root / 'modern/src/bonus.neo', 'fn amount() -> i64 = 5\n')
    write(root / 'modern/src/bonus.ax', 'fn amount() -> i64 = 99\n')
    write(root / 'bridge/neo.toml', '''[package]
name="bridge"
version="2.0.0"
entry="api/public.neo"
[dependencies.common]
path="../legacy"
version="1.2.3"
''')
    write(root / 'bridge/api/public.neo', 'import "pkg:common" as c\nfn joined() -> i64 = c::value()+2\n')
    write(root / 'bridge/src/more/delta.ax', 'fn offset() -> i64 = 3\n')
    write(root / 'legacy/axon.toml', '[package]\nname="legacy"\nversion="1.2.3"\n')
    write(root / 'legacy/src/lib.ax', 'fn value() -> i64 = 11\n')
    return app


class Comparison:
    def __init__(self, root, neoc):
        tools = root / 'toolchain'
        tools.mkdir()
        for tool in ('clang', 'ld', 'ld.lld', 'as'):
            path = shutil.which(tool)
            if path:
                (tools / tool).symlink_to(path)
        self.env = {'NEOC': str(neoc), 'NEO_RUNTIME': str(root / 'missing-runtime.o'), 'PATH': str(tools)}

    def run(self, cwd, command, *args, native=True):
        launcher = 'neo' if native else 'neoc.sh'
        return subprocess.run([ROOT / launcher, command, *args], cwd=cwd,
                              env=self.env if native else os.environ, capture_output=True,
                              text=True, timeout=300)

    def native(self, cwd, command, *args):
        result = self.run(cwd, command, *args)
        assert result.returncode == 0 and not result.stderr, result
        return result.stdout

    def modules(self, source, error=None):
        expected = modules_dump.dump(source)
        actual = self.native(source.parent, 'modules', source, '--target', modules_dump.DEFAULT_TARGET)
        if error:
            assert expected.startswith('(error ') and error in expected, expected
        assert actual == expected, '\n'.join(difflib.unified_diff(
            expected.splitlines(), actual.splitlines(), 'Python', 'Neo', n=2))[:5000]

    def build(self, cwd, *args, expected, native_args=None, dev=True):
        profile = ('--dev',) if dev else ()
        for native in (True, False):
            output = cwd / ('native-bin' if native else 'python-bin')
            build_args = native_args if native and native_args is not None else args
            built = self.run(cwd, 'build', *build_args, *profile, '-o', output, native=native)
            assert built.returncode == 0, built
            result = subprocess.run([output], cwd=cwd, capture_output=True, text=True, timeout=10)
            assert (result.returncode, result.stdout, result.stderr) == (0, expected, ''), result

    def build_error(self, cwd, *args, error):
        for native in (True, False):
            output = cwd / 'must-not-build'
            built = self.run(cwd, 'build', *args, '--dev', '-o', output, native=native)
            assert built.returncode == 1 and error in built.stdout + built.stderr, built
            assert not output.exists()


def compare(root, neoc):
    commands = Comparison(root, neoc)
    app = project(root)
    entry = app / 'src/main.neo'
    commands.modules(entry, 'missing or invalid neo.lock')
    commands.native(app, 'pkg', 'lock')
    commands.modules(entry)
    commands.native(app, 'pkg', 'vendor')
    for dependency in ('modern', 'bridge', 'legacy'):
        shutil.rmtree(root / dependency)
    commands.modules(entry)
    commands.build(app, expected='42\n', dev=False)
    assert commands.native(app, 'run', '--dev') == '42\n'

    # Generated mains may use regular imports into a locked source project.
    generated = root / 'generated/main.neo'
    write(generated, 'import "../app/src/local.neo" as local\nfn main() -> i64 = local::value()\n')
    commands.build_error(root, generated, error='package requires an ancestor neo.toml')
    commands.build(root, generated, '--package-root', app, expected='14\n',
                   native_args=(generated, '--package-root=' + str(app)))

    for name, error in (
        ('pkg:unknown', 'undeclared package dependency unknown'),
        ('pkg:', 'invalid package import pkg:'),
        ('pkg:/common', 'invalid package import pkg:/common'),
        ('pkg:common/../lib', 'invalid package import pkg:common/../lib'),
        ('pkg:common/.', 'invalid package import pkg:common/.'),
        ('pkg:common//bonus', 'invalid package import pkg:common//bonus'),
        ('pkg:common/café', 'invalid package import pkg:common/café'),
        ('pkg:common/missing', 'cannot read '),
    ):
        write(entry, f'import "{name}"\nfn main() -> i64 = 0\n')
        commands.modules(entry, error)

    write(root / 'other/neo.toml', '[package]\nname="other"\nversion="1.0.0"\n')
    write(root / 'other/lib.neo', 'import "pkg:common" as c\nfn value() -> i64 = c::value()\n')
    write(entry, 'import "../../other/lib.neo" as outside\nfn main() -> i64 = outside::value()\n')
    commands.modules(entry, 'source package is absent from neo.lock')

    write(entry, MAIN)
    legacy = next((app / '.neo/vendor').glob('legacy-*/src/lib.ax'))
    write(legacy, 'fn value() -> i64 = 123\n')
    commands.build_error(app, error='locked source changed: legacy@1.2.3')


def escape(root, neoc):
    commands = Comparison(root, neoc)
    app = root / 'app'
    write(app / 'neo.toml', '''[package]
name="app"
version="0.1.0"
[dependencies]
dep={path="../dep",version="1.0.0"}
''')
    write(app / 'src/main.neo', 'import "pkg:dep" as d\nfn main() -> i64 = d::value()\n')
    write(root / 'dep/neo.toml', '[package]\nname="dep"\nversion="1.0.0"\nentry="../outside.neo"\n')
    commands.native(app, 'pkg', 'lock')
    commands.native(app, 'pkg', 'vendor')
    shutil.rmtree(root / 'dep')
    write(app / '.neo/vendor/outside.neo', 'fn value() -> i64 = 42\n')
    commands.build_error(app, error='package import escapes source root')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('neoc', type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix='neo-package-import-') as temporary:
        root = Path(temporary)
        for name, test in (('compare', compare), ('escape', escape)):
            case = root / name
            case.mkdir()
            test(case, args.neoc.resolve())
    print('Native package imports matched Python module graphs, offline builds, and error diagnostics')


if __name__ == '__main__':
    main()
