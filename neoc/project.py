"""Local projects, native test executables and conservative formatting."""
from argparse import Namespace
import contextlib
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import subprocess
import sys
import tomllib
from . import legacy, syntax as S


def manifest(path='.'):
    path=Path(path).resolve()
    file=path if path.name in legacy.MANIFESTS else legacy.existing(path,legacy.MANIFESTS)
    if not file.is_file(): raise ValueError('no neo.toml at '+str(file))
    return file.parent,tomllib.loads(file.read_text())


def entry(file=None):
    if file:return str(Path(file).resolve())
    root,data=manifest()
    return str(root/data.get('package',{}).get('entry','src/main.neo'))


def build_options(file,output=None,no_cache=False):
    return Namespace(file=str(file),output=str(output) if output else None,no_cache=no_cache,
                     allow_unproven=False,emit_llvm=False,report=False)


def init(args):
    root=Path(args.path)
    if root.exists() and any(root.iterdir()):raise ValueError('init requires an empty directory')
    (root/'src').mkdir(parents=True,exist_ok=True)
    name=re.sub('[^A-Za-z0-9_-]','-',root.resolve().name)
    if not name[:1].isalpha():name='neo-'+name
    (root/'neo.toml').write_text('[package]\nname = '+json.dumps(name)+'\nversion = "0.1.0"\nentry = "src/main.neo"\n')
    (root/'src/main.neo').write_text('fn main () -> Arr u8 _ = "Hello, Neo!\\n"\n')
    print('Created '+str(root.resolve()))


def run(args):
    from .cli import build
    file=entry(None if args.file=='__project__' else args.file)
    output=Path(file).parent/legacy.build_dir(file)/'run'
    with contextlib.redirect_stdout(sys.stderr): report=build(build_options(file,output))
    print('neo: build '+report['build']['cache'],file=sys.stderr)
    command=shlex.split(os.environ.get('NEO_RUNNER',''))+[str(output)]+args.arguments
    if args.arguments[:1]==['--']:command=shlex.split(os.environ.get('NEO_RUNNER',''))+[str(output)]+args.arguments[1:]
    raise SystemExit(subprocess.call(command))


def test(args):
    from .cli import build, target_triple
    root,data=manifest(args.path)
    config=legacy.tool(data);cache=root/legacy.build_dir(root)
    failed=0;count=0
    if config.get('python-tests'):
        code=subprocess.call([sys.executable,'-m','unittest','discover','-s',str(root/config['python-tests']),'-p','test_*.py'],cwd=root)
        failed+=bool(code)
    tests=list(data.get('test',[]))
    for pattern in config.get('doc-tests',[]):
        for source in sorted(root.glob(pattern)):
            for index,match in enumerate(re.finditer(legacy.FENCE+r'(.*?)```\s*```text\n(.*?)```',source.read_text(),re.S)):
                code,expected=match.groups()
                file=cache/'docs'/(source.stem+'-'+str(index)+'.neo');file.parent.mkdir(parents=True,exist_ok=True);file.write_text(code)
                tests.append({'name':'doc-'+source.stem+'-'+str(index),'file':str(file),'stdout':expected})
    for pattern in config.get('test-globs',legacy.TEST_GLOBS):
        for source in sorted(root.glob(pattern)):
            tokens=S.lex(source.read_text())
            names=[tokens[i+1].text for i,t in enumerate(tokens[:-1]) if t.kind=='KW' and t.text=='fn' and tokens[i+1].text.startswith('test_')]
            if not names:continue
            body='noop()'
            for name in reversed(names):body='check '+name+'() in '+body
            digest=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
            wrapper=cache/'tests'/(source.stem+'-'+digest+'.neo');wrapper.parent.mkdir(parents=True,exist_ok=True)
            wrapper.write_text('import '+json.dumps(str(source))+'\neffect fn main () -> unit = '+body+'\n')
            tests.append({'name':str(source.relative_to(root)),'file':str(wrapper),'stdout':''})
    for case in tests:
        count+=1
        try:
            file=(root/case['file']).resolve();output=cache/'test-bin'/target_triple()/case['name'].replace('/','-')
            if case.get('reject'):
                result=subprocess.run([sys.executable,'-m','neoc','check',str(file)],capture_output=True,text=True)
                assert result.returncode!=0 and case.get('diagnostic','') in result.stdout,result.stdout
            else:
                with contextlib.redirect_stdout(sys.stderr):build(build_options(file,output))
                command=shlex.split(os.environ.get('NEO_RUNNER',''))+[str(output)]+list(map(str,case.get('args',[])))
                result=subprocess.run(command,capture_output=True,text=True,timeout=case.get('timeout',30),
                    env={**os.environ,'NEO_THREADS':'1',**case.get('env',{})})
                assert result.returncode==case.get('exit',0),(result.returncode,result.stderr)
                if 'stdout' in case:assert result.stdout==case['stdout'],(result.stdout,case['stdout'])
            print('PASS',case['name'],flush=True)
        except (Exception,SystemExit) as exc:
            failed+=1;print('FAIL',case['name'],str(exc),file=sys.stderr,flush=True)
    if config.get('integration') and not args.unit_only:
        failed+=bool(subprocess.call([sys.executable,str(root/config['integration'])],cwd=root))
    print(f'neo test: {count} native cases, {failed} failed',flush=True)
    if failed:raise SystemExit(1)


def formatted(source):
    from .formatter import formatted as format_source
    return format_source(source)


def fmt(args):
    paths=[]
    for value in args.paths or ['.']:
        path=Path(value)
        paths.extend(sorted(p for suffix in legacy.SUFFIXES for p in path.rglob('*'+suffix)) if path.is_dir() else [path])
    changed=[]
    for path in paths:
        if any(p in ('.neo-build',*legacy.IGNORED,'.kernel-build','node_modules','target') for p in path.parts):continue
        source=path.read_text()
        try:output=formatted(source)
        except S.SyntaxError_ as exc:raise ValueError(str(path)+': '+str(exc)) from exc
        if source!=output:
            changed.append(str(path))
            if not args.check:path.write_text(output)
    for path in changed:print(path)
    if args.check and changed:raise SystemExit(1)
