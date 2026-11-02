#!/usr/bin/env python3
"""A 300-opcode else-if dispatch compiles, proves its handlers' bounds and runs.

Each arm of an else-if chain adds a disjunctive `op != k` fact. Before the
relevance fallback, arms past the 8th could only discharge obligations that
were literally among the facts; before the large compiler stack, about 110
arms exceeded CPython's recursion limit while parsing."""
import json,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build,ROOT

ARMS=300

def source():
    arms=[f'if op == {k} then (if sp + {k%5+1} < n then wrapping_add(st[sp + {k%5+1}], {k}) else {k})' for k in range(ARMS)]
    return ('fn step(st : Arr i64 n, sp : i64{sp >= 0}, op : i64) -> i64\n  = '+'\n    else '.join(arms)+'\n    else -1\n'
            'fn main (iterations : i64{iterations >= 0}) -> i64\n'
            '  = let st = arr(i in 0..8) i * 100 in\n'
            f'    loop(i = 0, total = 0) while i >= 0 && i < iterations next(i + 1, wrapping_add(total, step(st, i % 7, i % {ARMS+1}))) yield total\n')

def model(iterations):
    st=[i*100 for i in range(8)];total=0
    for i in range(iterations):
        sp,op=i%7,i%(ARMS+1)
        if op<ARMS:
            j=sp+op%5+1;value=st[j]+op if j<8 else op
        else:value=-1
        total+=value
    return total

def main():
    with tempfile.TemporaryDirectory(prefix='neo-deep-dispatch-') as temp:
        path=Path(temp)/'dispatch.neo';path.write_text(source())
        binary=Path(temp)/'dispatch';report=build(str(path),binary)
        assert report['summary']['unproven']==0,report['summary']
        assert any(s['cases']==ARMS for s in report['switches']),report['switches']
        for iterations in [0,1,500,4000]:
            result=subprocess.run(RUNNER+[str(binary),str(iterations)],capture_output=True,text=True,timeout=60)
            assert result.returncode==0 and result.stdout==str(model(iterations))+'\n',(iterations,result.stdout,model(iterations),result.stderr)
    print(f'PASS {ARMS}-arm dispatch: parsed, every handler bound proven, one {ARMS}-case switch, results match the model',flush=True)

if __name__=='__main__':main()
