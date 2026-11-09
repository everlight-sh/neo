#!/usr/bin/env python3
"""Where a cold Neo build spends its time, stage by stage.

usage: breakdown.py OUT.json

One cold build per (tree, profile, program) with --report gives the compiler's
own stages: parse, check (of which proving obligations), AST optimization,
lowering to LLVM IR, clang compile, link. The IR is then compiled once more
with -ftime-report, which splits clang's compile into its optimizer and its
code generator. Trees older than the compile/link split report one
llvm_seconds for both.

Environment: NEO_TREES and NEO_DEV as for run.py, ONLY (program names).
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import NEO, TREES, E  # noqa: E402

SECTION = re.compile(r'===-+===\n\s*(.+?)\n===-+===\n\s*Total Execution Time: [\d.]+ seconds \(([\d.]+) wall clock\)(.*?)(?====-|\Z)', re.S)


def clang_split(report):
    """Optimizer and code-generator wall seconds of the build's own IR."""
    level = report['optimization']['level']
    target = subprocess.check_output(['clang', '-print-target-triple'], text=True).strip()
    flags = ['--target=' + target, f'-O{level}', '-ffunction-sections', '-fdata-sections']
    if target.startswith('x86_64'): flags.append('-falign-loops=32')
    r = subprocess.run(['clang', *flags, '-c', report['ir'], '-o', os.devnull, '-ftime-report'], capture_output=True, text=True)
    split = {'optimizer_seconds': 0.0, 'codegen_seconds': 0.0}
    for title, wall, body in SECTION.findall(r.stderr):
        if 'Pass execution timing report' not in title: continue
        kind = 'codegen_seconds' if 'DAG->DAG' in body or 'Instruction Selection' in body else 'optimizer_seconds'
        split[kind] += float(wall)
    return {k: round(v, 3) for k, v in split.items()}


def main():
    only = set(filter(None, E('ONLY', '').split(',')))
    dev = set(filter(None, E('NEO_DEV', '').split(',')))
    rows = []
    for program, path in NEO.items():
        if only and program not in only: continue
        for label, tree in TREES:
            for profile in ([], ['--dev']) if label in dev else ([],):
                started = time.perf_counter()
                r = subprocess.run(['./neoc.sh', 'build', path, '-o', '/tmp/breakdown-bin', '--report', '--no-cache', *profile],
                                   cwd=tree, capture_output=True, text=True)
                wall = time.perf_counter() - started
                if r.returncode != 0: raise SystemExit(f'{label} {program}: build failed\n{r.stdout[-2000:]}{r.stderr[-2000:]}')
                report = json.loads(r.stdout)
                build = {k: v for k, v in report['build'].items() if k.endswith('_seconds')}
                row = {'program': program, 'impl': 'Neo ' + label + (' dev' if profile else ''), 'wall': round(wall, 3),
                       **report['build_stages'], **build, **clang_split(report),
                       'ir_lines': sum(1 for _ in open(report['ir'])),
                       'inline_expansion_cuts': len(report.get('inline_expansion_cuts', []))}
                rows.append(row)
                print(json.dumps(row), flush=True)
                Path(sys.argv[1]).write_text(json.dumps(rows, indent=1))
    print('BREAKDOWN-DONE')


if __name__ == '__main__':
    main()
