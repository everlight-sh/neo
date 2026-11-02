"""Reproducible compiler-source releases, containing no application examples."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
from .packages import VERSION

ROOT=Path(__file__).resolve().parents[1]


def bundle(destination,epoch=0):
    if epoch<0:raise ValueError('SOURCE_DATE_EPOCH must be nonnegative')
    files={}
    for directory,pattern in (('neoc','*.py'),('runtime','*.neo'),('stdlib','*.neo'),('docs','*.md')):
        for path in sorted((ROOT/directory).glob(pattern)):files[str(path.relative_to(ROOT))]=path.read_bytes()
    files['neo']=(ROOT/'neo').read_bytes()
    for name in ['skills.md',*sorted(p.name for p in ROOT.glob('LICENSE*'))]:files[name]=(ROOT/name).read_bytes()
    files['README.md']=(f'# Neo {VERSION}\n\nCompiler-source/tool bundle. Requires Python 3.11+, Clang/LLVM and a linker.\n\n'
        'Put `neo` on your PATH (a symlink works; install.sh does this), run `neo doctor` to check the tools,\n'
        'then `neo init app`, `cd app` and `neo run`. Give coding agents `skills.md` before they write code.\n'
        'The language contract and complete core examples are in `docs/language-v01.md`.\n'
        'Application examples and benchmark data are distributed separately.\n\n'
        'Linux ARM64/x86-64 executables use the kernel directly without runtime libraries.\n'
        'ARM64 macOS still requires the system libSystem load command.\n'
        'TLS is experimental and has not had an independent cryptographic audit.\n'
        'MANIFEST.json lists SHA-256 hashes for every payload file.\n').encode()
    files['VERSION']=(VERSION+'\n').encode()
    manifest={'version':VERSION,'format':1,'build_dependencies':['Python >=3.11','LLVM clang and linker'],'files':{name:hashlib.sha256(content).hexdigest() for name,content in sorted(files.items())}}
    files['MANIFEST.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    import tempfile
    fd,stage=tempfile.mkstemp(prefix='.neo-release-',dir=destination.parent);os.close(fd)
    try:
        with open(stage,'wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=epoch) as gz,tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT) as archive:
            for name,content in sorted(files.items()):
                item=tarfile.TarInfo('neo-'+VERSION+'/'+name);item.size=len(content);item.mode=0o755 if name=='neo' else 0o644
                item.mtime=epoch;item.uid=item.gid=0;item.uname=item.gname='';archive.addfile(item,io.BytesIO(content))
        os.replace(stage,destination)
    finally:
        if Path(stage).exists():Path(stage).unlink()
    return {'ok':True,'version':VERSION,'archive':str(destination.resolve()),'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'files':len(files),'epoch':epoch}


def command(args):print(json.dumps(bundle(args.output,int(os.environ.get('SOURCE_DATE_EPOCH','0'))),indent=2))
