#!/usr/bin/env python3
"""keep-medians.py KEEP-AB.LOG: medians per client of each field scripts/keep-ab.sh prints."""
import statistics, sys

rows = {}
for line in open(sys.argv[1]):
    parts = line.split()
    if len(parts) < 2 or '=' not in parts[1]: continue
    for field in parts[1:]:
        key, value = field.split('=')
        rows.setdefault(parts[0], {}).setdefault(key, []).append(float(value))
for name, fields in rows.items():
    print(name, ' '.join(f'{k}={statistics.median(v):.1f} ({min(v):.1f}-{max(v):.1f})' for k, v in fields.items()), f'n={len(fields["p50"])}')
