"""Build the native compiler and its seed runtime with Python neoc.

    python3 compiler/bootstrap.py -o .neo-build/bin
    ./neo build examples/hello.neo -o /tmp/neo-hello

Python prepares the initial executable. Native builds use runtime source by
default. The adjacent object supports explicit --seed-runtime comparisons.
"""

import argparse
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neoc import cli  # noqa: E402
from neoc.llvm import LLVMGen  # noqa: E402


RUNTIME_ROOTS = {
    'ax_runtime_init', 'ax_usage', 'ax_parse_i64', 'ax_print_i64',
    'ax_print_f64', 'ax_print_bytes', 'ax_trap', 'ax_precondition_failed', 'ax_exit', 'ax_heap_alloc', 'ax_free',
}


def bootstrap(destination):
    destination.mkdir(parents=True, exist_ok=True)
    triple = cli.target_triple()
    with TemporaryDirectory(prefix='.bootstrap-', dir=destination) as temporary:
        stage = Path(temporary)
        source = stage / 'runtime-seed.neo'
        source.write_text('fn main() -> unit = noop()\n', encoding='utf-8')
        program, hashes = cli.load(source, target=triple)
        _, report = cli.check(program, hashes)
        if not report['ok']:
            cli.emit_json(report)
            raise SystemExit(1)
        ir = stage / 'runtime.ll'
        ir.write_text(LLVMGen(program.fns, hashes, triple, literal_inline=False).program(
            runtime_roots=RUNTIME_ROOTS,
        ), encoding='utf-8')
        flags = ['-mno-outline-atomics'] if triple.startswith(('arm64-', 'aarch64-')) else []
        subprocess.run([
            'clang', f'--target={triple}', '-O2', '-Wno-override-module', '-ffunction-sections', '-fdata-sections',
            *flags, '-c', ir, '-o', stage / 'neo-runtime.o',
        ], check=True)
        (stage / 'neo-runtime.o.target').write_text(triple + '\n', encoding='utf-8')
        subprocess.run([
            sys.executable, '-m', 'neoc', 'build', ROOT / 'compiler/src/main.neo', '--dev',
            '--target', triple, '-o', stage / 'neoc',
        ], check=True, cwd=ROOT)
        for name in ('neo-runtime.o', 'neo-runtime.o.target', 'neoc'):
            (stage / name).replace(destination / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-o', '--output', required=True, type=Path)
    args = parser.parse_args()
    bootstrap(args.output.resolve())


if __name__ == '__main__':
    main()
