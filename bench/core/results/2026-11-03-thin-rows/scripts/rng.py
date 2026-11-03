import json, statistics, sys
d = json.load(open(sys.argv[1]))
for r in d['results']:
    if sys.argv[2:] and not any(k in r['case'] for k in sys.argv[2:]): continue
    parts = []
    for v, rs in r['runs'].items():
        w = [m['wall_ms'] for m in rs]
        parts.append(f"{v}: {statistics.median(w):.1f} ({min(w):.1f}-{max(w):.1f}) u{statistics.median(m['user_ms'] for m in rs):.0f}/s{statistics.median(m['sys_ms'] for m in rs):.0f}")
    print(r.get('thp', ''), r['case'], 'w=%s' % r['workers'], ' | '.join(parts))
