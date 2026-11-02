#!/usr/bin/env python3
"""Instrument generated IR only; separate allocation counts from untraced timings."""
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def main():
    folder=ROOT/'.kernel-build/json-opt';results=[]
    for name,report in [('previous',folder/'baseline/build.json'),('optimized',folder/'build.json')]:
        data=json.loads(report.read_text());ir=Path(data['ir']).read_text()
        ir+='\n@json_profile_allocs = internal global i64 0, align 8\n'
        header='define ptr @ax_alloc(i64 %p_bytes) "no-builtins" {\nentry:'
        assert header in ir
        ir=ir.replace(header,header+'\n  %prof0 = load volatile i64, ptr @json_profile_allocs\n  %prof1 = add i64 %prof0, 1\n  store volatile i64 %prof1, ptr @json_profile_allocs')
        ir,n=re.subn(r'(  call void @ax_print_i64\(i64 %t\d+\))',r'  %profile_total = load volatile i64, ptr @json_profile_allocs\n  call void @ax_print_i64(i64 %profile_total)\n\1',ir);assert n==1
        file=folder/(name+'-allocations.ll');file.write_text(ir);binary=file.with_suffix('')
        subprocess.run(['clang','-O3','-nostdlib','-static','-Wl,-e,_start',str(file),'-o',str(binary)],check=True)
        result=subprocess.run([str(binary),'0','1000'],capture_output=True,text=True,check=True,env={**os.environ,'NEO_THREADS':'1'})
        allocations,checksum=map(int,result.stdout.split());assert checksum==513500
        results.append({'implementation':name,'documents':1000,'allocations':allocations,'checksum':checksum})
        print(name,allocations,'allocations / 1000 documents',flush=True)
    (folder/'allocation-profile.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
