#!/usr/bin/env python3
"""summarize.py RESULT.json [...]: median [min-max] wall ms and CPU ms per case and variant."""
import json, statistics, sys
for path in sys.argv[1:]:
    d = json.load(open(path))
    print(f"== {path} ({d['rounds']} rounds)")
    for r in d['results']:
        cells = []
        for v, rs in r['runs'].items():
            w = [m['wall_ms'] for m in rs]
            cells.append(f"{v} {statistics.median(w):.1f} [{min(w):.1f}-{max(w):.1f}]")
        print(f"{r['case']:22s} w={r['workers']} {'ok' if r['outputs_agree'] else 'MISMATCH'}  " + "  ".join(cells))
