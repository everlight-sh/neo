#!/usr/bin/env python3
"""Independent N-body numerics, worker thresholds, safe dispatch and fallback."""
import json,math,os,platform,shlex,subprocess,tempfile
from pathlib import Path
from kernel_runtime_smoke import audit
from vector_arrays_smoke import deny_clone
ROOT=Path(__file__).resolve().parents[1]
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))

def reference(n,steps):
    bodies=[[(i*2654435761%1009)/1009,(i*40503%1013)/1013,(i*69069%1019)/1019,0.,0.,0.,1/n] for i in range(n)]
    for _ in range(steps):
        updated=[]
        for b in bodies:
            ax=ay=az=0.
            for o in bodies:
                dx,dy,dz=o[0]-b[0],o[1]-b[1],o[2]-b[2];d2=dx*dx+dy*dy+dz*dz+.01;inv=o[6]/(d2*math.sqrt(d2))
                ax+=dx*inv;ay+=dy*inv;az+=dz*inv
            vx,vy,vz=b[3]+ax*.001,b[4]+ay*.001,b[5]+az*.001
            updated.append([b[0]+vx*.001,b[1]+vy*.001,b[2]+vz*.001,vx,vy,vz,b[6]])
        bodies=updated
    energy=0.
    for i,b in enumerate(bodies):
        potential=0.
        for j,o in enumerate(bodies):
            if i!=j:
                dx,dy,dz=o[0]-b[0],o[1]-b[1],o[2]-b[2];potential+=b[6]*o[6]/math.sqrt(dx*dx+dy*dy+dz*dz+.01)
        energy+=.5*b[6]*(b[3]**2+b[4]**2+b[5]**2)-.5*potential
    return energy

def main():
    with tempfile.TemporaryDirectory(prefix='neo-nbody-workers-') as tmp:
        binary=Path(tmp)/'nbody';r=subprocess.run(['python3','-m','neoc','build','examples/nbody.neo','-o',str(binary),'--report'],cwd=ROOT,capture_output=True,text=True,check=True)
        report=json.loads(r.stdout);audit(binary)
        if 'linux' in report.get('target','') or platform.system()=='Linux':
            assert report['parallel_regions'] and all(region['dispatcher']=='ax_par_for_shared' for region in report['parallel_regions']),report['parallel_regions']
        cases=[(1,0),(2,3),(7,0),(31,3),(257,2),(1023,0),(1024,2),(1025,1)]
        for n,steps in cases:
            expected=reference(n,steps)
            for workers in ('1','4'):
                r=subprocess.run(RUNNER+[str(binary),str(n),str(steps)],env={**os.environ,'NEO_THREADS':workers},capture_output=True,text=True,check=True,timeout=20)
                assert math.isclose(float(r.stdout),expected,rel_tol=1e-10,abs_tol=1e-12),(n,steps,workers,r.stdout,expected)
        if platform.system()=='Linux' and not RUNNER:
            r=subprocess.run([str(binary),'1024','2'],env={**os.environ,'NEO_THREADS':'4'},capture_output=True,text=True,check=True,timeout=20,preexec_fn=deny_clone)
            assert math.isclose(float(r.stdout),reference(1024,2),rel_tol=1e-10,abs_tol=1e-12)
            print('PASS record worker kernel EAGAIN fallback',flush=True)
    print('PASS N-body: independent Python model, 1/4 workers, odd sizes and 1024 dispatch threshold; static dependency audit',flush=True)
if __name__=='__main__':main()
