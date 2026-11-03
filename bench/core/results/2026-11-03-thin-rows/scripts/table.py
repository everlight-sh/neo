# table.py FILE [THP] : markdown rows Before | After | change | best other | margin before -> after
import json, statistics, sys
d = json.load(open(sys.argv[1])); thp_default = sys.argv[2] if len(sys.argv) > 2 else ''
names = {'Neo after': 'After', 'Neo before': 'Before'}
print('| THP | Row | Workers | Before ms | After ms | Change | Best other, ms | Margin before → after |')
print('|---|---|---:|---:|---:|---:|---|---:|')
for r in d['results']:
    med = {names.get(v, v): statistics.median(m['wall_ms'] for m in rs) for v, rs in r['runs'].items()}
    rng = {names.get(v, v): (min(m['wall_ms'] for m in rs), max(m['wall_ms'] for m in rs)) for v, rs in r['runs'].items()}
    others = {k: v for k, v in med.items() if k not in ('After', 'Before')}
    if not others: continue
    best = min(others, key=others.get)
    b, a = med['Before'], med['After']
    print(f"| {r.get('thp', thp_default)} | {r['case']} | {r['workers']} | {b:,.1f} | {a:,.1f} | {100*(a-b)/b:+.1f}% | {best} {others[best]:,.1f} | {others[best]/b:.2f}× → {others[best]/a:.2f}× |")
