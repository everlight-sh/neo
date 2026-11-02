"""Names from before the language was called Neo, still used by the sibling
projects: `.ax` sources, `axon.toml` and `axon.lock`, `axon` code fences in doc
tests, `.axon-build` caches and `AXON_*` variables. Once those projects are
migrated, delete this module, `./axon`, the runtime's rt_getenv_legacy and the
fallbacks that use them."""
import os
from pathlib import Path

SUFFIXES = ('.neo', '.ax')
MANIFESTS = ('neo.toml', 'axon.toml')
LOCKS = ('neo.lock', 'axon.lock')
IGNORED = ('.axon-build', '.axon')
TEST_GLOBS = ['tests/*_test.neo', 'tests/*_test.ax']
FENCE = r'```(?:neo|axon)\n'


def existing(root, names):
    """root/name for the first of names present, else for the first name."""
    return next((root/name for name in names if (root/name).is_file()), root/names[0])


def source(base):
    """base.neo, or base.ax when only that exists."""
    return next((path for path in (Path(str(base)+suffix) for suffix in SUFFIXES) if path.is_file()), Path(str(base)+SUFFIXES[0]))


def tool(data):
    tools = data.get('tool', {})
    return tools.get('neo', tools.get('axon', {}))


def build_dir(path):
    """Beside .ax sources or an axon.toml project the cache keeps its old name,
    which those projects already ignore."""
    path = Path(path)
    old = path.suffix == '.ax' or (path.is_dir() and not (path/MANIFESTS[0]).is_file() and (path/MANIFESTS[1]).is_file())
    return '.axon-build' if old else '.neo-build'


def mirror_environment():
    for key, value in list(os.environ.items()):
        if key.startswith('AXON_'): os.environ.setdefault('NEO_'+key[5:], value)
