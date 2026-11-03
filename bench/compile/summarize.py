#!/usr/bin/env python3
"""Markdown tables from run.py results.

usage: summarize.py RESULTS.json [MORE.json ...]

First one table per scenario (cold, noop, edit): median wall seconds, programs
by builds. Then medians over rounds of every scenario, child CPU seconds and
peak RSS of the cold build and binary size, and for Neo the median cold-build
stage split from --report. Several files (for example a separate run of the
large program) are pooled.
"""
import json, statistics, sys
from collections import defaultdict

ORDER = ['hello', 'http', 'json', 'nbody', 'https-client', 'tls-fixture', 'large']
BUILDS = ['Neo before', 'Neo after', 'Neo after dev', 'Rust', 'Rust debug', 'Go', 'Zig', 'Zig Debug']
STAGES = ['parse_seconds', 'check_seconds', 'prove_seconds', 'optimize_seconds', 'lower_seconds']


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def fmt(v, digits=2):
    return '–' if v is None else f'{v:.{digits}f}'


def main():
    runs = [run for path in sys.argv[1:] for run in json.load(open(path))['runs']]
    groups = defaultdict(list)
    for run in runs: groups[(run['program'], run['impl'])].append(run)
    impls = sorted({impl for _, impl in groups}, key=lambda i: (BUILDS.index(i) if i in BUILDS else len(BUILDS), i))
    for scenario in ('cold', 'noop', 'incremental'):
        print(f'{scenario}, median wall seconds:')
        print()
        print('| program | ' + ' | '.join(impls) + ' |')
        print('|---|' + '---:|' * len(impls))
        for program in ORDER:
            cells = [fmt(med([r[scenario]['wall'] for r in groups.get((program, impl), [])])) for impl in impls]
            if any(c != '–' for c in cells): print(f'| {program} | ' + ' | '.join(cells) + ' |')
        print()
    print('| program | build | rounds | cold s | noop s | incremental s | cold CPU s | cold RSS MB | binary KB |')
    print('|---|---|---:|---:|---:|---:|---:|---:|---:|')
    for program in ORDER:
        for impl in impls:
            rows = groups.get((program, impl))
            if not rows: continue
            size = med([r.get('binary_bytes') for r in rows])
            print(f"| {program} | {impl} | {len(rows)} | {fmt(med([r['cold']['wall'] for r in rows]))} "
                  f"| {fmt(med([r['noop']['wall'] for r in rows]))} | {fmt(med([r['incremental']['wall'] for r in rows]))} "
                  f"| {fmt(med([r['cold']['cpu'] for r in rows]))} | {fmt(med([r['cold']['rss_kb'] / 1024 for r in rows]), 0)} "
                  f"| {fmt(size / 1024 if size else None, 0)} |")
    print()
    print('Neo cold builds, median seconds per stage (`--report`; prove is part of check):')
    print()
    print('| program | build | parse | check | prove | AST opt | lower | clang compile | link | clang total |')
    print('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    for program in ORDER:
        for impl in impls:
            rows = groups.get((program, impl))
            if not rows or not impl.startswith('Neo'): continue
            stage = {k: med([r['cold']['stages'].get(k) for r in rows]) for k in STAGES}
            build = {k: med([r['cold']['build'].get(k) for r in rows]) for k in ('compile_seconds', 'link_seconds', 'llvm_seconds')}
            print(f"| {program} | {impl} | " + ' | '.join(fmt(stage[k]) for k in STAGES)
                  + f" | {fmt(build['compile_seconds'])} | {fmt(build['link_seconds'])} | {fmt(build['llvm_seconds'])} |")


if __name__ == '__main__':
    main()
