import os,subprocess,sys,time,statistics
# ab.py ROUNDS CPUS THREADS name=cmd... : interleaved wall-time medians (ms) and ranges
rounds,cpus,threads=int(sys.argv[1]),sys.argv[2],sys.argv[3]
vs=[a.split('=',1) for a in sys.argv[4:]]
env={**os.environ,'NEO_THREADS':threads,'ZIG_THREADS':threads,'RAYON_NUM_THREADS':threads}
runs={n:[] for n,_ in vs}; outs={n:set() for n,_ in vs}
for r in range(rounds+1):
    order=vs if r%2==0 else vs[::-1]
    for n,c in order:
        t0=time.perf_counter();p=subprocess.run(['taskset','-c',cpus]+c.split(),capture_output=True,text=True,env=env);t=(time.perf_counter()-t0)*1000
        assert p.returncode==0,(c,p.stderr)
        if r>0: runs[n].append(t); outs[n].add(p.stdout.strip())
for n,_ in vs: print(f"  {n:10s} median {statistics.median(runs[n]):9.1f} ms  range {min(runs[n]):9.1f}-{max(runs[n]):9.1f}  out {sorted(outs[n])}",flush=True)
