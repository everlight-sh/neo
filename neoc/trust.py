"""Where a source file lives. The shipped runtime and standard library are the
audited boundary several passes ask about, once per function or operation.
Resolving a path walks the filesystem, so answers are memoised per path."""
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT/'runtime'
STDLIB = ROOT/'stdlib'


@lru_cache(maxsize=None)
def resolved(path) -> Path: return Path(path).resolve()


@lru_cache(maxsize=None)
def within(path, root) -> bool: return resolved(path).is_relative_to(root)
