#!/usr/bin/env python3
"""medians.py AB.LOG: each client's median p50 over the rounds of scripts/ab.sh, with its min-max range."""
import statistics, sys

rounds = {}
for line in open(sys.argv[1]):
    if not line.startswith('round '): continue
    for field in line.split()[2:]:
        name, value = field.split('=')
        rounds.setdefault(name, []).append(float(value))
for name, values in rounds.items():
    print(f'{name:12} median {statistics.median(values):8.1f}  range {min(values):8.1f}-{max(values):8.1f}  n={len(values)}')
