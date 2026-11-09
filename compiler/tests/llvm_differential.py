"""Build and run programs with native neoc and compare with Python neoc.

    python3 compiler/bootstrap.py -o /tmp/neo-seed
    python3 compiler/tests/llvm_differential.py /tmp/neo-seed/neoc
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import platform
import shutil
import subprocess
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
RESOURCE = ('resource type Owner = {counter:ptr,digit:i64} drop dispose\n'
            'fn make(p:ptr,n:i64) -> Owner = Owner {counter=p,digit=n}\n'
            'effect(unsafe) fn dispose(x:Owner) -> unit = store_i64(x.counter,0,load_i64(x.counter,0)*10+x.digit)\n'
            'effect(unsafe) fn take(move x:Owner) -> i64 = x.digit\n')
RESOURCE_BRANCH = (RESOURCE + 'effect(unsafe) fn work(p:ptr,n:i64) -> i64 = '
                   'using a=make(p,1) in using b=make(p,2) in if n>0 then take(a) else b.digit\n'
                   'effect(unsafe) fn main(n:i64) -> i64 = let p=stack_alloc(8) in let init=store_i64(p,0,0) in '
                   'let value=work(p,n) in load_i64(p,0)')
CASES = (
    ('constant', 'fn main() -> i64 = 42', ()),
    ('arithmetic', 'fn main(x:i64) -> i64 = -(x*2+3)', ('21',)),
    ('branches', 'fn main(x:i64) -> i64 = if x<0 then if x<-2 then -x else 2 else x+1', ('-7',)),
    ('short-circuit', 'fn main(x:i64) -> i64 = if x!=0 && 12/x>0 then 1 else 0', ('0',)),
    ('remainder', 'fn main(x:i64) -> i64 = if x==0 then 0 else 13%x', ('5',)),
    ('recursive', 'fn main(x:i64) -> i64 = if x<=1 then 1 else x*main(x-1)', ('5',)),
    ('forward', 'fn main() -> i64 = f(2,true)\nfn f(x:i64,b:bool) -> i64 = if b then x else 0', ()),
    ('float', 'fn main(x:i64) -> i64 = i64(-(f64(x)/2.0) + 0.25)', ('11',)),
    ('float-output', 'fn main(x:i64) -> f64 = f64(x)/2.0', ('11',)),
    ('narrow', "fn main(x:i64) -> i64 = if 'a'<u8(x) then i64(u16(x)) else i64(i32(x))", ('99',)),
    ('unit', 'fn main() -> unit = noop()', ()),
    ('unit-pointer', 'fn helper() -> unit = noop()\nfn main() -> i64 = let done=helper() in if null()==null() then 7 else 9', ()),
    ('export', 'export fn answer(x:i64{x>0}) -> i64 = x*2\nfn main() -> i64 = answer(21)', ()),
    ('imported', 'import "../library.neo" as lib\nfn main() -> i64 = lib::triple(7)', ()),
    ('multi-argument', 'fn main(a:i64,b:i64,c:i64) -> i64 = a+b+c', ('2', '+7', '-4')),
    ('minimum-argument', 'fn main(x:i64) -> i64 = x', ('-9223372036854775808',)),
    ('missing-argument', 'fn main(x:i64) -> i64 = x', ()),
    ('invalid-argument', 'fn main(x:i64) -> i64 = x', ('9223372036854775808',)),
    ('bytes', 'fn main() -> Arr u8 _ = "é\\x00\\xff\\n"', ()),
    ('empty-bytes', 'fn main() -> Arr u8 _ = ""', ()),
    ('array-length', 'fn measure(a:Arr u8 n) -> i64 = n + len(a)\nfn main() -> i64 = measure(concat("a","bc"))', ()),
    ('array-index', 'fn main() -> i64 = i64("abc"[1])', ()),
    ('array-return-alias', 'fn keep(borrow a:Arr u8 n) -> Arr u8 n = a\nfn main() -> Arr u8 _ = let a=concat("a","b") in keep(a)', ()),
    ('array-shared-arguments', 'fn join(a:Arr u8 n,b:Arr u8 n) -> Arr u8 (2*n) = concat(a,b)\nfn main() -> Arr u8 _ = let a=concat("a","b") in join(a,a)', ()),
    ('array-choice', 'fn main(x:i64) -> Arr u8 _ = let a=concat("a","b") in if x>0 then a else push(a,\'!\')', ('-1',)),
    ('array-copy-on-update', 'fn main() -> Arr u8 _ = let a=concat("a","b") in let b=set(a,1,\'z\') in concat(a,b)', ()),
    ('array-push-empty', 'fn main() -> Arr u8 _ = push("",\'a\')', ()),
    ('array-scalar-range', 'fn main() -> i64 = let a=arr(i in -2..2) i*i in a[3]+len(a)', ()),
    ('array-bool-range', 'fn main() -> i64 = let a=arr(i in 0..3) i==1 in if a[1] && !a[2] then 1 else 0', ()),
    ('array-u16-concat', 'fn main() -> i64 = let a=arr(i in 0..3) u16(i+1000) in let b=concat(a,a) in i64(b[5])', ()),
    ('array-range-with-branches', 'fn main() -> Arr u8 _ = arr(i in 0..3) if i==0 then \'a\' else u8(i+97)', ()),
    ('scalar-loop', 'fn main(n:i64) -> i64 = loop(i=0,total=0) while i<n next(i+1,total+i) yield total', ('8',)),
    ('loop-branch-successor', 'fn main(n:i64) -> i64 = loop(i=0,total=0) while i<n next(i+1,if i==0 then 7 else total+i) yield total', ('8',)),
    ('loop-array', 'fn main() -> Arr u8 _ = loop(a="") while len(a)<8 next(push(a,\'!\')) yield a', ()),
    ('loop-array-alias', 'fn main() -> Arr u8 _ = let a=concat("a","b") in let b=loop(i=0,b=a) while i<5 next(i+1,push(b,\'!\')) yield b in concat(a,b)', ()),
    ('loop-empty', 'fn main() -> Arr u8 _ = loop(a=concat("a","b")) while false next(push(a,\'!\')) yield a', ()),
    ('integer-sum', 'fn main(n:i64) -> i64 = sum(i in 0..n) (i+1)', ('10',)),
    ('float-sum', 'fn main() -> f64 = sum(i in 1..5) f64(i)/2.0', ()),
    ('empty-sum', 'fn main() -> i64 = sum(i in 5..0) i', ()),
    ('record-sum', 'type Pair = { x:i64,y:f64 }\nfn main(n:i64) -> i64 = '
     'let p=sum(i in 0..n) Pair { x=i,y=f64(i)/2.0 } in p.x+i64(p.y)', ('5',)),
    ('empty-record-sum', 'type Pair = { x:i64,y:f64 }\nfn main() -> i64 = '
     'let p=sum(i in 2..0) Pair { x=i,y=f64(i) } in p.x+i64(p.y)', ()),
    ('check-pass', 'fn main(x:i64) -> i64 = check x>=0 && x<2 in i64("hi"[x])', ('1',)),
    ('check-fail', 'fn main(x:i64) -> i64 = check x>=0 && x<2 in i64("hi"[x])', ('-1',)),
    ('entry-refinement', 'fn main(x:i64{x>=0,x<2}) -> i64 = i64("hi"[x])', ('1',)),
    ('entry-refinement-fail', 'fn main(x:i64{x>=0,x<2}) -> i64 = i64("hi"[x])', ('-1',)),
    ('callee-refinement', 'fn take(a:Arr u8 n,i:i64{0<=i,i<n}) -> u8 = a[i]\nfn main() -> i64 = i64(take("hi",1))', ()),
    ('return-refinement', 'fn choose() -> i64{result==1} = 1\nfn main() -> i64 = i64("hi"[choose()])', ()),
    ('integer-overflow', 'fn main(x:i64) -> i64 = x+1', ('9223372036854775807',)),
    ('division-overflow', 'fn main(x:i64) -> i64 = x/-1', ('-9223372036854775808',)),
    ('effect-direct', 'effect(fs) fn first() -> i64 = 4\neffect fn second() -> i64 = first()+3\neffect(fs) fn main() -> i64 = second()', ()),
    ('bit-mask', 'fn main(x:i64) -> i64 = i64("abcd"[bit_and(x,3)])', ('-1',)),
    ('shifts', 'fn main() -> i64 = bit_xor(shift_left(1,67),bit_or(shift_right(-1,68),arithmetic_shift_right(-4,65)))', ()),
    ('wrapping-arithmetic', 'fn main() -> i64 = wrapping_mul(wrapping_add(9223372036854775807,1),wrapping_sub(5,2))', ()),
    ('integer-intrinsics', 'fn main() -> i64 = mul_high(-1,-1)+count_trailing_zeros(byte_swap64(1))', ()),
    ('float-intrinsics', 'fn main() -> f64 = sqrt(bits_float(float_bits(81.0)))', ()),
    ('raw-memory', 'effect(unsafe) fn main() -> i64 = let p=stack_alloc(16) in let a=store_i64(p,0,42) in let b=volatile_store_u8(p,8,\'a\') in load_i64(ptr_from_i64(ptr_to_i64(p)),0)+i64(volatile_load_u8(ptr_add(p,8),0))', ()),
    ('runtime-state', 'effect(unsafe) fn main() -> i64 = let s=runtime_state() in let count=load_i64(s,40) in let argv=load_ptr(s,48) in let envp=load_ptr(s,0) in if argv!=null() && envp==ptr_add(argv,(count+1)*8) then count else -1', ('one', 'two')),
    ('atomic-memory', 'effect(unsafe) fn main() -> i64 = let p=stack_alloc(16) in let init=atomic_store_i64(p,0,18) in let narrow=atomic_store_i32(p,8,i32(7)) in let fail=atomic_compare_exchange_i64(p,0,99,13) in let ok=atomic_compare_exchange_i64(p,0,18,17) in fail+ok+atomic_load_i64(p,0)+i64(atomic_load_i32(p,8))', ()),
    ('address-function', 'fn f() -> i64 = 42\neffect(unsafe) fn main() -> i64 = if addr(f)==null() then 0 else 1', ()),
    ('invoke-function', 'fn clock(id:i32,p:ptr) -> i32 = if p==null() then id else i32(0)\neffect(unsafe) fn main() -> i64 = i64(invoke_clock_gettime(addr(clock),i32(42),null()))', ()),
    ('handler-call', 'fn handle(bytes:Arr u8 n) -> Arr u8 (n+1) = concat(bytes,"!")\neffect(unsafe) fn main() -> Arr u8 _ = handler_call(addr(handle),data("hello"),5)', ()),
    ('byte-operations', 'fn slice() -> Arr u8 _ = byte_slice(concat("ab","cd"),1,3)\n'
     'fn main() -> Arr u8 _ = let a=slice() in let b=byte_copy(a,0,"z") in '
     'if byte_equal(a,"bc") && byte_read_le(b,0,2)==25466 then concat(a,b) else "mismatch"', ()),
    ('byte-read-width', 'fn main(width:i64) -> i64 = byte_read_le("abc",0,width)', ('3',)),
    ('byte-read-bounds', 'fn main(offset:i64) -> i64 = byte_read_le("abc",offset,2)', ('2',)),
    ('byte-copy-bounds', 'fn main(offset:i64) -> Arr u8 _ = byte_copy("abc",offset,"yz")', ('2',)),
    ('byte-write', 'fn main(width:i64) -> Arr u8 _ = let a=concat("ab","cdefghi") in '
                   'let b=byte_write_le(a,1,506097522914230528,width) in concat(a,b)', ('8',)),
    ('byte-write-width', 'fn main(width:i64) -> Arr u8 _ = byte_write_le("abc",1,65793,width)', ('9',)),
    ('byte-write-bounds', 'fn main(offset:i64) -> Arr u8 _ = byte_write_le("abc",offset,65793,3)', ('1',)),
    ('byte-write-zero', 'fn main() -> Arr u8 _ = byte_write_le("abc",3,-1,0)', ()),
    ('byte-slice-bounds', 'fn main(end:i64) -> Arr u8 _ = byte_slice("abc",0,end)', ('4',)),
    ('data-literal', 'effect(unsafe) fn main() -> i64 = i64(load_u8(data("abc"),1))', ()),
    ('byte-uninit-write', 'effect(unsafe) fn main() -> Arr u8 _ = let a=byte_uninit(2) in let p=data(a) in let first=store_u8(p,0,\'h\') in let second=store_u8(p,1,\'i\') in a', ()),
    ('view-alias', 'effect(unsafe) fn main() -> i64 = let p=stack_alloc(1) in let init=store_u8(p,0,\'a\') in let a=view(p,1) in let changed=store_u8(p,0,\'z\') in i64(a[0])', ()),
    ('view-escape', 'effect(unsafe) fn copy() -> Arr u8 (1) = let p=stack_alloc(1) in let init=store_u8(p,0,\'a\') in view(p,1)\neffect(unsafe) fn main() -> Arr u8 _ = copy()', ()),
    ('view-scope-escape', 'effect(unsafe) fn main() -> Arr u8 _ = let a=concat("a","b") in view(data(a),len(a))', ()),
    ('view-record-escape', 'type Text = { bytes:Arr u8 _ }\neffect(unsafe) fn main() -> Arr u8 _ = let p=stack_alloc(1) in let init=store_u8(p,0,\'a\') in let text=Text { bytes=view(p,1) } in let changed=store_u8(p,0,\'z\') in text.bytes', ()),
    ('record', 'type Point = { x:i64,y:i64 }\nfn main() -> i64 = let p=Point { y=3,x=7 } in p.x+p.y', ()),
    ('record-update', 'type Point = { x:i64,y:i64 }\nfn main() -> i64 = let p=Point { x=7,y=3 } in let q=p with { x=4 } in p.x+q.x', ()),
    ('record-array', 'type Text = { bytes:Arr u8 _ }\nfn main() -> Arr u8 _ = let a=Text { bytes=concat("a","b") } in let b=a with { bytes=push(a.bytes,\'!\') } in concat(a.bytes,b.bytes)', ()),
    ('record-array-return', 'type Text = { bytes:Arr u8 _ }\nfn keep(borrow text:Text) -> Text = text\nfn main() -> Arr u8 _ = keep(Text { bytes=concat("a","b") }).bytes', ()),
    ('record-nested', 'type Outer = { inner:Inner }\ntype Inner = { text:Arr u8 _ }\nfn main() -> Arr u8 _ = let a=Outer { inner=Inner { text=concat("a","b") } } in a.inner.text', ()),
    ('record-phi', 'type Text = { bytes:Arr u8 _ }\nfn main(x:i64) -> Arr u8 _ = let a=if x==0 then Text { bytes=concat("a","b") } else Text { bytes=concat("c","d") } in a.bytes', ('1',)),
    ('record-loop', 'type Text = { bytes:Arr u8 _ }\nfn main() -> Arr u8 _ = let a=loop(i=0,t=Text { bytes="" }) while i<5 next(i+1,t with { bytes=push(t.bytes,\'!\') }) yield t in a.bytes', ()),
    ('record-initializer-order', 'type Pair = { first:unit,second:i64 }\neffect(unsafe) fn main() -> i64 = let p=stack_alloc(8) in let initial=store_i64(p,0,0) in let r=Pair { second=load_i64(p,0),first=store_i64(p,0,42) } in r.second', ()),
    ('ragged-rows', 'fn rows() -> Arr Arr u8 _ (3) = arr(i in 0..3) arr(j in 0..i) u8(97+i+j)\nfn main() -> Arr u8 _ = let a=rows() in concat(a[2],a[1])', ()),
    ('row-outlives-parent', 'fn rows() -> Arr Arr u8 _ (2) = arr(i in 0..2) concat("row",arr(j in 0..1) u8(i+48))\nfn main() -> Arr u8 _ = rows()[1]', ()),
    ('row-edit', 'fn main() -> Arr u8 _ = let a=arr(i in 0..2) concat("row",arr(j in 0..1) u8(i+48)) in let b=push(set(a,0,a[1]),a[0]) in concat(a[0],b[0],b[2])', ()),
    ('record-elements', 'type Cell = { kind:u8,value:i64,bytes:Arr u8 _ }\nfn cells() -> Arr Cell (3) = arr(i in 0..3) Cell { kind=u8(i),value=i*2,bytes=concat("c",arr(j in 0..1) u8(i+48)) }\nfn main() -> Arr u8 _ = let a=cells() in let b=set(a,1,a[2]) in let c=push(b,b[0]) in concat(a[1].bytes,c[1].bytes,c[3].bytes)', ()),
    ('empty-record-array', 'type Cell = { value:Arr u8 _ }\nfn main() -> Arr u8 _ = let a=arr(i in 0..0) Cell { value="" } in push(a,Cell { value=concat("a","b") })[0].value', ()),
    ('record-array-branches', 'type Box = {value:Arr u8 _}\nfn choose(x:i64) -> Arr Box (1) = if x>0 then arr(i in 0..1) Box {value=concat("a","b")} else arr(i in 0..1) Box {value="other"}\nfn main() -> Arr u8 _ = choose(42)[0].value', ()),
    ('nested-array-field', 'type Pack = { rows:Arr Arr u8 _ _ }\nfn second(borrow p:Pack) -> Arr u8 _ = let a=p.rows in check len(a)>1 in a[1]\nfn main() -> Arr u8 _ = second(Pack { rows=arr(i in 0..3) concat("row",arr(j in 0..1) u8(i+48)) })', ()),
    ('three-dimensional-array', 'fn main() -> i64 = let a=arr(i in 0..2) arr(j in 0..2) arr(k in 0..2) i+j+k in let row=a[1][1] in check len(row)>1 in row[1]', ()),
    ('view-array-element', 'effect(unsafe) fn main() -> Arr u8 _ = let p=stack_alloc(1) in let init=store_u8(p,0,\'a\') in let row=view(p,1) in let a=push(arr(i in 0..1) "x",row) in let changed=store_u8(p,0,\'z\') in concat(a[1],row)', ()),
    ('generic-instances', 'fn id<T>(x:T) -> T = x\nfn main() -> Arr u8 _ = if id(true) then concat(id("value="),arr(i in 0..1) u8(id(42))) else ""', ()),
    ('generic-recursion', 'fn keep<T>(x:T,n:i64) -> T = if n<=0 then x else keep(x,n-1)\nfn main() -> Arr u8 _ = keep(concat("a","b"),5)', ()),
    ('generic-key-equality', 'fn equals<T>(a:T,b:T) -> bool = key_equal(a,b)\nfn main() -> i64 = if equals(u16(42),u16(42)) && !equals(true,false) then 1 else 0', ()),
    ('generic-nested-records', 'type Box<T> = {value:T}\nfn get<T>(borrow x:Box<T>) -> T = x.value\nfn main() -> Arr u8 _ = get(get(Box::<Box<Arr u8 _>> {value=Box::<Arr u8 _> {value=concat("a","b")}}))', ()),
    ('generic-conditional-enum', 'enum Choice<T> { Missing, Present(T) }\nfn main(n:i64) -> Arr u8 _ = let choice=if n==0 then Missing::<Arr u8 _>() else Present(concat("a","b")) in match choice { Present(text) => text, Missing => "missing" }', ('1',)),
    ('option-library', 'import "std:option"\nfn main() -> Arr u8 _ = option_or(Some(concat("a","b")),"missing")', ()),
    ('enum-multiple-payloads', 'enum Choice { A(Arr u8 _,i64), B(Arr u8 _,Arr u8 _), C }\nfn main(n:i64) -> Arr u8 _ = let value=if n>0 then B("a",concat("b","c")) else A("d",0) in match value { A(text,_) => text, B(a,b) => concat(a,b), _ => "c" }', ('1',)),
    ('enum-zero-record', 'type Box = {bytes:Arr u8 _}\nenum Choice { Empty, Present(Box) }\nfn main() -> Arr u8 _ = match Empty() { Empty => "ok", Present(value) => value.bytes }', ()),
    ('result-success', 'import "std:result"\nfn source() -> Result<i64,Arr u8 _> = Ok::<i64,Arr u8 _>(42)\nfn convert() -> Result<Arr u8 _,Arr u8 _> = let x=source()? in Ok::<Arr u8 _,Arr u8 _>(arr(i in 0..1) u8(x))\nfn main() -> Arr u8 _ = match convert() { Ok(value) => value, Err(error) => error }', ()),
    ('result-error', 'import "std:result"\nfn source() -> Result<i64,Arr u8 _> = Err::<i64,Arr u8 _>(concat("e","rr"))\nfn convert() -> Result<Arr u8 _,Arr u8 _> = let x=source()? in Ok::<Arr u8 _,Arr u8 _>(arr(i in 0..1) u8(x))\nfn main() -> Arr u8 _ = match convert() { Ok(value) => value, Err(error) => error }', ()),
    ('resource-branch-moved', RESOURCE_BRANCH, ('1',)),
    ('resource-branch-live', RESOURCE_BRANCH, ('0',)),
    ('resource-explicit-drop', RESOURCE + 'effect(unsafe) fn work(p:ptr) -> unit = using a=make(p,3) in using b=a in dispose(b)\n'
     'effect(unsafe) fn main() -> i64 = let p=stack_alloc(8) in let init=store_i64(p,0,0) in let done=work(p) in load_i64(p,0)', ()),
    ('resource-repeated-scope', RESOURCE + 'effect(unsafe) fn main() -> i64 = let p=stack_alloc(8) in let init=store_i64(p,0,0) in '
     'let done=loop(i=1) while i<4 next(using x=make(p,i) in i+1) yield i in load_i64(p,0)', ()),
)


def run(argv, **kwargs):
    return subprocess.run(argv, capture_output=True, timeout=120, **kwargs)


def compare(neoc, root, environment, name, source, args, settings=None):
    settings = settings or {}
    root = root / name
    root.mkdir()
    path = root / 'input.neo'
    path.write_text(source + '\n', encoding='utf-8')
    native_bin = root / 'module.ll'  # output basename can equal the staged IR filename
    linked = run([neoc, 'build', ROOT, path, '-o', native_bin, '--seed-runtime'], env={**environment, **settings})
    assert linked.returncode == 0, (name, linked.stdout, linked.stderr)
    reference_bin = root / 'reference'
    built = run([ROOT / 'neoc.sh', 'build', path, '--dev', '-o', reference_bin], env={**os.environ, **settings})
    assert built.returncode == 0, (name, built.stdout, built.stderr)
    expected = run([reference_bin, *args])
    actual = run([native_bin, *args])
    def result(process, binary):
        argv0 = os.fsencode(binary)
        return process.returncode, process.stdout.replace(argv0, b'<program>'), process.stderr.replace(argv0, b'<program>')
    assert result(actual, native_bin) == result(expected, reference_bin), (name, actual, expected)
    assert not list(root.glob('.neo-link-*'))
    return actual.stdout


def native_environment(root):
    tools = root / 'toolchain'
    tools.mkdir()
    for name in ('clang', 'ld', 'as', 'ld.lld'):
        path = shutil.which(name)
        if path:
            (tools / name).symlink_to(path)
    return {**os.environ, 'PATH': str(tools), 'NEO_CLANG': shutil.which('clang')}


def check_staging(neoc, root, environment):
    source = root / 'constant' / 'input.neo'
    output = root / 'shared'
    command = [neoc, 'build', ROOT, source, '-o', output, '--seed-runtime']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(command, env=environment), range(2)))
    assert all(result.returncode == 0 for result in results), results
    before = output.read_bytes()

    failing = root / 'failing clang'
    failing.write_text('#!/bin/sh\nwhile [ "$1" != -o ]; do shift; done\n'
                       'printf partial > "$2"\nprintf "test link failure\\n" >&2\nexit 42\n', encoding='utf-8')
    failing.chmod(0o700)
    refused = run(command, env={**environment, 'NEO_CLANG': str(failing)})
    assert refused.returncode != 0 and b'test link failure' in refused.stderr, refused
    assert output.read_bytes() == before
    assert not list(root.glob('.neo-link-*'))


def check_spawn_thread(neoc, root, environment):
    if platform.system() != 'Linux':
        return 0
    futex = 202 if platform.machine() == 'x86_64' else 98
    source = f'''
effect(unsafe) fn worker(values:ptr, chunk:i64) -> unit =
    store_i64(values,chunk*8,chunk+1)

effect(unsafe) fn run_job(pool:ptr, values:ptr, generation:i64) -> i64 =
    let first=store_i64(pool,24,0) in
    let pending=atomic_store_i64(pool,40,1) in
    let published=atomic_store_i64(pool,0,generation) in
    let woken=syscall6({futex},ptr_to_i64(pool),129,1,0,0,0) in
    let joined=loop (left=atomic_load_i64(pool,40)) while left!=0
      next (let waited=syscall6({futex},ptr_to_i64(ptr_add(pool,40)),128,left,0,0,0) in
            atomic_load_i64(pool,40)) yield left in
    loop (i=0,total=0) while i<64
      next (i+1,total+load_i64(values,i*8)) yield total

effect(unsafe) fn main() -> i64 =
    let pool=stack_alloc(48) in
    let values=stack_alloc(512) in
    let stack=stack_alloc(1048576) in
    let zero=atomic_store_i64(pool,0,0) in
    let job=store_ptr(pool,8,addr(worker)) in
    let context=store_ptr(pool,16,values) in
    let limit=store_i64(pool,32,64) in
    let pid=spawn_thread(pool,ptr_add(stack,1048576)) in
    if pid<=0 then -1 else
    let first=run_job(pool,values,1) in
    let cleared=loop (i=0) while i<64
      next (let reset=store_i64(values,i*8,0) in i+1) yield i in
    let second=run_job(pool,values,2) in
    if first==2080 && second==2080 then 42 else -2
'''
    assert compare(neoc, root, environment, 'spawn-thread', source, ()) == b'42\n'
    return 1


def check_fiber(neoc, root, environment):
    source = '''
effect(unsafe) fn task(context:ptr) -> unit =
    let parent=load_ptr(context,200) in
    let first=store_i64(context,208,17) in
    let suspended=fiber_swap(context,parent) in
    let second=store_i64(context,208,42) in
    fiber_swap(context,parent)

effect(unsafe) fn main() -> i64 =
    let parent=stack_alloc(200) in
    let context=stack_alloc(216) in
    let stack=stack_alloc(65536) in
    let cleared=loop (i=0) while i<216
      next (let reset=store_i64(context,i,0) in i+8) yield i in
    let saved=store_ptr(context,200,parent) in
    let ready=fiber_init(context,ptr_add(stack,65536),addr(task),context) in
    let first=fiber_swap(parent,context) in
    let observed=load_i64(context,208) in
    let second=fiber_swap(parent,context) in
    if observed==17 then load_i64(context,208) else -1
'''
    assert compare(neoc, root, environment, 'fiber-switch', source, ()) == b'42\n'


def check_source_runtime(neoc, root, environment):
    target = neoc.with_name('neo-runtime.o.target').read_text(encoding='utf-8').strip()
    darwin = '-apple-' in target
    x86 = target.startswith('x86_64-')
    write, exit_, mmap, munmap, private = (4, 1, 197, 73, 4098) if darwin else (
        (1, 231, 9, 11, 34) if x86 else (64, 94, 222, 215, 34)
    )
    runtime = root / 'runtime'
    runtime.mkdir()
    for filename in ('http', 'handles', 'http_async', 'async', 'events', 'timers', 'frame_cache',
                     'http_linux', 'http_uring', 'platform_macos', 'platform_linux_x86_64', 'platform_linux'):
        (runtime / f'{filename}.neo').touch()
    core = runtime / 'core.neo'
    source = f'''
export effect fn ax_runtime_init(env:ptr) -> unit = store_ptr(runtime_state(),0,env)
export effect fn ax_exit(code:i64) -> unit = let done=syscall6({exit_},code,0,0,0,0,0) in noop()
export effect fn ax_trap(message:ptr) -> unit = ax_exit(1)
export effect fn ax_precondition_failed(message:ptr) -> unit = ax_exit(3)
export effect fn ax_usage(program:ptr,names:ptr) -> unit = noop()
export fn ax_parse_i64(text:ptr,name:ptr) -> i64 = 0
export effect fn ax_print_i64(value:i64) -> unit = noop()
export effect fn ax_print_f64(value:f64) -> unit = noop()
export effect fn ax_print_bytes(bytes:ptr,n:i64) -> unit = let wrote=syscall6({write},1,ptr_to_i64(bytes),n,0,0,0) in noop()
export effect fn ax_heap_alloc(bytes:i64) -> ptr = let length=bytes+16 in
    let address=syscall6({mmap},0,length,3,{private},-1,0) in
    if address<0 then let done=ax_exit(1) in null() else
    let base=ptr_from_i64(address) in let count=store_i64(base,0,1) in
    let stored=store_i64(base,8,length) in ptr_add(base,16)
export effect fn ax_free(bytes:ptr,n:i64) -> unit =
    let done=syscall6({munmap},ptr_to_i64(ptr_add(bytes,-16)),load_i64(bytes,-8),0,0,0,0) in noop()
export effect fn memcpy(dst:ptr,src:ptr,n:i64) -> ptr =
    loop(i=0) while i<n next(let byte=store_u8(dst,i,load_u8(src,i)) in i+1) yield dst
fn rt_word(byte:i64) -> Arr u8 _ =
    if byte*72340172838076673 == -1 then "neo" else "bad byte pattern"
'''
    core.write_text(source, encoding='utf-8')
    entry = root / 'source-runtime.neo'
    entry.write_text('fn main() -> Arr u8 _ = concat(rt_word(255)," runtime\\n")\n', encoding='utf-8')
    output = root / 'source-runtime'
    command = [neoc, 'build', root, entry, '-o', output, '--target', target]
    env = {**environment, 'NEO_RUNTIME': str(root / 'missing-seed.o')}
    build = run(command, env=env)
    assert build.returncode == 0, build
    actual = run([output], env=env)
    assert (actual.returncode, actual.stdout, actual.stderr) == (0, b'neo runtime\n', b''), actual
    previous = output.read_bytes()

    core.write_text(source.replace('export effect fn ax_runtime_init', 'effect fn ax_runtime_init'), encoding='utf-8')
    rejected = run(command, env=env)
    assert rejected.returncode == 1 and b'runtime must export ax_runtime_init' in rejected.stdout, rejected
    assert output.read_bytes() == previous


def check_foreign_abi(neoc, root, environment):
    source = root / 'foreign.neo'
    source.write_text(
        'extern fn add_foreign(base:i64, ...) -> i64\n'
        'export fn c_entry(x:i64) -> i64 = x+1\n'
        'effect(unsafe) fn main() -> i64 = add_foreign(c_entry(37),i32(2),2.0,null())\n', encoding='utf-8',
    )
    checked = run([ROOT / 'neoc.sh', 'check', source])
    assert checked.returncode == 0, checked
    emitted = run([neoc, 'emit-llvm', ROOT, source], env=environment)
    assert emitted.returncode == 0, emitted
    ir = root / 'foreign.ll'
    ir.write_bytes(emitted.stdout)
    companion = root / 'foreign.c'
    companion.write_text('''#include <stdarg.h>
#include <stdint.h>
extern int64_t neo_entry(void);
extern int64_t c_entry(int64_t);
int64_t add_foreign(int64_t base, ...) {
    va_list args;
    va_start(args, base);
    int value = va_arg(args, int);
    double real = va_arg(args, double);
    void *pointer = va_arg(args, void *);
    va_end(args);
    return pointer == 0 ? base + value + (int64_t)real : -1;
}
int main(void) { return neo_entry() != 42 || c_entry(10) != 11; }
''', encoding='utf-8')
    output = root / 'foreign'
    linked = run([environment['NEO_CLANG'], '-Wno-override-module', ir, companion, '-o', output], env=environment)
    assert linked.returncode == 0, linked
    result = run([output], env=environment)
    assert result.returncode == 0, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('neoc', type=Path)
    args = parser.parse_args()
    neoc = args.neoc.resolve()
    with TemporaryDirectory(prefix='neo-llvm-diff-') as tmp:
        root = Path(tmp)
        (root / 'library.neo').write_text('pub fn triple(x:i64) -> i64 = x*3\n', encoding='utf-8')
        environment = native_environment(root)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda case: compare(neoc, root, environment, *case), CASES))
        pid_call = 20 if platform.system() == 'Darwin' else 172 if platform.machine() == 'aarch64' else 39
        compare(neoc, root, environment, 'syscall',
                'effect(unsafe) fn main(n:i64) -> i64 = if syscall6(n,0,0,0,0,0,0)>0 then 1 else 0', (str(pid_call),))
        exit_call, wait_call = (1, 7) if platform.system() == 'Darwin' else (
            (94, 260) if platform.machine() == 'aarch64' else (231, 61)
        )
        fork_source = ('effect(unsafe) fn main(exit_nr:i64,wait_nr:i64) -> i64 = let pid=fork_syscall() in '
                       'if pid==0 then let exited=syscall6(exit_nr,17,0,0,0,0,0) in -1 '
                       'else if pid<0 then -2 else let slot=stack_alloc(8) in '
                       'let joined=syscall6(wait_nr,pid,ptr_to_i64(slot),0,0,0,0) in '
                       'if joined==pid && load_i32(slot,0)==i32(4352) then 1 else -3')
        assert compare(neoc, root, environment, 'fork', fork_source, (str(exit_call), str(wait_call))) == b'1\n'
        extra = 2
        if platform.machine() in ('arm64', 'aarch64'):
            assert compare(neoc, root, environment, 'counter',
                           'effect(unsafe) fn main() -> i64 = if counter_frequency()>0 && counter_ticks()>0 then 1 else 0', ()) == b'1\n'
            extra += 1
        stats_source = ('effect(unsafe) fn main() -> i64 = let before=load_i64(runtime_state(),64) in '
                        'let a=byte_uninit(37) in let p=data(a) in let written=store_u8(p,0,\'x\') in '
                        'let after=load_i64(runtime_state(),64) in '
                        'if allocation_stats_enabled() && after>before && load_u8(p,0)==\'x\' then 1 else 0')
        for flag in ('0', '1'):
            assert compare(neoc, root, environment, f'allocation-stats-{flag}', stats_source, (),
                           {'NEO_ALLOC_STATS': flag}) == (flag + '\n').encode()
            extra += 1
        check_staging(neoc, root, environment)
        check_source_runtime(neoc, root, environment)
        check_foreign_abi(neoc, root, environment)
        extra += check_spawn_thread(neoc, root, environment)
        check_fiber(neoc, root, environment)
        extra += 1
        raw_ir = run([neoc, 'emit-llvm', ROOT, root / 'constant' / 'input.neo'], env={'PATH': '/nonexistent'})
        assert raw_ir.returncode == 0 and b'define i64 @neo_entry()' in raw_ir.stdout and b'@main(' not in raw_ir.stdout, raw_ir
        unsupported = root / 'syscall-ir.neo'
        unsupported.write_text('effect(unsafe) fn main() -> i64 = syscall6(0,0,0,0,0,0,0)\n', encoding='utf-8')
        refused = run([neoc, 'emit-llvm', ROOT, unsupported], env=environment)
        assert refused.returncode == 2 and refused.stdout.startswith(b'(unsupported '), refused

    print(f'{len(CASES) + extra} native builds matched Python neoc, including argv handling and atomic link staging')
    print('Runtime sources linked and ran with no bootstrap runtime object')
    print('Native LLVM linked and ran with a C caller and variadic callee')


if __name__ == '__main__':
    main()
