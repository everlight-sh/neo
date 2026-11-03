"""Unchanged rebuilds without parsing.

Every build leaves a record beside its cached binary: a hash of each source
text it read, each import as written with the path it resolved to, and the
manifest that named each module. Records are keyed by what is known before
parsing: the entry file, the compiler's sources and location, the clang that
PATH finds, flags and NEO_*/AXON_* variables. `neo build` and `neo run` look
for a record first. When every text, resolution and manifest still matches,
they publish the cached binary without importing the rest of the compiler.
Any difference, and any argument this module does not know, takes the full
path, whose cache key stays the authority. So do package imports, whose
resolution reads the lock file and package trees. NEO_QUICK=0 turns this off.
"""
import hashlib, json, os, shutil, sys, time
from pathlib import Path
from . import legacy

HERE = os.path.dirname(os.path.abspath(__file__))
FORMAT = 1
VALUES = {'-o': 'output', '--output': 'output', '--opt-level': 'opt_level', '--target': 'target', '--diagnostic-format': 'diagnostic_format'}
FLAGS = {'--report': 'report', '--dev': 'dev', '--allow-unproven': 'allow_unproven'}
# Stand-ins for the two report fields a cache hit replaces.
BUILD, BINARY = '\0neo-quick-build\0', '\0neo-quick-binary\0'


def clang():
    """The clang subprocess would run, and what identifies its file."""
    for folder in os.get_exec_path():
        path = os.path.join(folder, 'clang')
        if os.path.isfile(path) and os.access(path, os.X_OK):
            real = os.path.realpath(path); info = os.stat(real)
            return [path, real, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_dev]
    return None


def resolved(file):
    """The entry path as `neo build` resolves it."""
    return str(Path(file).resolve())


def key(file, dev, opt_level, allow_unproven):
    """Everything the full cache key depends on except what parsing reads."""
    environment = sorted((k, v) for k, v in os.environ.items() if k.startswith(('NEO_', 'AXON_')))
    h = hashlib.sha256(repr((FORMAT, resolved(file), HERE, sys.platform, os.uname().machine,
                             bool(dev), opt_level, bool(allow_unproven), clang(), environment)).encode())
    for name in sorted(os.listdir(HERE)):
        if name.endswith('.py'):
            h.update(name.encode())
            with open(os.path.join(HERE, name), 'rb') as source: h.update(source.read())
    return h.hexdigest()


def folder(entry):
    return os.path.join(os.path.dirname(os.path.abspath(entry)), legacy.build_dir(entry))


def remember(quick_key, entry, program, cache_key, report):
    """Record a finished build or full-path hit for `lookup`."""
    if program.package_imports: return
    shown = {**report, 'build': BUILD, 'binary': BINARY}
    record = {'format': FORMAT, 'entry': entry, 'cache_key': cache_key, 'binary_sha256': report['binary_sha256'],
              'sources': {path: hashlib.sha256(text.encode()).hexdigest() for path, text in program.sources.items()},
              'imports': program.import_edges, 'manifests': program.module_manifests,
              'line': {'program': report['program'], 'summary': report['summary'], 'folded_calls': report['folded_calls'],
                       'inlined_calls': report['inlined_calls'], 'parallel_regions': len(report['parallel_regions']),
                       'vector_sums': len(report['vector_sums'])},
              'report': json.dumps(shown, indent=2, ensure_ascii=False)}
    path = os.path.join(folder(entry), 'quick-' + quick_key + '.json'); stage = path + '.' + str(os.getpid()) + '.tmp'
    with open(stage, 'w') as file: json.dump(record, file)
    os.replace(stage, path)


def nearest(path, found):
    """The manifest modules._identity reads for path: the first neo.toml or
    axon.toml among its parents, or ''."""
    for parent in path.parents:
        name = str(parent)
        if name not in found: found[name] = next((str(parent / m) for m in legacy.MANIFESTS if (parent / m).is_file()), '')
        if found[name]: return found[name]
    return ''


def current(record):
    """Whether each source text, import resolution and module manifest the
    recorded build read is still what it was."""
    for written, target in record['imports']:
        if str(Path(written).resolve()) != target: return False
    for path, digest in record['sources'].items():
        if hashlib.sha256(Path(path).read_text(encoding='utf-8').encode()).hexdigest() != digest: return False
    found, texts = {}, {}
    for path, (manifest, digest) in record['manifests'].items():
        if nearest(Path(path), found) != manifest: return False
        if manifest:
            if manifest not in texts: texts[manifest] = hashlib.sha256(Path(manifest).read_text().encode()).hexdigest()
            if texts[manifest] != digest: return False
    return True


