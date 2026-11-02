#!/usr/bin/env python3
"""Summarize all retained cases and screen paired before/after regressions."""
import argparse, json, random, statistics
from pathlib import Path

def interval(before,after,invert=False):
    assert len(before)==len(after) and len(before)>=5
    ratio=(statistics.median(before)/statistics.median(after)) if invert else (statistics.median(after)/statistics.median(before))
    rng=random.Random(271028);values=[];n=len(before)
    for _ in range(20000):
        indexes=[rng.randrange(n) for _ in range(n)]
        a=statistics.median(before[i] for i in indexes);b=statistics.median(after[i] for i in indexes)
        values.append(a/b if invert else b/a)
    values.sort();low,high=values[500],values[19500]
    state='regression screen' if ratio>1.05 and low>1 else 'possible slowdown' if ratio>1.05 else 'improvement' if ratio<0.95 and high<1 else 'no material change established'
    return dict(slowdown_ratio=ratio,ci95=[low,high],classification=state)

def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();out=a.folder
    data=json.loads((out/'measurements.json').read_text());assert data['valid'];summary={};regressions=[]
    for section in ['compute','json','collections']:
        rows=[]
        for item in data[section]:
            internal=section=='collections'
            def timing(run):return int(run['output'].split()[1]) if internal else run['wall_ns']
            measurements={name:dict(ms=statistics.median(timing(r) for r in runs)/1e6,range_ms=[min(timing(r) for r in runs)/1e6,max(timing(r) for r in runs)/1e6],peak_rss_mib=max(r['peak_rss_bytes'] for r in runs)/2**20) for name,runs in item['runs'].items()}
            change=interval([timing(r) for r in item['runs']['previous']],[timing(r) for r in item['runs']['Axon']])
            record=dict(section=section,case=item['case'],workers=item['workers'],measurements=measurements,change=change);rows.append(record);regressions.append(record)
        summary[section]=rows
    summary['maps']=[]
    for item in data['maps']:
        measurements={}
        for name,runs in item['runs'].items():
            phases={}
            for phase in ['insert','lookup','steady','update','lookup_updated','delete','lookup_remaining']:
                records=[next(x for x in r['phases'] if x['phase']==phase) for r in runs]
                phases[phase]=dict(ms=statistics.median(x['ns'] for x in records)/1e6,rss_mib=statistics.median(x['rss_bytes'] for x in records)/2**20,peak_rss_mib=statistics.median(x['peak_rss_bytes'] for x in records)/2**20,pss_mib=statistics.median(x['pss_bytes'] for x in records)/2**20)
            measurements[name]=phases
        record=dict(n=item['n'],reserved=item['reserved'],measurements=measurements);summary['maps'].append(record)
        if not item['n']:continue
        for phase in ['insert','lookup','update','lookup_updated','delete','lookup_remaining']:
            old=[next(x for x in r['phases'] if x['phase']==phase)['ns'] for r in item['runs']['previous']]
            new=[next(x for x in r['phases'] if x['phase']==phase)['ns'] for r in item['runs']['Axon']]
            regressions.append(dict(section='maps',case=f"{item['n']}-{'reserved' if item['reserved'] else 'growing'}-{phase}",change=interval(old,new),before_ms=statistics.median(old)/1e6,after_ms=statistics.median(new)/1e6))
    summary['http']=[]
    for case in sorted({x['case'] for x in data['http']}):
        samples={name:[x['result'] for x in data['http'] if x['case']==case and x['implementation']==name] for name in ['previous','Axon','Rust','Go','Bun']}
        measurements={name:dict(rps=statistics.median(x['median_rps'] for x in runs),cpu_us_per_request=statistics.median(x['cpu_us_per_request'] for x in runs),peak_pss_mib=max(x['peak_footprint_bytes'] for x in runs)/2**20,peak_rss_mib=max(x['peak_rss_bytes'] for x in runs)/2**20) for name,runs in samples.items()}
        change=interval([x['median_rps'] for x in samples['previous']],[x['median_rps'] for x in samples['Axon']],True)
        record=dict(section='http',case=case,measurements=measurements,change=change);summary['http'].append(record);regressions.append(record)
    result=dict(summary=summary,regressions=regressions,screened=[x for x in regressions if x['change']['classification'] in ['regression screen','possible slowdown']],profiles=data['profiles'],notes=[
        'Slowdown ratio >1 means current Axon is slower than the interleaved frozen build. HTTP uses previous/current throughput; other cases use current/previous elapsed time.',
        'Paired-round ratio-of-medians bootstrap, 20,000 resamples, 95% intervals. These are unadjusted screening intervals across multiple cases; independent repeats are needed to confirm flags.',
        'Material-change screen uses a 5% median threshold and excludes zero-size timing (correctness only). Every nonempty original case remains listed.'
    ])
    confirmation_path=out/'confirmation/measurements.json'
    if confirmation_path.exists():
        confirm=json.loads(confirmation_path.read_text());assert confirm['valid'];checks=[]
        for item in confirm['maps']:
            for phase in ['insert','lookup','update','lookup_updated','delete','lookup_remaining']:
                old=[next(x for x in r['phases'] if x['phase']==phase)['ns'] for r in item['runs']['previous']]
                new=[next(x for x in r['phases'] if x['phase']==phase)['ns'] for r in item['runs']['Axon']]
                checks.append(dict(section='maps',case=f"{item['n']}-{'reserved' if item['reserved'] else 'growing'}-{phase}",before_ms=statistics.median(old)/1e6,after_ms=statistics.median(new)/1e6,change=interval(old,new)))
        for item in confirm['collections']:
            old=[x['phase_ns'] for x in item['runs']['previous']];new=[x['phase_ns'] for x in item['runs']['Axon']]
            checks.append(dict(section='collections',case=item['case'],before_ms=statistics.median(old)/1e6,after_ms=statistics.median(new)/1e6,change=interval(old,new)))
        result['confirmation']=checks
        result['confirmed_regressions']=[x for x in checks if x['change']['classification']=='regression screen']
    result['memory_regressions']=[]
    for row in summary['collections']:
        before=row['measurements']['previous']['peak_rss_mib'];after=row['measurements']['Axon']['peak_rss_mib']
        if after>before*1.05 and after-before>1:result['memory_regressions'].append(dict(case=row['case'],before_peak_rss_mib=before,after_peak_rss_mib=after,ratio=after/before))
    (out/'analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:result.get(k) for k in ['confirmed_regressions','memory_regressions']},indent=2))

if __name__=='__main__':main()
