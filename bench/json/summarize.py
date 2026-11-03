#!/usr/bin/env python3
"""summarize.py RUNS.json: per-case medians, ranges and ratios from an x86.py run, as Markdown.

"Neo after ×" is the other implementation's median wall time divided by Neo after's (above 1.00× means
Neo after is faster). "Paired" counts the rounds in which Neo after was faster than it in the same round.
"Separate" says whether the two wall-time ranges do not overlap.
"""
import json, statistics, sys

def main():
    data = json.load(open(sys.argv[1]))
    print(f"CPU {data['cpu']}, {data['warmup']} warmup rounds, {data['rounds']} measured rounds, seed {data['seed']}.\n")
    for case, body in data['cases'].items():
        runs = body['runs']; neo = runs['Neo after']
        mine = statistics.median(x['wall_ms'] for x in neo); lo, hi = min(x['wall_ms'] for x in neo), max(x['wall_ms'] for x in neo)
        print(f"### {case} (checksum {body['expected']})\n")
        print('| Implementation | Median ms | Range ms | User ms | Neo after × | Paired | Separate |')
        print('|---|---:|---:|---:|---:|---:|---|')
        for name, values in sorted(runs.items(), key=lambda kv: statistics.median(x['wall_ms'] for x in kv[1])):
            walls = [x['wall_ms'] for x in values]; median = statistics.median(walls)
            user = statistics.median(x['user_ms'] for x in values)
            if name == 'Neo after':
                print(f'| **{name}** | **{median:.1f}** | {min(walls):.1f}–{max(walls):.1f} | {user:.0f} | — | — | — |'); continue
            paired = sum(1 for a, b in zip(sorted(neo, key=lambda x: x['round']), sorted(values, key=lambda x: x['round'])) if a['wall_ms'] < b['wall_ms'])
            separate = 'yes' if hi < min(walls) or lo > max(walls) else 'no'
            print(f'| {name} | {median:.1f} | {min(walls):.1f}–{max(walls):.1f} | {user:.0f} | {median / mine:.2f}× | {paired}/{len(values)} | {separate} |')
        print()

if __name__ == '__main__':
    main()
