#!/usr/bin/env python3
"""Build minimal ARM64 runtime images using the existing Linux tool container."""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--context', default='colima-axon-bench')
    p.add_argument('--tools', default='axon-kernel-bench-tools')
    p.add_argument('--reuse-binaries', action='store_true', help='Reuse already built binaries; still audit and rebuild images')
    args = p.parse_args()
    docker = ['docker', '--context', args.context]
    out = ROOT/'.kernel-build/docker-ssr'; out.mkdir(parents=True, exist_ok=True)
    def run(command, **kwargs):
        result = subprocess.run([str(a) for a in command], cwd=ROOT, capture_output=True, text=True, **kwargs)
        if result.returncode: raise RuntimeError(result.stdout+result.stderr)
        return result.stdout+result.stderr
    commands = [
        docker+['exec', args.tools, 'bun', 'run', '/axon/examples/jsx-ssr/build.ts', '/axon/.kernel-build/docker-ssr/axon'],
        docker+['exec', '-w', '/axon/bench/rust', args.tools, 'env', 'CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER=musl-gcc',
            'RUSTFLAGS=-C target-feature=+crt-static -C strip=symbols', 'cargo', 'build', '--release', '--locked', '--target', 'aarch64-unknown-linux-musl', '--bin', 'ssr_container'],
        docker+['exec', '-w', '/axon/bench/rust', args.tools, 'env', 'RUSTFLAGS=-C strip=symbols',
            'cargo', 'build', '--release', '--locked', '--target', 'aarch64-unknown-linux-gnu', '--bin', 'ssr_container'],
    ]
    for index, command in enumerate([] if args.reuse_binaries else commands):
        print('Building', 'Axon' if index == 0 else 'Rust', flush=True)
        (out/f'build-{index}.log').write_text(run(command))
    shutil.copy2(ROOT/'bench/rust/target/aarch64-unknown-linux-musl/release/ssr_container', out/'rust')
    shutil.copy2(ROOT/'bench/rust/target/aarch64-unknown-linux-gnu/release/ssr_container', out/'rust-gnu')
    for name in ('axon', 'rust'):
        binary = '/axon/.kernel-build/docker-ssr/'+name
        for kind, flags in (('program-headers', ['-l']), ('dynamic', ['-d'])):
            result = run(docker+['exec', args.tools, 'readelf', *flags, binary])
            (out/f'{name}-{kind}.txt').write_text(result)
            assert 'INTERP' not in result and 'NEEDED' not in result, result
        if name == 'axon': assert not run(docker+['exec', args.tools, 'nm', '-u', binary]).strip()
    context = out/'context'; context.mkdir(exist_ok=True)
    for file in HERE.iterdir():
        if file.is_file(): shutil.copy2(file, context/file.name)
    for name in ('axon', 'rust'): shutil.copy2(out/name, context/name)
    gnu_root = context/'rust-gnu-rootfs'; gnu_root.mkdir(exist_ok=True)
    shutil.copy2(out/'rust-gnu', gnu_root/'server')
    linked = run(docker+['exec', args.tools, 'ldd', '/axon/.kernel-build/docker-ssr/rust-gnu'])
    (out/'rust-gnu-ldd.txt').write_text(linked)
    for library in sorted(set(re.findall(r'/[^\s()]+', linked))):
        target = gnu_root/library.lstrip('/'); target.parent.mkdir(parents=True, exist_ok=True)
        run(docker+['cp', '-L', args.tools+':'+library, str(target)])
    for name in ('page.tsx', 'reference.tsx'):
        shutil.copy2(ROOT/'examples/jsx-ssr'/name, context/name)
    images = {}
    specs = [('Axon JSX', 'axon', 'Dockerfile.axon', None), ('Rust Hyper', 'rust', 'Dockerfile.rust', None),
        ('Rust Hyper glibc', 'rust-gnu', 'Dockerfile.rust-gnu', None),
        ('Bun direct', 'bun-direct', 'Dockerfile.bun', 'direct'), ('Bun React', 'bun-react', 'Dockerfile.bun', 'react')]
    for label, slug, dockerfile, target in specs:
        tag = f'axon-compare-{slug}:20261023'
        command = docker+['build', '--platform', 'linux/arm64', '-f', str(context/dockerfile), '-t', tag]
        if target: command += ['--target', target]
        command += [str(context)]
        print('Image:', label, flush=True)
        (out/f'build-image-{slug}.log').write_text(run(command))
        info = json.loads(run(docker+['image', 'inspect', tag]))[0]
        cid = run(docker+['create', tag]).strip()
        try:
            process = subprocess.Popen(docker+['export', cid], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with tarfile.open(fileobj=process.stdout, mode='r|') as tar:
                payload = sum(member.size for member in tar if member.isfile() and member.name.lstrip('./') not in
                    ('.dockerenv', 'etc/hostname', 'etc/hosts', 'etc/resolv.conf'))
            error = process.stderr.read(); assert process.wait() == 0, error
        finally: run(docker+['rm', cid])
        archive = out/f'{slug}.docker-save.tar.gz'
        with archive.open('wb') as f, gzip.GzipFile(fileobj=f, mode='wb', mtime=0) as z:
            process = subprocess.Popen(docker+['image', 'save', tag], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            shutil.copyfileobj(process.stdout, z, 1024*1024)
            error = process.stderr.read(); assert process.wait() == 0, error
        images[label] = {'tag': tag, 'id': info['Id'], 'engine_reported_image_bytes': info['Size'], 'rootfs_file_bytes': payload,
            'gzip_docker_save_bytes': archive.stat().st_size, 'architecture': info['Architecture'], 'inspect': info}
    files = list(HERE.glob('*')) + [ROOT/'bench/rust/Cargo.toml', ROOT/'bench/rust/Cargo.lock', ROOT/'bench/rust/src/ssr_container.rs',
        ROOT/'examples/jsx-ssr/page.tsx', ROOT/'examples/jsx-ssr/compile.ts', ROOT/'examples/jsx-ssr/html.neo',
        ROOT/'examples/jsx-ssr/server.neo', ROOT/'examples/jsx-ssr/build.ts'] + list((ROOT/'runtime').glob('*.neo')) + list((ROOT/'neoc').glob('*.py'))
    metadata = {'images': images, 'source_sha256': {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.is_file()},
        'binary_sha256': {name: hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('axon', 'rust', 'rust-gnu')},
        'rustc': run(docker+['exec', args.tools, 'rustc', '--version']).strip(),
        'clang': run(docker+['exec', args.tools, 'clang', '--version']).splitlines()[0],
        'musl': run(docker+['exec', args.tools, 'dpkg-query', '-W', 'musl', 'musl-dev']).strip(),
        'bun_base': json.loads(run(docker+['image', 'inspect', 'oven/bun:1.3.13-alpine']))[0], 'build_commands': commands}
    (out/'images.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print('Manifest:', out/'images.json', flush=True)


if __name__ == '__main__': main()
