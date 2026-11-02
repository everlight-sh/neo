#!/usr/bin/env python3
"""Native static-language/crypto/TLS checks in roots without libraries/tools."""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
from kernel_runtime_smoke import audit
from tls_language import certificates,peer


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--kernel',required=True,type=Path);parser.add_argument('--crypto',required=True,type=Path);parser.add_argument('--tls',required=True,type=Path)
    args=parser.parse_args();assert platform.system()=='Linux' and os.geteuid()==0 and not os.environ.get('NEO_RUNNER')
    for binary in (args.kernel,args.crypto,args.tls):audit(binary.resolve())
    with tempfile.TemporaryDirectory(prefix='neo-language-empty-root-') as tmp:
        base=Path(tmp)
        for name in ('kernel','crypto'):
            root=base/name;root.mkdir();shutil.copy2(getattr(args,name).resolve(),root/'run')
            data=bytes(range(256))*17 if name=='crypto' else None
            result=subprocess.run(['chroot',str(root),'/run']+(['0'] if name=='crypto' else []),input=data,capture_output=True,timeout=10)
            assert result.returncode==0,result.stderr
            assert result.stdout==(hashlib.sha256(data).digest() if data is not None else b'language kernel OK\n')
            assert sorted(p.name for p in root.iterdir())==['run']
        fixtures=base/'certificates';fixtures.mkdir();certificates(fixtures)
        root=base/'tls';root.mkdir();shutil.copy2(args.tls.resolve(),root/'run');shutil.copy2(fixtures/'ca.der',root/'trust.der')
        with peer(fixtures) as (port,received):
            result=subprocess.run(['chroot',str(root),'/run',str(port),'/trust.der','localhost'],capture_output=True,timeout=10)
            assert result.returncode==0 and result.stdout==b'secure echo\n',(result.stdout,result.stderr)
        assert sorted(p.name for p in root.iterdir())==['run','trust.der']
    print('PASS empty-root language/RNG/futex and SHA-256: executable only; TLS: executable plus explicit trust-anchor data, no libraries or tools',flush=True)


if __name__=='__main__':main()
