#!/usr/bin/env python3
"""Publish complete core regression measurements without replacing old reports."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--report',type=Path,required=True);a=p.parse_args();assert not a.report.exists()
    d=json.loads((a.folder/'analysis.json').read_text());raw=json.loads((a.folder/'measurements.json').read_text());assert raw['valid'];s=d['summary']
    lines=['# Axon core benchmarks and regression check — 2026-10-27','',
        '**The rerun is not regression-free.** The independent repeat confirms slower small string-map operations and million-key deletion. Generic `HashMap` peak RSS rises about 10%, while its workload runs faster. Compute and HTTP show no confirmed material timing regression against the interleaved frozen executable. JSON, append and sort improve.','',
        'This is the language compiler/runtime/standard library, with no Axon database or framework involved. Compiler/runtime/stdlib source remained unchanged throughout this request (85 files checked before and after). New code is benchmark tooling and Bun/Go counterparts.','',
        'Native ARM64 Linux on the Apple M1 Pro, ten-vCPU Linuxkit VM. Nine measured shuffled rounds plus two excluded warmups for the main process/map comparisons; a separate 15-round repeat after three warmups for suspect map cases. Current and frozen 2026-10-25 Axon executables run interleaved on the same VM. One-worker cases use CPU 0; four-worker compute uses CPUs 0–3. Timing and compilation/tests do not overlap. Binaries and timed inputs are VM-local.','',
        'Rust 1.98.1 optimized native executables from the prior run were verified against retained binary hashes and rerun unchanged. Go is rebuilt with 1.25.14; Bun is 1.3.13, matching the prior Bun version. Clang is 18.1.3. Axon remains statically linked with no interpreter, shared libraries or undefined imports.','',
        '## Current compute comparison','',
        'Median complete-process milliseconds, including launch/allocation/computation/destruction. Integer results agree exactly; N-body energies agree within relative tolerance 1e-9. Existing Axon/Rust/Go workload sources are unchanged. Layout, scheduling and implementations differ. Bun compute is a new standalone single-thread counterpart of the same equations; it is not reported as a four-worker implementation.','',
        '| Case | Workers | Previous Axon | Current Axon | Rust | Go | Bun |','|---|---:|---:|---:|---:|---:|---:|']
    for r in s['compute']:
        values=r['measurements'];cells=[f"{values[n]['ms']:.3f}" if n in values else '—' for n in ['previous','Axon','Rust','Go','Bun']]
        lines.append(f"| {r['case']} | {r['workers']} | "+' | '.join(cells)+' |')
    lines+=['',
        'Historical absolute rankings do not reproduce on this VM. For example, the exact frozen Mandelbrot executable now takes approximately 538 ms (one worker), versus 99.4 ms in the older Colima report; current Axon takes approximately 548 ms. That historical difference cannot be attributed to the new compiler code alone. The table above retains all current losses, and the paired old/current results isolate the incremental change in this environment.','',
        '## Dynamic JSON workflow','',
        'Whole-process milliseconds: construct varying JSON, fully parse it, read integer/UTF-8/array fields, checksum and release. This is not an isolated parser comparison. Rust uses serde_json::Value, Go uses encoding/json with map/slice values, Bun uses JSON.parse, and Axon uses its validated source/index representation. The Go counterpart is newly added; all outputs are checked against the same independent checksum.','',
        '| Documents | Previous Axon | Current Axon | Rust | Go | Bun |','|---:|---:|---:|---:|---:|---:|']
    for r in s['json']:lines.append('| '+r['case']+' | '+' | '.join(f"{r['measurements'][n]['ms']:.3f}" for n in ['previous','Axon','Rust','Go','Bun'])+' |')
    lines+=['','## Other library regression cases','','Internal append/sort/map-and-checksum phase milliseconds; process launch and output are excluded.','',
        '| Case | Previous Axon | Current Axon | Previous peak RSS MiB | Current peak RSS MiB |','|---|---:|---:|---:|---:|']
    for r in s['collections']:
        b,c=r['measurements']['previous'],r['measurements']['Axon'];lines.append(f"| {r['case']} | {b['ms']:.3f} | {c['ms']:.3f} | {b['peak_rss_mib']:.3f} | {c['peak_rss_mib']:.3f} |")
    lines+=['',
        'The initial nine-round complete 1M string-map case looked 6.2% slower, with broad overlapping ranges. The independent 15-round repeat instead measured 302.285 → 255.095 ms. Both datasets remain retained; a consistent slowdown direction is not established for that aggregate case. Its individual small-map and deletion regressions below are confirmed separately.','',
        'Generic `HashMap` is distinct from the compact byte/string map below. Generic-map peak RSS is 285.656 → 313.922 MiB (+9.9%). Its allocation requests drop from 10,549,982 to 3,000,019, while cumulative requested bytes increase from 336,491,465 to 358,357,023. Fewer requests do not imply lower peak memory.','',
        '## String-map comparison','',
        'Each phase includes decimal key construction and the ordinary public API. Reads validate every expected value and sum it; the final read has 50% misses after deleting even keys. Insert/update/delete and procfs memory pauses are outside read timers. Axon returns owned bytes; Rust/Go/Bun use their ordinary string APIs. Bun Map has no reserve API and is measured only in growing mode.','',
        '| Entries | Allocation | Implementation | Insert ms | Lookup ms | Update ms | Delete ms | Updated lookup ms | Mixed hit/miss lookup ms |','|---:|---|---|---:|---:|---:|---:|---:|---:|']
    for r in s['maps']:
        if not r['n']:continue
        for name,v in r['measurements'].items():
            lines.append(f"| {r['n']} | {'reserved' if r['reserved'] else 'growing'} | {name} | "+' | '.join(f"{v[phase]['ms']:.3f}" for phase in ['insert','lookup','update','delete','lookup_updated','lookup_remaining'])+' |')
    lines+=['','### Million-entry map memory','','Steady RSS is sampled with the complete original map live; peak is median process high-water after the workflow. Go/Bun explicitly collect before the steady sample, outside timing. Empty-map cases are retained as correctness checks, not sub-microsecond performance claims. The Axon byte-map 2-GiB arena limit is unchanged.','',
        '| Allocation | Implementation | Steady RSS MiB | Peak RSS MiB |','|---|---|---:|---:|']
    for r in s['maps']:
        if r['n']!=1000000:continue
        for name,v in r['measurements'].items():lines.append(f"| {'reserved' if r['reserved'] else 'growing'} | {name} | {v['steady']['rss_mib']:.3f} | {v['lookup_remaining']['peak_rss_mib']:.3f} |")
    lines+=['','## Independent regression confirmation','','Fifteen fresh measured shuffled pairs after three warmups. All full workflows and value/count checks still run. Slowdown is current/previous time. Intervals are paired-round bootstrap ratios of medians (20,000 resamples, 95%). Initial screening spans many cases; these unadjusted intervals describe this local sample, not a universal guarantee. A confirmed material screen requires >5% median slowdown and an interval wholly above 1.','',
        '| Case | Previous ms | Current ms | Change | Ratio interval | Result |','|---|---:|---:|---:|---|---|']
    for r in d['confirmation']:
        c=r['change'];lines.append(f"| {r['case']} | {r['before_ms']:.3f} | {r['after_ms']:.3f} | {(c['slowdown_ratio']-1)*100:+.1f}% | {c['ci95'][0]:.3f}–{c['ci95'][1]:.3f} | {c['classification']} |")
    lines+=['','## HTTP runtime','','Five fresh shuffled paired runs per scenario. Servers use CPU 0 or CPUs 0–3; load clients and sampler use CPUs 4–7. Each trial has a one-second warmup and two-second measurement. A validation-first Go client checks status, Content-Length and every complete Hello World body, and drains outstanding pipeline batches. All reported trials have zero I/O/response errors. Route validation also checks missing, stencil and N-body endpoints before load.','',
        'The first wrk attempt reported 39 timeout samples and was stopped. Its raw traces and partial measurements are preserved separately; none of its rates enter these tables. The accepted client protocol differs from historical wrk throughput, so compare versions within this run. These are closed-loop client-observed rates, potentially load-generator limited; latency percentiles are not measured. Bun retains one JavaScript handler loop in the four-CPU budget.','',
        '| Case | Previous Axon req/s | Current Axon req/s | Rust req/s | Go req/s | Bun req/s |','|---|---:|---:|---:|---:|---:|']
    for r in s['http']:lines.append('| '+r['case']+' | '+' | '.join(f"{r['measurements'][n]['rps']:,.0f}" for n in ['previous','Axon','Rust','Go','Bun'])+' |')
    lines+=['','| Case | Implementation | Server CPU µs/request | Peak aggregate PSS MiB |','|---|---|---:|---:|']
    for r in s['http']:
        for n,v in r['measurements'].items():lines.append(f"| {r['case']} | {n} | {v['cpu_us_per_request']:.3f} | {v['peak_pss_mib']:.3f} |")
    lines+=['','## Validation and evidence','','- 123 compiler unit tests pass in the native preparation workspace.','- Every compute/JSON/map run checks its output; every map phase checks complete counts and expected values.','- Actual measured current map, append and JSON executables pass execution in empty Linux roots containing only the executable.','- All current Axon executables pass undefined-symbol, ELF interpreter and shared-library audits. Python/LLVM remain build tools.','- Full source snapshots, exact binaries, build logs, tool versions, unfiltered samples, failed HTTP traces, bootstrap analysis and independent repeat are retained. No compiler/runtime/stdlib files were changed to obtain this rerun.','',
        'Artifacts: `.kernel-build/core-regression-2026-10-27/results/`. Main files: `measurements.json`, `analysis.json`, `confirmation/measurements.json`, `inventory.json`, `unit-tests.log`, `current-source/`, `baseline-source/`, `control-sources/` and `bin/`. Historical reports and artifacts remain unchanged.','']
    a.report.write_text('\n'.join(lines));(a.folder/'report.md').write_text('\n'.join(lines));print(a.report)

if __name__=='__main__':main()
