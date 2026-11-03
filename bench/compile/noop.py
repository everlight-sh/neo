#!/usr/bin/env python3
"""Unchanged rebuilds, timed many times: Neo trees against Rust and Go.

usage: noop.py OUT.json ROUNDS

Every (program, build) pair is built once untimed, then rebuilt unchanged
ROUNDS times in shuffled order (fixed seed). Neo rows run `./neo build P -o
OUT --report`, the command run.py times, and also without --report. Wall
seconds come from the parent's clock around the whole command, launcher
included.

Zig is left out: `zig build-exe` keeps no output cache, so its unchanged
rebuild is a full build (run.py measures it).

Environment: NEO_TREES, SOURCES, WORK and ONLY as for run.py; OTHERS=0 leaves
out Rust and Go.
"""
import json, os, random, statistics, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import ENV, NEO, OTHER, SOURCES, TREES, WORK, E  # noqa: E402


def pairs():
    only = set(filter(None, E('ONLY', '').split(',')))
    out = []
    for program, path in NEO.items():
        if only and program not in only: continue
        for label, tree in TREES:
            binary = str(WORK / 'noop' / f'{label}-{program}')
            out.append((program, f'Neo {label}', tree, ['./neo', 'build', path, '-o', binary, '--report']))
            out.append((program, f'Neo {label} (no --report)', tree, ['./neo', 'build', path, '-o', binary]))
        if E('OTHERS', '1') == '0': continue
        for impl, (cwd, argv, _) in OTHER.get(program, {}).items():
            if impl == 'Zig': continue
            argv = [a.replace('{out}', str(WORK / 'noop' / f'{impl}-{program}')) for a in argv]
            out.append((program, impl, str(SOURCES / cwd), argv))
    return out


def timed(cwd, argv):
    started = time.perf_counter()
    r = subprocess.run(argv, cwd=cwd, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    seconds = time.perf_counter() - started
    if r.returncode: raise SystemExit(f'{argv} failed in {cwd}:\n{r.stderr.decode()[-2000:]}')
    return seconds


def main():
    out_path, rounds = sys.argv[1], int(sys.argv[2])
    (WORK / 'noop').mkdir(parents=True, exist_ok=True)
    todo = pairs()
    for _, _, cwd, argv in todo: timed(cwd, argv)  # build, and leave each tree's own records
    samples = {(p, i): [] for p, i, _, _ in todo}
    order = random.Random(11)
    for round_no in range(rounds):
        order.shuffle(todo)
        for program, impl, cwd, argv in todo: samples[(program, impl)].append(timed(cwd, argv))
        print(f'round {round_no} done', flush=True)
    result = [{'program': p, 'impl': i, 'median': statistics.median(v), 'min': min(v), 'max': max(v), 'samples': v}
              for (p, i), v in samples.items()]
    Path(out_path).write_text(json.dumps({'rounds': rounds, 'runs': result}, indent=1))
    for r in result: print(f"{r['program']:13} {r['impl']:28} {r['median']:.4f} s  ({r['min']:.4f}-{r['max']:.4f})")
    print('NOOP-DONE')


if __name__ == '__main__':
    main()
