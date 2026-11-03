#!/usr/bin/env python3
"""Markdown tables from run.py output: per row the median wall time and
range of every variant, Neo after's advantage over the best competitor (the
fastest median of Zig, Zig native and Rust), and whether Neo after's slowest
run beats that competitor's fastest run (separate ranges).

usage: summarize.py RESULT.json [RESULT.json ...]
"""
import json, statistics, sys

COMPETITORS = ('Zig', 'Zig native', 'Rust')


def cell(runs):
    walls = [r['wall_ms'] for r in runs]
    return statistics.median(walls), min(walls), max(walls)


def fmt(ms):
    return f'{ms:,.1f}'


def main():
    for path in sys.argv[1:]:
        data = json.load(open(path))
        variants = []
        for row in data['results']:
            for v in row['runs']:
                if v not in variants: variants.append(v)
        print(f'### {path.rsplit("/", 1)[-1]} ({data["rounds"]} rounds)\n')
        print('| THP | Row | Workers | ' + ' | '.join(variants) + ' | Neo after vs best | Separate ranges | Neo after vs before |')
        print('|---|---|---:|' + '---:|' * len(variants) + '---:|---|---:|')
        for row in data['results']:
            cells = {v: cell(rs) for v, rs in row['runs'].items()}
            best = min((v for v in COMPETITORS if v in cells), key=lambda v: cells[v][0])
            after, before = cells['Neo after'], cells.get('Neo before')
            ratio = cells[best][0] / after[0]
            separate = 'yes' if after[2] < cells[best][1] else 'no'
            text = [f'{fmt(m)} ({fmt(lo)}–{fmt(hi)})' if v in cells else '' for v in variants for m, lo, hi in [cells.get(v, (0, 0, 0))]]
            gain = f'{before[0] / after[0]:.2f}×' if before else ''
            flag = '' if row['outputs_agree'] else ' OUTPUT MISMATCH'
            print(f"| {row['thp']} | {row['case']}{flag} | {row['workers']} | " + ' | '.join(text)
                  + f' | {ratio:.2f}× ({best}) | {separate} | {gain} |')
        print()


if __name__ == '__main__':
    main()
