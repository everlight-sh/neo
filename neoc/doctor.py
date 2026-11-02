"""`neo doctor`: can this machine build Neo programs? Reports the platform and
the tools the compiler calls, then builds and runs a one-line program."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

SUPPORTED = {('Linux', 'x86_64'), ('Linux', 'aarch64'), ('Darwin', 'arm64')}


def first_line(argv):
    try: result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError): return None
    lines = (result.stdout or result.stderr).splitlines()
    return lines[0].strip() if result.returncode == 0 and lines else None


def install_hint():
    if platform.system() == 'Darwin': return 'xcode-select --install'
    for manager, command in (('apt-get', 'sudo apt install clang lld binutils'), ('dnf', 'sudo dnf install clang lld binutils'),
                             ('pacman', 'sudo pacman -S clang lld binutils'), ('apk', 'sudo apk add clang lld binutils')):
        if shutil.which(manager): return command
    return 'install clang, lld and binutils with your package manager'


def smoke():
    """Build and run hello world; None on success, else what went wrong."""
    with tempfile.TemporaryDirectory(prefix='neo-doctor-') as tmp:
        source = Path(tmp)/'hello.neo'; binary = Path(tmp)/'hello'
        source.write_text('fn main () -> Arr u8 _ = "ok\\n"\n')
        built = subprocess.run([sys.executable, '-m', 'neoc', 'build', str(source), '-o', str(binary), '--no-cache'], capture_output=True, text=True)
        if built.returncode != 0:
            try: return 'build failed: ' + '; '.join(e.get('msg', '') for e in json.loads(built.stdout)['errors'])[:500]
            except (ValueError, KeyError, TypeError): return 'build failed: ' + (built.stderr or built.stdout).strip()[-500:]
        ran = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
        return None if ran.returncode == 0 and ran.stdout == 'ok\n' else f'the built program printed {ran.stdout!r} (exit {ran.returncode})'


def command(args):
    from .packages import VERSION
    system, machine = platform.system(), platform.machine()
    rows = []
    def row(name, status, detail): rows.append((name, status, detail))
    row('platform', 'ok' if (system, machine) in SUPPORTED else 'unsupported',
        f'{system} {machine}' + ('' if (system, machine) in SUPPORTED else ' (Neo supports x86-64 and ARM64 Linux, ARM64 macOS)'))
    row('python', 'ok', sys.version.split()[0] + ' at ' + sys.executable)
    clang = first_line(['clang', '--version'])
    row('clang', 'ok' if clang else 'missing', clang or 'not found on PATH')
    linker = shutil.which('ld')
    row('linker', 'ok' if linker else 'missing', linker or 'ld not found on PATH')
    lld = first_line(['ld.lld', '--version'])
    row('lld', 'ok' if lld else 'optional', lld or 'not found; needed only to build for another CPU (--target)')
    missing = [name for name, status, _ in rows if status in ('missing', 'unsupported')]
    if not missing:
        problem = smoke()
        row('build', 'failed' if problem else 'ok', problem or 'built and ran hello world')
    print('Neo ' + VERSION)
    for name, status, detail in rows: print(f'  {status:<11} {name:<9} {detail}')
    if any(status in ('missing', 'unsupported', 'failed') for _, status, _ in rows):
        if {'clang', 'linker'} & set(missing): print('Install the missing tools with: ' + install_hint())
        raise SystemExit(1)
    print('Ready: neo init app && cd app && neo run')
