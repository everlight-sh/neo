"""Compare the native release and editor commands with the Python reference."""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
import tarfile
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]


def run(command, cwd, env, **kwargs):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=300, **kwargs)
    assert result.returncode == 0, (command, result.returncode, result.stdout[-500:], result.stderr[-500:])
    return result.stdout


def release(root, neoc, env):
    native = root / 'native.tar.gz'
    repeat = root / 'native-repeat.tar.gz'
    python = root / 'python.tar.gz'
    epoch = '123456789'
    reference = json.loads(run([ROOT / 'neoc.sh', 'release', '--native', neoc, '-o', python],
                               root, {**os.environ, 'SOURCE_DATE_EPOCH': epoch}))
    for target in (native, repeat):
        report = json.loads(run([ROOT / 'neo', 'release', '-o', target], root, {**env, 'SOURCE_DATE_EPOCH': epoch}))
        assert report['archive'] == str(target)
        assert report['sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
        for key in ('version', 'platform', 'files', 'epoch', 'ok'):
            assert report[key] == reference[key], (key, report, reference)
    assert native.read_bytes() == repeat.read_bytes()
    assert not list(root.glob('.neo-release-*'))
    assert int.from_bytes(native.read_bytes()[4:8], 'little') == int(epoch)
    with tarfile.open(native) as actual, tarfile.open(python) as expected:
        assert [m.get_info() for m in actual] == [m.get_info() for m in expected]
    with gzip.open(native) as actual, gzip.open(python) as expected:
        assert actual.read() == expected.read(), 'USTAR streams differ'


def frame(body):
    if not isinstance(body, bytes):
        body = json.dumps({'jsonrpc': '2.0', **body}, ensure_ascii=False).encode()
    return b'Content-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body


def messages(data):
    out = []
    while data:
        header, data = data.split(b'\r\n\r\n', 1)
        length = int(header.split(b':')[1])
        out.append(json.loads(data[:length]))
        data = data[length:]
    return out


def editor(root, env):
    project = root / 'space é🚀'
    project.mkdir()
    main = project / 'main.neo'
    helper = project / 'helper.neo'
    main.write_text('fn main() -> i64 = 0\n')
    helper.write_text('fn answer() -> i64 = 40\n')
    uri = main.as_uri()
    helper_uri = helper.as_uri()
    doc = {'textDocument': {'uri': uri}}
    use = {**doc, 'position': {'line': 2, 'character': 24}}
    source = '; 🚀\nimport "helper.neo" as m\nfn main()->i64=m::answer()\n'
    requests = [
        b'{',
        {'id': 1, 'method': 'initialize'},
        {'method': 'textDocument/didOpen', 'params': {'textDocument': {
            'uri': helper_uri, 'version': 1, 'text': 'fn answer() -> i64 = 42\n'}}},
        {'method': 'textDocument/didOpen', 'params': {'textDocument': {
            'uri': uri, 'version': 1, 'text': source}}},
        {'id': 2, 'method': 'textDocument/completion', 'params': use},
        {'id': 3, 'method': 'textDocument/hover', 'params': use},
        {'id': 4, 'method': 'textDocument/definition', 'params': use},
        {'id': 5, 'method': 'textDocument/documentSymbol', 'params': doc},
        {'id': 6, 'method': 'textDocument/formatting', 'params': doc},
        {'method': 'textDocument/didChange', 'params': {'textDocument': {'uri': uri, 'version': 2},
            'contentChanges': [{'text': source.split('m::answer')[0] + 'm::'}]}},
        {'id': 7, 'method': 'textDocument/completion', 'params': {
            **doc, 'position': {'line': 2, 'character': 18}}},
        {'method': 'textDocument/didChange', 'params': {'textDocument': {'uri': uri, 'version': 3},
            'contentChanges': [{'text': 'fn main() -> i64 = true\n'}]}},
        {'method': 'textDocument/didClose', 'params': doc},
        {'id': 'shutdown', 'method': 'shutdown'},
        {'method': 'exit'},
    ]
    data = b''.join(map(frame, requests))
    old = messages(run([ROOT / 'neoc.sh', 'lsp'], root, os.environ, input=data))
    new = messages(run([ROOT / 'neo', 'lsp'], root, env, input=data))
    old_ids = {x['id']: x for x in old if 'id' in x}
    new_ids = {x['id']: x for x in new if 'id' in x}
    assert old_ids.keys() == new_ids.keys()
    for key in (None, 1, 2, 3, 4, 5, 6, 7, 'shutdown'):
        assert new_ids[key] == old_ids[key], (key, new_ids[key], old_ids[key])
    for output in (old, new):
        diagnostics = [x['params'] for x in output if x.get('method') == 'textDocument/publishDiagnostics'
                       and x['params']['uri'] == uri]
        assert [(d.get('version'), bool(d['diagnostics'])) for d in diagnostics] == [
            (1, False), (2, True), (3, True), (None, False)], diagnostics
    assert main.read_text() == 'fn main() -> i64 = 0\n'
    assert helper.read_text() == 'fn answer() -> i64 = 40\n'


def graph(root, env):
    source = root / 'graph.neo'
    source.write_text(
        'type Pair = { a: i64, b: i64 }\n'
        'fn twice(x:i64) -> i64 = x * 2\n'
        'fn fraction() -> f64 = 0.1 + 1.0e-5\n'
        'fn main() -> i64 = let p = Pair { b=4, a=3 } in '
        'let q = p with { b=2, a=21 } in twice(q.a)\n'
    )
    for flags in ([], ['--full']):
        old = json.loads(run([ROOT / 'neoc.sh', 'graph', source, *flags], root, os.environ))
        new = json.loads(run([ROOT / 'neo', 'graph', source, *flags], root, env))
        assert old == new, (old['program'], new['program'], old['functions']['main'], new['functions']['main'])


def driver(root, env):
    library = root / 'library.neo'
    library.write_text('fn answer() -> i64 = 42\n')
    for launcher, environment in (('neo', env), ('neoc.sh', os.environ)):
        result = run([ROOT / launcher, 'check', '--library', library, '--diagnostic-format', 'json'], root, environment)
        assert json.loads(result)['ok']
    main = root / 'arguments.neo'
    main.write_text('import "std:io"\neffect fn main() -> Arr u8 _ = cli_arg(1).value\n')
    native = run([ROOT / 'neo', 'run', '--dev', main, '--', 'argument with spaces'], root,
                 {**env, 'NEO_RUNNER': '/bin/sh -c \'exec "$@"\' neo-test'})
    assert native == b'argument with spaces'
    result = run([ROOT / 'neo', 'doctor'], root, env)
    assert b'built and ran hello world' in result


def response(binary, mode):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    env = {**os.environ, 'NEO_THREADS': '1', 'NEO_TEST_BODY': 'world'}
    with subprocess.Popen([binary, str(port), str(mode)], env=env, start_new_session=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as server:
        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    client = socket.create_connection(('127.0.0.1', port), timeout=1)
                    break
                except OSError:
                    if server.poll() is not None:
                        raise AssertionError(server.stderr.read())
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.05)
            with client:
                client.settimeout(5)
                client.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
                with client.makefile('rb') as stream:
                    return stream.read()
        finally:
            try:
                os.killpg(server.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGKILL)
                server.wait(timeout=3)


def http(root, env):
    source = root / 'serve.neo'
    source.write_text(
        'import "std:io"\n'
        'fn reply(body:Arr u8 _) -> Arr u8 _ = '
        'concat("HTTP/1.1 200 OK\\r\\nContent-Length: 5\\r\\nConnection: close\\r\\n\\r\\n", body)\n'
        'fn pure_handler(request:Arr u8 _) -> Arr u8 _ = reply("hello")\n'
        'effect(env) fn effect_handler(request:Arr u8 _) -> Arr u8 _ = reply(env_get("NEO_TEST_BODY").value)\n'
        'effect(env,net) fn main(port:i64,mode:i64) -> i64 = '
        'if mode==0 then serve(port,pure_handler) else serve_effect(port,effect_handler)\n'
    )
    native, reference = root / 'native-server', root / 'reference-server'
    run([ROOT / 'neo', 'build', source, '--dev', '-o', native], root, env)
    run([ROOT / 'neoc.sh', 'build', source, '--dev', '-o', reference], root, os.environ)
    for mode, body in enumerate((b'hello', b'world')):
        old, new = response(reference, mode), response(native, mode)
        assert old == new and new.endswith(b'\r\n\r\n' + body), (old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('neoc', type=Path)
    parser.add_argument('--case', choices=('release', 'editor', 'graph', 'driver', 'http'), action='append')
    args = parser.parse_args()
    with TemporaryDirectory(prefix='neo-tooling-diff-') as tmp:
        root = Path(tmp)
        tools = root / 'toolchain'
        tools.mkdir()
        for name in ('clang', 'ld', 'ld.lld', 'as', 'gzip'):
            path = shutil.which(name)
            if path:
                (tools / name).symlink_to(path)
        neoc = args.neoc.resolve()
        env = {'PATH': str(tools), 'NEOC': str(neoc)}
        if not args.case or 'release' in args.case:
            release(root, neoc, env)
        if not args.case or 'editor' in args.case:
            editor(root, env)
        if not args.case or 'graph' in args.case:
            graph(root, env)
        if not args.case or 'driver' in args.case:
            driver(root, env)
        if not args.case or 'http' in args.case:
            http(root, env)
    print('Native tooling verification passed')


if __name__ == '__main__':
    main()
