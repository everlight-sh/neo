#!/usr/bin/env python3
"""Report every case, plus both immediate and original-baseline comparisons."""
import argparse,json,statistics
from pathlib import Path
from summarize_regression import interval

def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    data=json.loads((a.folder/'measurements.json').read_text());assert data['valid']
    names=['previous','Before','Axon','Rust','Go','Bun'];labels=['Original Axon','Pre-fix Axon','Fixed Axon','Rust','Go','Bun']
    median=statistics.median;analysis=[]
    lines=['# Axon core regression fixes — native Linux ARM64, 2026-10-27','',
      'All timings below are fresh, interleaved runs on the same VM. Lower milliseconds and memory are better; higher HTTP requests/s is better. Original Axon is the SHA-verified 2026-10-25 append/JSON-fixed build. Pre-fix Axon is the frozen 2026-10-27 build from the regression report. Fixed Axon contains the language changes described here. Historical reports and executables are retained.','',
      '## Language changes','',
      '- A 16-byte allocation header derives capacity from its size class, replacing the redundant 32-byte header.',
      '- Aligned control pointers carry the private-count flag. Private allocations use ordinary retain/release and uniqueness loads; shared worker allocations retain atomic operations.',
      '- Heap array descriptors occupy 24 bytes instead of 32, including arrays nested in record fields. The ownership bit is packed into the control word and decoded before use. SSA and function array values retain the existing four fields.',
      '- Small nonrecursive helpers called with boolean literals are exposed to LLVM so allocator policy branches can fold.',
      '- Byte-map value replacement preserves the existing key and fingerprint instead of rewriting both.',
      '- Short positive integer formatting packs bounded decimal groups instead of looping over pairs. Signed/general formatting retains its checked path.','',
      '## Protocol and limits','',
      'Apple M1 Pro host; native ARM64 Ubuntu container; CPU affinity 0 for single-worker runs and 0–3 for four-worker runs. Binaries and data are VM-local. Builds and tests finish before timing. The core harness uses nine measured shuffled rounds after two warm-ups. Integer/checksum outputs are exact; N-body energies use relative tolerance 1e-9 and absolute tolerance 1e-12. Every timed map value is checked. Map pauses for memory sampling are outside phase timers.','',
      'Rust uses unchanged optimized 1.98.1 ARM64 executables whose hashes match the earlier benchmark; no Rust source or flags were changed. Go and Axon are rebuilt; Bun runs the unchanged workload sources. Exact versions, commands, outputs, SHA-256 hashes and source snapshots are in the raw results.','',
      'JSON numbers measure construction, parsing, access, checksum and cleanup, including process startup; they do not isolate parsing. Axon map reads return owned bytes; Rust/Go reads borrow strings. Bun has no reserve API and no four-worker compute implementation here. Generic-map memory is a separate workload from the compact byte-map comparison.','',
      '95% intervals use 20,000 paired-round bootstrap resamples of median ratios. A >5% median slowdown with a lower interval bound >1 is a regression screen, not a multiplicity-adjusted statistical proof. Independent 15-round map confirmation is retained separately. The original frozen binaries also rerun substantially slower than some historical absolute results on this VM; comparisons below use current paired runs.','']
    def table(header,rows):
        lines.extend(['| '+' | '.join(header)+' |','|'+'|'.join(['---']*len(header))+'|'])
        lines.extend('| '+' | '.join(map(str,row))+' |' for row in rows);lines.append('')
    def changes(section,case,runs,timing,invert=False):
        for base in ['previous','Before']:
            analysis.append(dict(section=section,case=case,baseline=base,**interval([timing(r) for r in runs[base]],[timing(r) for r in runs['Axon']],invert)))
    for section in ['compute','json','collections']:
        lines.extend(['## '+section.title()+' — milliseconds','']);rows=[]
        for item in data[section]:
            timing=(lambda r:int(r['output'].split()[1])) if section=='collections' else (lambda r:r['wall_ns'])
            case=item['case']+(' / '+str(item['workers'])+' workers' if section=='compute' else '')
            rows.append([case,*[f'{median(timing(r) for r in item["runs"][name])/1e6:.3f}' if name in item['runs'] else '—' for name in names]])
            changes(section,case,item['runs'],timing)
        table(['Case',*labels],rows)
    lines.extend(['## Map API phases — milliseconds',''])
    for item in data['maps']:
        if not item['n']:continue
        case=f'{item["n"]:,} keys, '+('reserved' if item['reserved'] else 'growing');lines.extend(['### '+case,'']);rows=[]
        for phase in ['insert','lookup','update','lookup_updated','delete','lookup_remaining']:
            timing=lambda r:next(x['ns'] for x in r['phases'] if x['phase']==phase)
            rows.append([phase,*[f'{median(timing(r) for r in item["runs"][name])/1e6:.3f}' if name in item['runs'] else '—' for name in names]])
            changes('maps',case+' / '+phase,item['runs'],timing)
        table(['Phase',*labels],rows)
        rows=[]
        for metric in ['rss_bytes','peak_rss_bytes','pss_bytes']:
            rows.append([metric,*[f'{median(next(x[metric] for x in r["phases"] if x["phase"]=="steady") for r in item["runs"][name])/2**20:.2f}' if name in item['runs'] else '—' for name in names]])
        table(['Steady checkpoint memory (MiB)',*labels],rows)
    lines.extend(['## Collection peak memory — MiB','']);rows=[]
    for item in data['collections']:
        rows.append([item['case'],*[f'{median(r["peak_rss_bytes"] for r in item["runs"][name])/2**20:.2f}' if name in item['runs'] else '—' for name in names]])
    table(['Case',*labels],rows)
    lines.extend(['## HTTP — validated requests/s','',data['http_protocol'],'','Five measured rounds per scenario, one warm-up load per trial; servers on CPUs 0 or 0–3, load client and sampler on CPUs 4–7. Every response status, length and body is validated; outstanding pipeline batches are drained. All worker processes count toward CPU and PSS.','']);rows=[]
    for case in sorted({x['case'] for x in data['http']}):
        runs={name:[x['result'] for x in data['http'] if x['case']==case and x['implementation']==name] for name in names}
        rows.append([case,*[f'{median(r["median_rps"] for r in runs[name]):,.0f}' for name in names]])
        changes('http',case,runs,lambda r:r['median_rps'],True)
    table(['Scenario',*labels],rows)
    for metric,title,scale in [('cpu_us_per_request','HTTP server CPU — microseconds/request',1),('peak_footprint_bytes','HTTP peak total PSS — MiB',1/2**20)]:
        lines.extend(['### '+title,'']);rows=[]
        for case in sorted({x['case'] for x in data['http']}):
            rows.append([case,*[f'{median(x["result"][metric] for x in data["http"] if x["case"]==case and x["implementation"]==name)*scale:.3f}' for name in names]])
        table(['Scenario',*labels],rows)
    lines.extend(['## Regression screens','']);table(['Section','Case','Baseline','Fixed/baseline slowdown','95% interval','Classification'],[[x['section'],x['case'],labels[names.index(x['baseline'])],f'{x["slowdown_ratio"]:.3f}×',f'{x["ci95"][0]:.3f}–{x["ci95"][1]:.3f}',x['classification']] for x in analysis])
    confirmation=a.folder/'confirmation/measurements.json'
    if confirmation.exists():
        d=json.loads(confirmation.read_text());assert d['valid'];lines.extend(['## Independent map confirmation','',f'{d["repeats"]} measured rounds after {d["warmups"]} warm-ups; original and fixed Axon interleaved.','']);rows=[];checks=[]
        for item in d['maps']:
            for phase in ['insert','lookup','update','lookup_updated','delete','lookup_remaining']:
                timing=lambda r:next(x['ns'] for x in r['phases'] if x['phase']==phase)
                old=[timing(r) for r in item['runs']['previous']];new=[timing(r) for r in item['runs']['Axon']];change=interval(old,new)
                case=f'{item["n"]} / {"reserved" if item["reserved"] else "growing"} / {phase}'
                rows.append([case,f'{median(old)/1e6:.3f}',f'{median(new)/1e6:.3f}',f'{change["slowdown_ratio"]:.3f}×',f'{change["ci95"][0]:.3f}–{change["ci95"][1]:.3f}',change['classification']]);checks.append(dict(case=case,**change))
        table(['Case','Original ms','Fixed ms','Slowdown','95% interval','Classification'],rows)
    else:checks=[]
    lines.extend(['## Validation evidence','',
      'Full `axon test` on macOS and native Linux, including unit tests, native language/doc cases, all integration scripts and JSX/SSR tests. Heap probes validate alignment, full rounded payload capacity, 3,072 simultaneous nonoverlapping blocks, both private/shared modes, pool reuse and boundaries through 32 MiB. Shared-array tests run both 1- and 4-worker modes. The logs are retained with the raw results.','',
      'Every measured Axon ELF has no undefined imports, PT_INTERP or DT_NEEDED entries. Actual JSON, append and full 1M-key map binaries execute inside an empty chroot containing only that executable. Runtime and standard library sources remain Axon-only; Python/LLVM are build tools. macOS test binaries have no undefined imports, but the platform loader still requires its system load command; the fully standalone deployment proof is Linux.','',
      'Raw results: `.kernel-build/core-regression-fixes-2026-10-27/results/`. Earlier reports and candidate screenings are retained separately.'])
    a.report.write_text('\n'.join(lines)+'\n');(a.folder/'fix-analysis.json').write_text(json.dumps(dict(comparisons=analysis,confirmation=checks),indent=2));print(a.report)

if __name__=='__main__':main()
