#!/usr/bin/env python3
"""Run HTTP from an otherwise empty root filesystem (Linux container, root)."""
import argparse
import os
from pathlib import Path
import platform
import shlex
import shutil
import tempfile

from http_smoke import verify
from kernel_runtime_smoke import audit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    args = p.parse_args()
    assert platform.system() == 'Linux' and os.geteuid() == 0, 'Run inside the Linux test container as root'
    audit(args.binary.resolve())
    with tempfile.TemporaryDirectory(prefix='neo-empty-root-') as tmp:
        base = Path(tmp); root = base/'root'; root.mkdir()
        shutil.copy2(args.binary.resolve(), root/'http')
        wrapper = base/'launch'
        wrapper.write_text('#!/bin/sh\nexec chroot '+shlex.quote(str(root))+' /http "$@"\n')
        wrapper.chmod(0o755)
        assert [p.name for p in root.iterdir()] == ['http']
        verify(wrapper, workers=4)
        print('HTTP PASS from an empty root containing only the executable: no /lib, /usr, /proc or runtime files.', flush=True)


if __name__ == '__main__': main()
