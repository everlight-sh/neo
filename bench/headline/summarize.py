#!/usr/bin/env python3
"""Markdown tables for run_headline.py output: medians, ranges and Vif's ratio against each competitor.

usage: summarize.py http.json cli.json
Ratios are oriented so that above 1.00x means Vif is better: req/s Vif / other; milliseconds and
memory other / Vif. "Ranges" says whether Vif's worst run still beats the other's best run.
"""
import json, statistics, sys

http, cli = (json.load(open(p)) for p in sys.argv[1:3])


def table(title, unit, rows, higher_better, fmt):
    """rows: {name: [values]}; 'Vif' must be present."""
    vif = rows['Vif']; vm = statistics.median(vif)
    print(f'### {title}\n\n| Implementation | Median {unit} | Range | Vif vs it | Ranges |\n|---|---:|---:|---:|---|')
    for name, xs in sorted(rows.items(), key=lambda kv: statistics.median(kv[1]), reverse=higher_better):
        m = statistics.median(xs)
        if name == 'Vif': ratio, sep = '', ''
        else:
            r = vm / m if higher_better else m / vm
            ratio = f'{r:.2f}x'
            clear = min(vif) > max(xs) if higher_better else max(vif) < min(xs)
            lost = max(vif) < min(xs) if higher_better else min(vif) > max(xs)
            sep = 'separate (Vif ahead)' if clear else 'separate (Vif behind)' if lost else 'overlap'
        print(f'| {name} | {fmt(m)} | {fmt(min(xs))}-{fmt(max(xs))} | {ratio} | {sep} |')
    print()


n = len(next(iter(http['results']['hello'].values())))
for scenario, title in (('hello', 'HTTP hello, one worker (req/s)'), ('pipeline-16', 'Pipelined HTTP, 16 deep, one worker (req/s)')):
    res = http['results'][scenario]
    table(f'{title}, {n} rounds', 'req/s', {k: [r['rps'] for r in v] for k, v in res.items()}, True, lambda x: f'{x:,.0f}')
    print('| Implementation | p50 us | p99 us | server CPU/request us (user + sys) | server CPUs busy | client CPUs busy | errors |\n|---|---:|---:|---:|---:|---:|---|')
    for k, v in res.items():
        med = lambda f: statistics.median(r[f] for r in v)
        print(f"| {k} | {med('p50_us'):.0f} | {med('p99_us'):.0f} | {med('user_us'):.2f} + {med('sys_us'):.2f} = {med('user_us') + med('sys_us'):.2f}"
              f" | {med('server_cpu'):.2f} | {med('client_cpu'):.2f} | {sum(r['bad'] for r in v)} |")
    print()
mib = lambda x: f'{x / 2**20:.2f}'
table('Memory: peak aggregate PSS of the server process tree under the hello load (MiB)', 'MiB',
      {k: [r['peak_pss'] for r in v] for k, v in http['results']['hello'].items()}, False, mib)
table('Memory: peak aggregate RSS under the hello load (MiB, for reference)', 'MiB',
      {k: [r['peak_rss'] for r in v] for k, v in http['results']['hello'].items()}, False, mib)
print('| Implementation | processes | threads (main process) | idle PSS MiB |\n|---|---:|---:|---:|')
for k, v in http['results']['hello'].items():
    print(f"| {k} | {v[0]['processes']} | {v[0]['threads']} | {mib(statistics.median(r['idle_pss'] for r in v))} |")
print('\nValidation:', ', '.join(f"{k}: hello {'ok' if v['hello'] else 'FAIL'}, 16-deep pipelined {'ok' if v['pipelined_16'] else 'FAIL'}, io_uring fds {v['io_uring_fds']}"
                                  for k, v in http['validation'].items()), '\n')
for case, d in cli['results'].items():
    table(f"{case} ({cli['rounds']} rounds after {cli['warmups']} warm-ups; output {d['reference']})", 'ms',
          {k: [r['wall_ms'] for r in v] for k, v in d['runs'].items()}, False, lambda x: f'{x:.1f}')
    print('| Implementation | median CPU ms | peak RSS MiB |\n|---|---:|---:|')
    for k, v in d['runs'].items():
        print(f"| {k} | {statistics.median(r['cpu_ms'] for r in v):.1f} | {max(r['peak_rss_kib'] for r in v) / 1024:.1f} |")
    print()
