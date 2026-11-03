#!/usr/bin/env python3
"""Markdown rows for the report from a compare.py measurements.json. usage: report_rows.py JSON"""
import json, sys, statistics
d = json.load(open(sys.argv[1]))
order = ['Neo', 'Neo (before)', 'Rust', 'Go', 'Bun']
rows = {(r['scenario'], r['server']): r for r in d['results']}
multi = {'hello-64', 'hello-256', 'pipeline-16', 'smooth-10000-default', 'nbody-default'}
us = lambda v: 'n/a' if v is None else (f'{v/1000:.1f} ms' if v >= 10000 else f'{v:,.0f} µs')
for sc in d['scenarios']:
    name = sc[0]
    print(f"\n### {name}{' (multi-worker)' if name in multi else ' (one worker)'}\n")
    print(f"`{sc[1].replace('POST:', 'POST ')}`, {sc[2]} connections" + (f", pipeline depth {sc[3]}" if sc[3] else '') + '.\n')
    print('| Server | req/s (median; range) | p50 | p99 (worst run) | CPU µs/req | Other cores | Errors |')
    print('|---|---:|---:|---:|---:|---:|---:|')
    rust = rows.get((name, 'Rust'))
    for s in order:
        r = rows.get((name, s))
        if not r: continue
        p99 = 'n/a' if r['median_p99_us'] is None or sc[3] else f"{us(r['median_p99_us'])} ({us(r['max_p99_us'])})"
        p50 = 'n/a' if sc[3] else us(r['median_p50_us'])
        label = f'**{s}**' if s == 'Neo' else s
        print(f"| {label} | {r['median_rps']:,.0f} ({r['min_rps']:,.0f}–{r['max_rps']:,.0f}) | {p50} | {p99} | {r['cpu_us_per_request']:.2f} | {r['median_other_cores']:.1f} | {r['errors']} / {r['non2xx']} |")
print('\n### Neo against Rust\n')
print('| Scenario | Throughput Neo / Rust | CPU per request Rust / Neo | p99 Neo / Rust | Neo (before) throughput / Rust | Neo (before) CPU Rust / Neo |')
print('|---|---:|---:|---:|---:|---:|')
for sc in d['scenarios']:
    n, b, r = rows.get((sc[0], 'Neo')), rows.get((sc[0], 'Neo (before)')), rows.get((sc[0], 'Rust'))
    if not (n and r): continue
    p = 'n/a' if sc[3] else f"{n['median_p99_us']/r['median_p99_us']:.2f}×"
    print(f"| {sc[0]} | {n['median_rps']/r['median_rps']:.2f}× | {r['cpu_us_per_request']/n['cpu_us_per_request']:.2f}× | {p} | {b['median_rps']/r['median_rps']:.2f}× | {r['cpu_us_per_request']/b['cpu_us_per_request']:.2f}× |")
# per-round view for Neo vs Rust
print('\n### Per round (Neo / Rust req/s)\n')
parts = d['parts']
for sc in d['scenarios']:
    line = []
    for rnd in sorted({p['round'] for p in parts}):
        get = lambda s: next((p for p in parts if p['scenario'] == sc[0] and p['server'] == s and p['round'] == rnd), None)
        n, r = get('Neo'), get('Rust')
        if n and r: line.append(f"{n['median_rps']:,.0f} / {r['median_rps']:,.0f}")
    print(f"- {sc[0]}: " + '; '.join(line))
