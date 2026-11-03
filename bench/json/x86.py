#!/usr/bin/env python3
"""Typed and dynamic JSON decoding on one x86-64 Linux box: Neo before/after, Rust serde_json,
Bun, Zig std.json and Go encoding/json in the same interleaved rounds.

Cases (every implementation computes the same checksum, which is checked on every run):
  doc-typed    small document built and decoded 1,000,000 times through typed fields:
               Neo json_field_decoder (bench/core/document_decoder.neo) vs serde derive
               (bench/rust/src/typed_json.rs doc-typed) and Zig typed structs.
  orders-typed 1,000-order array built once, decoded 1,000 times through typed fields:
               bench/core/orders_decoder.neo vs typed_json orders-typed and Zig typed structs.
  doc-dynamic  the headline JSON row: examples/library_bench.neo mode 0 vs serde_json::Value
               (usability parse), Bun JSON.parse, Go encoding/json and Zig std.json Value.
  orders-dynamic  bench/core/orders_json.neo vs typed_json orders-value and Zig Value.

Method: complete-process wall time (fork to exit, including startup, output and exit), every
process pinned with taskset to CPU (default 1; CPU 0 also serves the system) with one worker
(NEO_THREADS/GOMAXPROCS/RAYON_NUM_THREADS = 1). WARMUP rounds, then ROUNDS rounds; each round
runs every variant of a case once in a shuffled order (fixed seed). User and system CPU come
from wait4.

usage: x86.py OUT.json ROUNDS [CASE ...]
Binaries: NEO_BEFORE (/root/before), NEO_AFTER (/root/after), RUST (/root/rust), GO (/root/go-bin),
ZIG (/root/zig-baseline/bin), ZIGN (/root/zig-native/bin), SRC (/root/axon: Bun sources).
"""
import json, os, random, statistics, subprocess, sys, time
from pathlib import Path

E = os.environ.get
BEFORE, AFTER, RUST, GO = Path(E('NEO_BEFORE', '/root/before')), Path(E('NEO_AFTER', '/root/after')), Path(E('RUST', '/root/rust')), Path(E('GO', '/root/go-bin'))
ZIG, ZIGN, SRC = Path(E('ZIG', '/root/zig-baseline/bin')), Path(E('ZIGN', '/root/zig-native/bin')), Path(E('SRC', '/root/axon'))
CPU, WARMUP, SEED = E('CPU', '1'), int(E('WARMUP', '2')), int(E('SEED', '20261103'))
ONE = {'NEO_THREADS': '1', 'GOMAXPROCS': '1', 'RAYON_NUM_THREADS': '1', 'ZIG_THREADS': '1'}
N = '1000000'


def neo(name, *args):
    """The same Neo program built from the base tree and from this tree."""
    return {'Neo before': [BEFORE / name, *args], 'Neo after': [AFTER / name, *args]}


CASES = {  # case -> (variants {name: argv}, expected output)
    'doc-typed': ({
        **neo('document_decoder', N),
        'Rust serde typed': [RUST / 'typed_json', 'doc-typed', N],
        'Rust serde Value': [RUST / 'typed_json', 'doc-value', N],
        'Zig typed arena': [ZIG / 'json', 'doc-typed-arena', N],
        'Zig typed arena native': [ZIGN / 'json', 'doc-typed-arena', N],
    }, '513500000'),
    'orders-typed': ({
        **neo('orders_decoder', '1000', '1000'),
        'Rust serde typed': [RUST / 'typed_json', 'orders-typed', '1000'],
        'Zig typed arena': [ZIG / 'json', 'orders-typed-arena', '1000'],
        'Zig typed arena native': [ZIGN / 'json', 'orders-typed-arena', '1000'],
    }, '34327000'),
    'doc-dynamic': ({
        **neo('library_bench', '0', N),
        'Bun JSON.parse': ['bun', SRC / 'bench/usability/bun.ts', 'parse', N],
        'Rust serde_json::Value': [RUST / 'usability', 'parse', N],
        'Go encoding/json': [GO / 'json', N],
        'Zig Value': [ZIG / 'json', 'doc-value', N],
        'Zig typed arena': [ZIG / 'json', 'doc-typed-arena', N],
        'Zig typed arena native': [ZIGN / 'json', 'doc-typed-arena', N],
    }, '513500000'),
    'orders-dynamic': ({
        **neo('orders_json', '1000', '1000'),
        'Rust serde_json::Value': [RUST / 'typed_json', 'orders-value', '1000'],
        'Zig Value': [ZIG / 'json', 'orders-value', '1000'],
        'Zig Value arena': [ZIG / 'json', 'orders-value-arena', '1000'],
    }, '34327000'),
}


def run(argv):
    env = {**os.environ, **ONE}
    start = time.perf_counter_ns()
    p = subprocess.Popen(['taskset', '-c', CPU, *map(str, argv)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    wall = time.perf_counter_ns() - start
    # communicate() reaps the child; its rusage is the children delta below.
    return wall, out.decode().strip(), err.decode()[-2000:], p.returncode


def main():
    out_path, rounds = Path(sys.argv[1]), int(sys.argv[2])
    names = sys.argv[3:] or list(CASES)
    rng = random.Random(SEED)
    data = {'cpu': CPU, 'warmup': WARMUP, 'rounds': rounds, 'seed': SEED, 'started': time.time(), 'cases': {}}
    for case in names:
        variants, expected = CASES[case]
        variants = {k: v for k, v in variants.items() if Path(v[0]).exists() or v[0] == 'bun'}
        runs = {k: [] for k in variants}
        for r in range(WARMUP + rounds):
            order = list(variants); rng.shuffle(order)
            for name in order:
                before = os.times()
                wall, output, err, code = run(variants[name])
                after = os.times()
                assert code == 0 and output == expected, (case, name, code, output, expected, err)
                if r >= WARMUP:
                    runs[name].append({'round': r - WARMUP, 'wall_ms': wall / 1e6,
                                       'user_ms': (after.children_user - before.children_user) * 1e3,
                                       'sys_ms': (after.children_system - before.children_system) * 1e3})
        data['cases'][case] = {'expected': expected, 'argv': {k: list(map(str, v)) for k, v in variants.items()}, 'runs': runs}
        summary = {k: round(statistics.median(x['wall_ms'] for x in v), 1) for k, v in runs.items()}
        print(case, json.dumps(summary), flush=True)
        out_path.write_text(json.dumps(data, indent=1))
    data['finished'] = time.time()
    out_path.write_text(json.dumps(data, indent=1))


if __name__ == '__main__':
    main()
