#!/usr/bin/env python3
"""SIMD array edges/ownership, checked masks, and kernel worker ABI/fallback."""
import ctypes
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import tempfile

from kernel_runtime_smoke import audit

ROOT = Path(__file__).resolve().parents[1]
RUNNER = shlex.split(os.environ.get('NEO_RUNNER',''))

def rem(x): return (abs(x) % 1000003) * (-1 if x < 0 else 1)

def reference(n, seed):
    a=[rem(seed+i) for i in range(n)]
    b=[a[i] if i < 3 or i+2 >= n else rem(a[i-3]+3*a[i]+a[i+2]) for i in range(n)]
    return sum(b[i] if i==0 or i+1==n else a[i-1]-b[i+1] for i in range(n))

def deny_clone():
    # Inject a genuine kernel EAGAIN, without a production-only testing hook.
    class Filter(ctypes.Structure):
        _fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint)]
    class Program(ctypes.Structure):
        _fields_=[('len',ctypes.c_ushort),('filter',ctypes.POINTER(Filter))]
    number=220 if platform.machine() in ('aarch64','arm64') else 56
    instructions=(Filter*4)(Filter(0x20,0,0,0),Filter(0x15,0,1,number),Filter(0x06,0,0,0x50000|11),Filter(0x06,0,0,0x7fff0000))
    program=Program(4,instructions)
    libc=ctypes.CDLL(None,use_errno=True)
    assert libc.prctl(38,1,0,0,0)==0
    assert libc.prctl(22,2,ctypes.byref(program),0,0)==0

def main():
    with tempfile.TemporaryDirectory(prefix='neo-vector-arrays-') as tmp:
        for vector in ('0','1'):
            binary=Path(tmp)/('arrays-'+vector)
            r=subprocess.run(['python3','-m','neoc','build','tests/fixtures/vector_arrays.neo','--report','-o',str(binary)],cwd=ROOT,
                capture_output=True,text=True,env={**os.environ,'NEO_VEC':vector},check=True)
            report=json.loads(r.stdout);assert bool(report['vector_arrays'])==(vector=='1')
            allocating=[region for region in report['parallel_regions'] if region['fn']=='main' and region['pos'][0]==22 and region['kind']=='arr']
            assert allocating and all(region['dispatcher']=='ax_par_for' for region in allocating)
            audit(binary)
            count=0
            for n in (0,1,2,3,4,5,7,8,9,15,16,17,31,32,33,65,129,1023,1024,1025,4097):
                for seed in (0,1,-1,37,-999999):
                    for workers in ('1','4'):
                        r=subprocess.run(RUNNER+[str(binary),str(n),str(seed),'0'],capture_output=True,text=True,check=True,timeout=15,env={**os.environ,'NEO_THREADS':workers})
                        assert int(r.stdout)==reference(n,seed),(vector,n,seed,workers,r.stdout,r.stderr)
                        count+=1
            for workers in ('1','4'):
                for n in (0,1,3,4,5,12,13):
                    r=subprocess.run(RUNNER+[str(binary),str(n),str((1<<63)-1),'1'],capture_output=True,text=True,check=True,timeout=15,env={**os.environ,'NEO_THREADS':workers})
                    assert r.stdout.strip()=='0',(vector,workers,n,r.stdout,r.stderr)
                for start in (-(1<<63),-(1<<63)+3,(1<<63)-101,(1<<63)-6):
                    for n in (0,1,3,4,5,17,100):
                        if start+n > (1<<63)-1:continue
                        expected=sum((abs(i)%17)*(-1 if i<0 else 1) for i in range(start,start+n))
                        r=subprocess.run(RUNNER+[str(binary),str(n),str(start),'3'],capture_output=True,text=True,check=True,timeout=15,env={**os.environ,'NEO_THREADS':workers})
                        assert int(r.stdout)==expected,(vector,workers,start,n,r.stdout,r.stderr)
                for n in (14,1024,4097,262145):
                    r=subprocess.run(RUNNER+[str(binary),str(n),str((1<<63)-1),'1'],capture_output=True,text=True,timeout=15,env={**os.environ,'NEO_THREADS':workers})
                    assert r.returncode!=0 and 'overflow' in r.stderr,(vector,workers,n,r.stdout,r.stderr)
                r=subprocess.run(RUNNER+[str(binary),'4097','0','2'],capture_output=True,text=True,check=True,timeout=15,env={**os.environ,'NEO_THREADS':workers})
                assert int(r.stdout)==4097*4097
            r=subprocess.run(RUNNER+[str(binary),'262145','37','0'],capture_output=True,text=True,check=True,timeout=15,env={**os.environ,'NEO_THREADS':'4'})
            assert int(r.stdout)==reference(262145,37)
            if platform.system()=='Linux' and not RUNNER:
                r=subprocess.run([str(binary),'262145','37','0'],preexec_fn=deny_clone,capture_output=True,text=True,timeout=15,env={**os.environ,'NEO_THREADS':'4'})
                assert r.returncode==0 and int(r.stdout)==reference(262145,37),(r.stdout,r.stderr)
            print(f'NEO_VEC={vector}: {count} affine-load/negative-origin/empty-interior/float cases; masked overflow, near-i64-limit induction, allocating fallback PASS',flush=True)
            if platform.system()=='Linux' and not RUNNER:print('Injected clone EAGAIN: sequential fallback PASS',flush=True)
        if platform.system()=='Linux' and not RUNNER:
            binary=Path(tmp)/'worker-abi'
            subprocess.run(['python3','-m','neoc','build','tests/fixtures/shared_worker_abi.neo','-o',str(binary)],cwd=ROOT,check=True)
            audit(binary)
            for _ in range(20):
                r=subprocess.run([str(binary)],capture_output=True,text=True,check=True,timeout=15)
                assert r.stdout.strip()=='276',(r.stdout,r.stderr)
            print('Native raw-clone worker creation, callback ABI, shared writes and join: 20 runs PASS',flush=True)

if __name__=='__main__':main()
