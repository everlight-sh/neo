#!/usr/bin/env python3
"""Build and audit dependency-free application images for both Linux targets."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', default='colima-axon-bench')
    parser.add_argument('--tools', default='axon-kernel-bench-tools')
    args = parser.parse_args()
    docker = ['docker', '--context', args.context]
    out = ROOT/'.kernel-build/usability/images'
    metadata = {'images': [], 'valid': False}
    for arch, target, platform in [('arm64', 'aarch64-unknown-linux-gnu', 'linux/arm64'),
                                   ('x86_64', 'x86_64-unknown-linux-gnu', 'linux/amd64')]:
        for name in ('json-cli', 'notes', 'webhook'):
            folder = out/arch/name
            folder.mkdir(parents=True, exist_ok=True)
            binary = folder/'app'
            command = docker+['exec', '-w', '/axon', '-e', 'NEO_TARGET='+target, args.tools,
                              'python3', '-m', 'neoc', 'build', f'examples/{name}/main.neo',
                              '-o', '/axon/'+str(binary.relative_to(ROOT)), '--report']
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            (folder/'build.json').write_text(result.stdout+result.stderr)
            audit = {}
            for kind, tool in [('imports', ['nm', '-u']), ('headers', ['readelf', '-l']), ('dynamic', ['readelf', '-d'])]:
                value = subprocess.check_output(docker+['exec', args.tools, *tool, '/axon/'+str(binary.relative_to(ROOT))], text=True)
                (folder/(kind+'.txt')).write_text(value)
                assert not value.strip() if kind == 'imports' else 'INTERP' not in value and 'NEEDED' not in value
                audit[kind] = value
            (folder/'input.json').write_text('[{"id":1,"name":"café 🚀","score":2}]\n')
            (folder/'Dockerfile').write_text('FROM scratch\nCOPY app /server\nCOPY input.json /input.json\n'
                                            'USER 65532:65532\nENTRYPOINT ["/server"]\nCMD ["8080"]\n')
            tag = f'axon-usability-{name}-{arch}:20261024'
            result = subprocess.run(docker+['build', '--platform', platform, '-t', tag, str(folder)], capture_output=True, text=True, check=True)
            (folder/'image-build.log').write_text(result.stdout+result.stderr)
            info = json.loads(subprocess.check_output(docker+['image', 'inspect', tag], text=True))[0]
            metadata['images'].append({'name': name, 'architecture': arch, 'tag': tag, 'id': info['Id'],
                'binary_bytes': binary.stat().st_size, 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                'image_bytes': info['Size'], 'build_command': command, 'audit': audit})
            print('PASS built/audited', tag, flush=True)
    metadata['valid'] = True
    (out/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')


if __name__ == '__main__':
    main()
