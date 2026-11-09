"""Compare real Cancellation behavior using the native compiler and Python neoc."""

import argparse
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from llvm_differential import ROOT, native_environment, run

sys.path.insert(0, str(ROOT))
from compiler.bootstrap import RUNTIME_ROOTS  # noqa: E402
from neoc import cli  # noqa: E402
from neoc.llvm import LLVMGen  # noqa: E402


RUNTIME_CALLS = (
    ('rt_mmap', 'size:i64', 'size', 'i64'),
    ('rt_handle_new', 'address:i64, kind:i64', 'address, kind', 'i64'),
    ('rt_handle_fd', 'token:i64, kind:i64', 'token, kind', 'i64'),
    ('rt_handle_drop', 'token:i64, kind:i64', 'token, kind', 'unit'),
    ('rt_handle_live', '', '', 'i64'),
)

SOURCE = '''import "std:cancel"
effect fn exercise() -> i64 =
  using original=new_cancellation() in using owner=original in
  let before=is_cancelled(owner) in
  let stopped=cancel(owner) in let again=cancel(owner) in
  if !before && is_cancelled(owner) && rt_handle_live()==1 then 1 else -1
effect fn main() -> i64 =
  let before=rt_handle_live() in let result=exercise() in
  if before==0 && result==1 && rt_handle_live()==0 then 42 else 0
'''


def test_runtime(root, triple, clang):
    # Bridge only these calls into the real platform/runtime object. This
    # isolates cancellation's ownership checks in an explicit seed build.
    source = root / 'runtime-bridge.neo'
    source.write_text('fn main() -> unit = noop()\n' + ''.join(
        f'export effect fn neo_test_{name}({params}) -> {result} = {name}({args})\n'
        for name, params, args, result in RUNTIME_CALLS
    ), encoding='utf-8')
    program, hashes = cli.load(source, target=triple)
    _, report = cli.check(program, hashes)
    assert report['ok'], report
    ir = root / 'runtime.ll'
    ir.write_text(LLVMGen(program.fns, hashes, triple, literal_inline=False).program(
        runtime_roots=RUNTIME_ROOTS,
    ), encoding='utf-8')
    runtime = root / 'runtime.o'
    flags = ['-mno-outline-atomics'] if triple.startswith(('arm64-', 'aarch64-')) else []
    compiled = run([clang, f'--target={triple}', '-O2', '-Wno-override-module', *flags, '-c', ir, '-o', runtime])
    assert compiled.returncode == 0, compiled
    runtime.with_suffix('.o.target').write_text(triple + '\n', encoding='utf-8')
    return runtime


def compare(neoc, root):
    environment = native_environment(root)
    triple = neoc.with_name('neo-runtime.o.target').read_text(encoding='utf-8').strip()
    runtime = test_runtime(root, triple, environment['NEO_CLANG'])
    stdlib = root / 'stdlib'
    stdlib.mkdir()
    for name in ('cancel.neo', 'errors.neo'):
        shutil.copyfile(ROOT / 'stdlib' / name, stdlib / name)
    (stdlib / 'time.neo').write_text('import "std:errors"\n' + ''.join(
        f'extern fn neo_test_{name}({params}) -> {result}\n'
        f'effect(process) fn {name}({params}) -> {result} = neo_test_{name}({args})\n'
        for name, params, args, result in RUNTIME_CALLS
    ), encoding='utf-8')
    source = root / 'cancellation.neo'
    source.write_text(SOURCE, encoding='utf-8')
    reference = root / 'reference'
    native = root / 'native'
    python_build = run([ROOT / 'neoc.sh', 'build', source, '--dev', '-o', reference])
    assert python_build.returncode == 0, python_build
    native_build = run([neoc, 'build', root, source, '-o', native, '--seed-runtime'],
                       env={**environment, 'NEO_RUNTIME': str(runtime)})
    assert native_build.returncode == 0, native_build
    for binary in (reference, native):
        result = run([binary])
        assert (result.returncode, result.stdout, result.stderr) == (0, b'42\n', b''), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('neoc', type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix='neo-cancellation-diff-') as temporary:
        compare(args.neoc.resolve(), Path(temporary).resolve())
    print('Cancellation ownership, cancellation, and runtime handle cleanup match Python')


if __name__ == '__main__':
    main()