def publish(source, destination):
    """Publish a fresh inode; never overwrite a mapped macOS executable."""
    destination = os.path.abspath(destination)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    stage = os.path.join(os.path.dirname(destination), '.neo-publish-' + os.urandom(8).hex())
    try: shutil.copy2(source, stage); os.replace(stage, destination)
    finally:
        if os.path.exists(stage): os.unlink(stage)


def hit(file, output, dev=False, opt_level=None, allow_unproven=False):
    """Publish the recorded build of file to output if nothing it read has
    changed: its record, else None."""
    try:
        entry = resolved(file)
        with open(os.path.join(folder(entry), 'quick-' + key(entry, dev, opt_level, allow_unproven) + '.json')) as handle:
            record = json.load(handle)
        if record.get('format') != FORMAT or record['entry'] != entry or not current(record): return None
        binary = os.path.join(folder(entry), record['cache_key'] + '.bin')
        with open(binary, 'rb') as handle:
            if hashlib.sha256(handle.read()).hexdigest() != record['binary_sha256']: return None
        if not os.path.isfile(os.path.join(folder(entry), record['cache_key'] + '.json')): return None
        publish(binary, output or os.path.splitext(os.path.basename(entry))[0])
        return record
    except (OSError, ValueError, KeyError, TypeError, UnicodeError): return None


def options(argv):
    """The options of `neo build FILE ...`, or None unless every argument is
    one this module knows."""
    chosen = {'file': None, 'output': None, 'opt_level': None, 'target': None, 'diagnostic_format': 'json',
              'report': False, 'dev': False, 'allow_unproven': False}
    rest = iter(argv)
    for arg in rest:
        if arg in FLAGS: chosen[FLAGS[arg]] = True
        elif arg in VALUES:
            value = next(rest, None)
            if value is None or value.startswith('-'): return None
            chosen[VALUES[arg]] = value
        elif arg.startswith('-') or chosen['file'] is not None: return None
        else: chosen['file'] = arg
    if chosen['file'] is None or chosen['diagnostic_format'] != 'json' or chosen['opt_level'] not in (None, '0', '1', '2', '3'): return None
    return chosen


def lookup(argv):
    """Answer `neo build` or `neo run` from a record; False means take the full path."""
    started = time.monotonic()
    if os.environ.get('NEO_QUICK') == '0': return False
    if argv[:1] == ['build']:
        chosen = options(argv[1:])
        if chosen is None: return False
        if chosen['target']: os.environ['NEO_TARGET'] = chosen['target']
        record = hit(chosen['file'], chosen['output'], chosen['dev'], chosen['opt_level'], chosen['allow_unproven'])
        if record is None: return False
        out = chosen['output'] or os.path.splitext(os.path.basename(record['entry']))[0]
        line = record['line']
        if chosen['report']:
            build = {'cache': 'hit', 'graph': line['program'][:16], 'total_seconds': round(time.monotonic() - started, 4), 'quick': True}
            print(record['report'].replace(json.dumps(BUILD), json.dumps(build, indent=2).replace('\n', '\n  '), 1)
                  .replace(json.dumps(BINARY), json.dumps(out, ensure_ascii=False), 1))
        else:
            s = line['summary']
            print(f"neoc: {out}  graph {line['program'][:16]}  "
                  f"obligations {s['proven']}/{s['obligations']} proven, {s['runtime_checks']} runtime checks, "
                  f"{line['parallel_regions']} parallel regions, {line['vector_sums']} vectorised sums, "
                  f"{line['folded_calls']} calls folded, {line['inlined_calls']} inlined, build hit")
        return True
    if argv[:1] == ['run']:
        at = 2 if argv[1:2] == ['--dev'] else 1
        file = argv[at] if len(argv) > at else None
        if file is None or file.startswith('-'): return False
        entry = resolved(file)
        output = os.path.join(folder(entry), 'run')
        if hit(entry, output, dev=at == 2) is None: return False
        print('neo: build hit', file=sys.stderr)
        import shlex, subprocess
        arguments = argv[at + 1:]
        if arguments[:1] == ['--']: arguments = arguments[1:]
        raise SystemExit(subprocess.call(shlex.split(os.environ.get('NEO_RUNNER', '')) + [output] + arguments))
    return False
