#!/usr/bin/env python3
"""Freeze all three Axon versions before the core-fix comparison."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--before-workspace',type=Path,required=True);a=p.parse_args()
    subprocess.run(['python3',str(a.source/'bench/core/prepare_regression.py'),'--source',str(a.source),'--workspace',str(a.workspace)],check=True)
    out=a.workspace/'results';bins=out/'bin';inventory=json.loads((out/'inventory.json').read_text())
    before=json.loads((a.before_workspace/'results/inventory.json').read_text());inventory['before_inventory']=before
    for name,details in before['binaries'].items():
        if not name.startswith('axon-'):continue
        f=a.before_workspace/'results/bin'/name
        assert hashlib.sha256(f.read_bytes()).hexdigest()==details['sha256'],name
        target=bins/name.replace('axon-','before-',1);shutil.copyfile(f,target);target.chmod(0o755)
        inventory['binaries'][target.name]=details
    shutil.copytree(a.before_workspace/'current',out/'before-source',ignore=shutil.ignore_patterns('__pycache__','.axon-build','.kernel-build'))
    for name,digest in before['source_hashes'].items():
        assert hashlib.sha256((out/'before-source'/name).read_bytes()).hexdigest()==digest,name
    subprocess.run(['go','build','-o',str(bins/'http-load'),str(a.workspace/'current/bench/core/http_load.go')],check=True)
    f=bins/'http-load';inventory['binaries']['http-load']={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}
    (out/'inventory.json').write_text(json.dumps(inventory,indent=2))
    print('THREE AXON VERSIONS FROZEN',flush=True)

if __name__=='__main__':main()
