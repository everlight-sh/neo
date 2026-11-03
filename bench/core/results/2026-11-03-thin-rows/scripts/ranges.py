import json, statistics, sys
d = json.load(open(sys.argv[1]))
for r in d['results']:
    parts = []
    for v, rs in r['runs'].items():
        w = sorted(m['wall_ms'] for m in rs)
        parts.append(f"{v}: {statistics.median(w):.1f} ({w[0]:.1f}-{w[-1]:.1f})")
    print(r['case'], 'w=%s' % r['workers'], 'ok' if r.get('outputs_agree') else 'MISMATCH', ' | '.join(parts))
