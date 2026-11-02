#!/usr/bin/env python3
"""Markdown tables from run_cli.py / run_http.py JSON. usage: summarize.py DIR"""
import json, statistics, sys
from pathlib import Path

d = Path(sys.argv[1])
med = lambda xs: statistics.median(xs)
mib = lambda kib: kib / 1024


def compute():
    data = json.loads((d / 'compute.json').read_text())
    print(f"rounds {data['rounds']} ({data['started']} - {data['finished']})\n")
    before = any('Vif before' in r['runs'] for r in data['results'])
    print('| Case | Workers | Vif ms | Zig ms | Zig native ms | Zig / Vif | Zig native / Vif | Peak RSS MiB Vif / Zig / Zig native |'
          + (' Vif before ms | Vif before / Vif | Peak RSS MiB Vif before |' if before else '') + ' Outputs |')
    print('|---|---:|---:|---:|---:|---:|---:|---:|' + ('---:|---:|---:|' if before else '') + '---|')
    for r in data['results']:
        m = {v: med([x['wall_ms'] for x in rs]) for v, rs in r['runs'].items()}
        rss = {v: max(x['peak_rss_kib'] for x in rs) for v, rs in r['runs'].items()}
        extra = (f" {m['Vif before']:.1f} | {m['Vif before'] / m['Vif']:.2f}× | {mib(rss['Vif before']):.1f} |" if before else '')
        print(f"| {r['case']} | {r['workers']} | {m['Vif']:.1f} | {m['Zig']:.1f} | {m['Zig native']:.1f} | "
              f"{m['Zig'] / m['Vif']:.2f}× | {m['Zig native'] / m['Vif']:.2f}× | "
              f"{mib(rss['Vif']):.1f} / {mib(rss['Zig']):.1f} / {mib(rss['Zig native']):.1f} |{extra} {'agree' if r['outputs_agree'] else 'DIFFER'} |")
    print('\nRun ranges (min-max ms):')
    for r in data['results']:
        print(f"- {r['case']} w={r['workers']}: " + '; '.join(
            f"{v} {min(x['wall_ms'] for x in rs):.1f}-{max(x['wall_ms'] for x in rs):.1f}" for v, rs in r['runs'].items()))


def json_suite():
    data = json.loads((d / 'json.json').read_text())
    print(f"\nrounds {data['rounds']} ({data['started']} - {data['finished']})\n")
    for r in data['results']:
        vif = med([x['wall_ms'] for x in r['runs']['Vif']])
        print(f"### {r['case']} (checksum {r['checksum']}, outputs {'agree' if r['outputs_agree'] else 'DIFFER'})\n")
        print('| Implementation | Median ms | Min-max ms | Median CPU ms | Peak RSS MiB | vs Vif |')
        print('|---|---:|---:|---:|---:|---:|')
        for v, rs in r['runs'].items():
            w = [x['wall_ms'] for x in rs]
            print(f"| {v} | {med(w):.1f} | {min(w):.1f}-{max(w):.1f} | {med([x['cpu_ms'] for x in rs]):.1f} | "
                  f"{mib(max(x['peak_rss_kib'] for x in rs)):.2f} | {med(w) / vif:.2f}× |")
        print()


def http():
    data = json.loads((d / 'http.json').read_text())
    print(f"\nrounds {data['rounds']}, server CPUs {data['server_cpus']}, client CPUs {data['client_cpus']}\n")
    for scen, rows in data['results'].items():
        vif = med([x['rps'] for x in rows['Vif']])
        print(f"### {scen}\n")
        print('| Server | Median req/s | Run range | p50 µs | p99 µs | CPU µs/req (user + kernel) | Server CPU busy | Peak RSS MiB | Threads | req/s vs Vif | CPU/req vs Vif |')
        print('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
        vcpu = med([x['user_us'] + x['sys_us'] for x in rows['Vif']])
        for name, rs in rows.items():
            rps = med([x['rps'] for x in rs]); u = med([x['user_us'] for x in rs]); s = med([x['sys_us'] for x in rs])
            lat = lambda k: 'n/a' if scen.startswith('pipeline') else f"{med([x[k] for x in rs]):.0f}"
            bad = ' (ERRORS)' if any(x['bad'] for x in rs) else ''
            print(f"| {name}{bad} | {rps:,.0f} | {min(x['rps'] for x in rs):,.0f}-{max(x['rps'] for x in rs):,.0f} | {lat('p50')} | {lat('p99')} | "
                  f"{u:.2f} + {s:.2f} = {u + s:.2f} | {med([(x['user_us'] + x['sys_us']) * x['rps'] / 1e4 for x in rs]):.0f}% | "
                  f"{max(x['peak_rss'] for x in rs) / 2**20:.1f} | {rs[0]['threads']} | {rps / vif:.2f}× | {med([x['user_us'] + x['sys_us'] for x in rs]) / vcpu:.2f}× |")
        print()


for part in sys.argv[2:] or ['compute', 'json', 'http']:
    if (d / f'{part}.json').exists(): {'compute': compute, 'json': json_suite, 'http': http}[part]()
