#!/usr/bin/env python3
"""Prepare a VM-local, frozen language benchmark workspace before timing."""
import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args()
    root=a.source.resolve();work=a.workspace.resolve();work.mkdir(exist_ok=False)
    source=work/'current';source.mkdir();out=work/'results';out.mkdir();(out/'bin').mkdir()
    extensions={'.py','.neo','.go','.mod','.sum','.rs','.toml','.lock','.ts','.tsx','.lua','.json','.pem','.crt','.key','.txt','.md','.sh'}
    excluded={'__pycache__','.axon-build','.kernel-build','node_modules','results','target','.git','dist','build'}
    for folder in ['neoc','runtime','stdlib','examples','tests','bench','docs']:
        for parent,dirs,files in os.walk(root/folder):
            dirs[:]=[d for d in dirs if d not in excluded]
            for name in files:
                f=Path(parent)/name
                if f.suffix not in extensions:continue
                target=source/f.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
    for name in ['axon','neoc.sh','neo.toml','pyproject.toml']:
        if (root/name).is_file():shutil.copy2(root/name,source/name)
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    original=root/'.kernel-build/append-json-2026-10-25'
    manifest=json.loads((original/'source/sources.json').read_text())
    for name,digest in manifest.items():assert sha(original/'source'/name)==digest,('baseline source',name)
    shutil.copytree(original/'source',out/'baseline-source')
    metadata={}
    for name in ['core','maps','regressions']:
        metadata[name]=json.loads((original/name/'measurements.json').read_text())
        shutil.copyfile(original/name/'measurements.json',out/(name+'-baseline-measurements.json'))
    compute=root/'bench/usability/results/2026-10-25-132551-compute'
    metadata['compute']=json.loads((compute/'measurements.json').read_text());shutil.copyfile(compute/'measurements.json',out/'compute-baseline-measurements.json')
    http=root/'bench/http/results/2026-10-25-104406-native'
    metadata['http']=json.loads((http/'measurements.json').read_text());shutil.copyfile(http/'measurements.json',out/'http-baseline-measurements.json')
    copies={
        'previous-collections':original/'core/after-collections','previous-generic':original/'core/after-generic',
        'previous-json':original/'regressions/Axon-fixed-json','previous-map':original/'maps/Axon-after',
        'rust-map':original/'maps/Rust','rust-json':root/'bench/rust/target/release/usability',
        'previous-http':http/'bin/axon','rust-http':http/'bin/rust'}
    for kind in ['mandel','stencil','nbody']:
        copies['previous-'+kind]=compute/('axon-'+kind);copies['rust-'+kind]=root/'bench/rust/target/release'/kind
    expected={
        'previous-collections':metadata['core']['binary_sha256']['after-collections'],
        'previous-generic':metadata['core']['binary_sha256']['after-generic'],
        'previous-json':metadata['regressions']['binaries']['Axon-fixed-json']['sha256'],
        'previous-map':metadata['maps']['binaries']['Axon after']['sha256'],
        'rust-map':metadata['maps']['binaries']['Rust']['sha256'],
        'rust-json':metadata['regressions']['binaries']['Rust-json']['sha256'],
        'previous-http':metadata['http']['servers']['Axon']['sha256'],
        'rust-http':metadata['http']['servers']['Rust']['sha256']}
    for kind in ['mandel','stencil','nbody']:
        expected['previous-'+kind]=metadata['compute']['binary_sha256'][kind+'-Axon'];expected['rust-'+kind]=metadata['compute']['binary_sha256'][kind+'-Rust']
    for name,file in copies.items():
        assert sha(file)==expected[name],('frozen executable changed',name)
        shutil.copyfile(file,out/'bin'/name);(out/'bin'/name).chmod(0o755)
    env={**os.environ,'NEO_HOME':str(source),'PYTHONPATH':str(source),'GOWORK':'off','GOTOOLCHAIN':'local','CGO_ENABLED':'0','NEO_THREADS':'1','GOMAXPROCS':'1'}
    def command(cmd,name,cwd=source,extra=None):
        print('BUILD/CHECK',name,flush=True)
        r=subprocess.run(list(map(str,cmd)),cwd=cwd,env={**env,**(extra or {})},capture_output=True,text=True)
        (out/(name+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,(name,r.stdout[-1500:],r.stderr[-1500:]);return r.stdout
    command(['python3','-m','unittest','discover','-s','tests','-p','test_*.py'],'unit-tests')
    cases={'mandel':'examples/mandel.neo','stencil':'examples/stencil.neo','nbody':'examples/nbody.neo','json':'examples/library_bench.neo','collections':'tests/fixtures/language_bench.neo','generic':'tests/fixtures/generic_map_bench.neo','map':'bench/maps/workload.neo','http':'examples/http.neo'}
    for kind,file in cases.items():
        report=json.loads(command(['python3','-m','neoc','build',file,'-o',out/'bin'/('axon-'+kind),'--report'],'axon-'+kind))
        assert report['undefined_symbols']==[]
    for kind,file in [('collections','tests/fixtures/language_bench.neo'),('generic','tests/fixtures/generic_map_bench.neo')]:
        command(['python3','-m','neoc','build',file,'-o',out/'bin'/('axon-'+kind+'-profile'),'--report'],'axon-'+kind+'-profile',extra={'NEO_ALLOC_STATS':'1'})
        baseline=original/'core'/('after-'+kind+'-profile');shutil.copyfile(baseline,out/'bin'/('previous-'+kind+'-profile'));(out/'bin'/('previous-'+kind+'-profile')).chmod(0o755)
    for kind in ['mandel','stencil','nbody','http']:
        command(['go','build','-o',out/'bin'/('go-'+kind),'./'+kind],'go-'+kind,cwd=source/'bench/go')
    command(['go','build','-o',out/'bin/go-map',source/'bench/maps/go.go'],'go-map')
    command(['go','build','-o',out/'bin/go-json',source/'bench/core/json.go'],'go-json')
    audits={}
    for binary in (out/'bin').iterdir():
        header=command(['readelf','-h',binary],binary.name+'-elf')
        assert 'AArch64' in header,binary
        if binary.name.startswith(('axon-','previous-')):
            imports=command(['nm','-u',binary],binary.name+'-imports');segments=command(['readelf','-l',binary],binary.name+'-segments');dynamic=command(['readelf','-d',binary],binary.name+'-dynamic')
            assert not imports.strip() and 'INTERP' not in segments and 'NEEDED' not in dynamic
        audits[binary.name]={'sha256':sha(binary),'bytes':binary.stat().st_size}
    files={str(f.relative_to(source)):sha(f) for f in source.rglob('*') if f.is_file() and '__pycache__' not in f.parts and '.axon-build' not in f.parts}
    versions={name:command(cmd,'version-'+name).strip() for name,cmd in [('clang',['clang','--version']),('go',['go','version']),('bun',['bun','--version']),('kernel',['uname','-a']),('cpu',['lscpu'])]}
    versions['rust']='Frozen optimized executables from verified prior run: rustc 1.98.1 (48a229cea 2026-09-01); compiler not required to rerun unchanged binaries.'
    inventory={'workspace':str(work),'source_hashes':files,'binaries':audits,'versions':versions,'baseline_sources':manifest,'native_arch':os.uname().machine}
    (out/'inventory.json').write_text(json.dumps(inventory,indent=2));print('READY',work,flush=True)

if __name__=='__main__':main()
