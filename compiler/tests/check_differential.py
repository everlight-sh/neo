"""Compare the native checker with the Python reference.

    ./neoc.sh build compiler/src/main.neo --dev -o /tmp/neoc
    python3 compiler/tests/check_differential.py /tmp/neoc
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
RESOURCE = ('resource type Owner = {value:i64} drop dispose\n'
            'fn make() -> Owner = Owner {value=42}\n'
            'effect(process) fn dispose(x:Owner) -> unit = noop()\n'
            'fn observe(x:Owner) -> i64 = x.value\n'
            'effect(process) fn take(move x:Owner) -> i64 = observe(x)\n')

# Every case states the native exit status and whether Python accepts it.
CASES = (
    ('integer', 0, True, 'fn main(x:i64) -> i64 = -(x * 2 + 3)'),
    ('float', 0, True, 'fn main() -> f64 = -1.25 / 2.0'),
    ('bool', 0, True, 'fn main(x:i64) -> i64 = if !(x <= 0) && x != 7 || false then 1 else 0'),
    ('narrow', 0, True, "fn main(x:i64) -> i64 = if 'a' < u8(x) then i64(u16(x)) else i64(i32(x))"),
    ('i64-min', 0, True, 'fn main() -> i64 = -9223372036854775808'),
    ('i64-max', 0, True, 'fn main() -> i64 = 9223372036854775807'),
    ('unit', 0, True, 'fn main() -> unit = noop()'),
    ('pointer', 0, True, 'fn main() -> i64 = if null() == null() then 1 else 0'),
    ('shadow', 0, True, 'fn main(x:i64) -> i64 = let x=true in if x then 1 else 0'),
    ('scope', 0, True, 'fn main(x:i64) -> i64 = (let x=true in if x then 1 else 0) + x'),
    ('forward-call', 0, True, 'fn main() -> i64 = f(1,true)\nfn f(x:i64,b:bool) -> i64 = if b then x else 0'),
    ('recursive-call', 0, True, 'fn main(x:i64) -> i64 = if x <= 0 then 0 else main(x-1)'),
    ('body', 1, False, 'fn main() -> i64 = true'),
    ('main-parameter', 1, False, 'fn main(x:bool) -> i64 = 0'),
    ('main-return', 1, False, 'fn main() -> bool = true'),
    ('main-export', 1, False, 'export fn main() -> i64 = 0'),
    ('extern-scalar', 0, True, 'extern fn foreign(x:i32,p:ptr) -> f64\neffect(unsafe) fn main() -> f64 = foreign(i32(5),null())'),
    ('extern-array', 1, False, 'extern fn foreign(a:Arr u8 _) -> i64\nfn main() -> i64 = 0'),
    ('extern-refinement', 1, False, 'extern fn foreign(x:i64{x>0}) -> i64\nfn main() -> i64 = 0'),
    ('extern-varargs', 0, True, 'extern fn foreign(x:i64, ...) -> unit\neffect(unsafe) fn main() -> unit = foreign(1,i32(2),3.0,null())'),
    ('extern-varargs-type', 1, False, 'extern fn foreign(x:i64, ...) -> unit\neffect(unsafe) fn main() -> unit = foreign(1,true)'),
    ('extern-varargs-missing', 1, False, 'extern fn foreign(x:i64, ...) -> unit\neffect(unsafe) fn main() -> unit = foreign()'),
    ('extern-capability', 1, False, 'extern fn foreign() -> i64\neffect fn bridge() -> i64 = foreign()\neffect(fs) fn main() -> i64 = bridge()'),
    ('export-refinement', 0, True, 'export fn exported(x:i64{x>0}) -> i64{result>0} = x\nfn main() -> i64 = exported(2)'),
    ('export-bool', 1, False, 'export fn exported() -> bool = true\nfn main() -> i64 = 0'),
    ('export-borrow', 1, False, 'export fn exported(borrow a:Arr u8 _) -> i64 = len(a)\nfn main() -> i64 = 0'),
    ('no-main', 1, False, 'fn helper() -> i64 = 0'),
    ('i64-overflow', 1, False, 'fn main() -> i64 = 9223372036854775808'),
    ('i64-underflow', 1, False, 'fn main() -> i64 = -9223372036854775809'),
    ('unary', 1, False, 'fn main() -> i64 = -true'),
    ('arithmetic', 1, False, 'fn main() -> i64 = 1 + 2.0'),
    ('logic', 1, False, 'fn main() -> i64 = if true && 1 then 1 else 0'),
    ('compare', 1, False, 'fn main() -> i64 = if false < true then 1 else 0'),
    ('equality', 1, False, 'fn main() -> i64 = if 0 == true then 1 else 0'),
    ('cast', 1, False, 'fn main() -> i64 = i64(true)'),
    ('condition', 1, False, 'fn main() -> i64 = if 1 then 2 else 3'),
    ('branches', 1, False, 'fn main() -> i64 = if true then 1 else false'),
    ('call-arity', 1, False, 'fn f(x:i64) -> i64 = x\nfn main() -> i64 = f()'),
    ('call-type', 1, False, 'fn f(x:i64) -> i64 = x\nfn main() -> i64 = f(false)'),
    ('builtin-arity', 1, False, 'fn main() -> unit = noop(1)'),
    ('division', 0, True, 'fn main() -> i64 = 12 / 3'),
    ('division-unproven', 1, False, 'fn main(x:i64) -> i64 = 12 / x'),
    ('remainder', 0, True, 'fn main() -> i64 = 12 % 3'),
    ('guarded-quotient-invariant', 0, True, 'fn main() -> i64 = loop(i=0,d:i64{d>=1}=1000) while i<6 next(i+1,if d>=10 then d/10 else 1) yield d'),
    ('range-conditional-bound', 0, True, 'fn main(n:i64) -> Arr u8 _ = arr(i in 0..(if n<0 then 0 else n)) u8(0)'),
    ('refinement-across-joins', 0, True,
     'fn positive() -> i64{result>=1} = 1\nfn require(n:i64{n>=1}) -> i64 = n\n'
     'fn main(x:i64) -> i64 = let n=positive() in '
     + ''.join(f'let v{i}=if x>{i} then x else 0 in ' for i in range(10)) + 'require(n)'),
    ('quotient-postcondition', 0, True, 'fn main(x:i64{x>=10,x<20}) -> i64{result==1} = x/10'),
    ('remainder-index', 0, True, 'fn main(x:i64{x>=0}) -> i64 = i64("abcdefghij"[x%10])'),
    ('array', 0, True, 'fn main() -> Arr u8 _ = "hi"'),
    ('array-expression', 0, True, 'fn main() -> i64 = let a="hi" in len(a)'),
    ('literal-index', 0, True, 'fn main() -> i64 = i64("hi"[1])'),
    ('literal-index-out', 1, False, 'fn main() -> i64 = i64("hi"[2])'),
    ('negative-index', 1, False, 'fn main() -> i64 = i64("hi"[-1])'),
    ('empty-index', 1, False, 'fn main() -> i64 = i64(""[0])'),
    ('wrong-index-type', 1, False, 'fn main() -> i64 = i64("hi"[false])'),
    ('not-array-index', 1, False, 'fn main() -> i64 = 2[0]'),
    ('not-array-len', 1, False, 'fn main() -> i64 = len(2)'),
    ('utf8-length', 0, True, 'fn main() -> Arr u8 (2) = "é"'),
    ('wrong-return-length', 1, False, 'fn main() -> Arr u8 (1) = "hi"'),
    ('wrong-return-shape', 1, False, 'fn f() -> Arr i64 _ = "hi"\nfn main() -> i64 = 0'),
    ('wrong-main-array', 1, False, 'fn main() -> Arr i64 _ = arr(i in 0..0) i'),
    ('invalid-size-param', 1, False, 'fn f(a:Arr u8 (1)) -> i64 = len(a)\nfn main() -> i64 = 0'),
    ('missing-size-return', 1, False, 'fn f() -> Arr u8 n = "hi"\nfn main() -> i64 = 0'),
    ('wrong-size-binder', 1, False, 'fn f(n:bool,a:Arr u8 n) -> i64 = len(a)\nfn main() -> i64 = 0'),
    ('implicit-size', 0, True, 'fn f(a:Arr u8 n) -> i64 = n\nfn main() -> i64 = f("hi")'),
    ('explicit-size', 0, True, 'fn f(n:i64,a:Arr u8 n) -> i64 = n\nfn main() -> i64 = f(2,"hi")'),
    ('explicit-size-mismatch', 1, False, 'fn f(n:i64,a:Arr u8 n) -> i64 = n\nfn main() -> i64 = f(1,"hi")'),
    ('shared-size', 0, True, 'fn f(a:Arr u8 n,b:Arr u8 n) -> i64 = n\nfn main() -> i64 = f("hi","ok")'),
    ('shared-size-mismatch', 1, False, 'fn f(a:Arr u8 n,b:Arr u8 n) -> i64 = n\nfn main() -> i64 = f("hi","x")'),
    ('independent-existentials', 0, True, 'fn f(a:Arr u8 _,b:Arr u8 _) -> i64 = len(a)+len(b)\nfn main() -> i64 = f("hi","x")'),
    ('array-argument-type', 1, False, 'fn f(a:Arr u8 n) -> i64 = n\nfn main() -> i64 = f(arr(i in 0..2) i)'),
    ('dependent-return', 0, True, 'fn f(a:Arr u8 n) -> Arr u8 n = a\nfn main() -> Arr u8 (2) = f("hi")'),
    ('affine-return', 0, True, 'fn f(a:Arr u8 n) -> Arr u8 (2*n+1) = concat(a,a,"!")\nfn main() -> Arr u8 (5) = f("hi")'),
    ('existential-return', 0, True, 'fn f() -> Arr u8 _ = "hi"\nfn main() -> i64 = let a=f() in len(a)'),
    ('array-join', 0, True, 'fn main(x:i64) -> Arr u8 _ = if x<0 then "x" else "hi"'),
    ('array-join-type', 1, False, 'fn f(b:bool) -> Arr u8 _ = if b then "x" else arr(i in 0..1) i\nfn main() -> i64 = 0'),
    ('array-equality', 1, False, 'fn main() -> i64 = if "x" == "x" then 1 else 0'),
    ('guarded-index', 0, True, 'fn f(a:Arr u8 n,i:i64) -> i64 = if 0<=i && i<n then i64(a[i]) else 0\nfn main() -> i64 = f("hi",1)'),
    ('else-index', 0, True, 'fn f(a:Arr u8 n,i:i64) -> i64 = if i<0 || i>=n then 0 else i64(a[i])\nfn main() -> i64 = f("hi",1)'),
    ('check-index', 0, True, 'fn f(a:Arr u8 n,i:i64) -> i64 = check i>=0 && i<n in i64(a[i])\nfn main() -> i64 = f("hi",1)'),
    ('affine-index', 0, True, 'fn f(a:Arr u8 n,i:i64) -> i64 = check i>=0 && 2*i+1<n in i64(a[2*i])\nfn main() -> i64 = f("hi",0)'),
    ('index-wrong-branch', 1, False, 'fn f(a:Arr u8 n,i:i64) -> i64 = if 0<=i && i<n then 0 else i64(a[i])\nfn main() -> i64 = f("hi",1)'),
    ('range', 0, True, 'fn f(a:Arr u8 n) -> Arr u8 n = arr(i in 0..n) a[i]\nfn main() -> Arr u8 (2) = f("hi")'),
    ('range-negative', 1, False, 'fn main() -> Arr u8 _ = arr(i in 2..1) u8(i)'),
    ('range-symbolic', 1, False, 'fn main(n:i64) -> Arr u8 _ = arr(i in 0..n) u8(i)'),
    ('range-type', 1, False, 'fn main() -> Arr u8 _ = arr(i in false..1) u8(i)'),
    ('sum-array', 0, True, 'fn f(a:Arr i64 n) -> i64 = sum(i in 0..n) a[i]\nfn main() -> i64 = f(arr(i in 0..5) i)'),
    ('push', 0, True, 'fn main() -> Arr u8 (3) = push("hi",\'!\')'),
    ('push-type', 1, False, 'fn main() -> Arr u8 _ = push("hi",1)'),
    ('set', 0, True, 'fn main() -> Arr u8 (2) = set("hi",1,\'!\')'),
    ('set-bounds', 1, False, 'fn main() -> Arr u8 _ = set("hi",2,\'!\')'),
    ('set-index-type', 1, False, 'fn main() -> Arr u8 _ = set("hi",true,\'!\')'),
    ('concat-u16', 0, True, 'fn f() -> Arr u16 (2) = concat(arr(i in 0..1) u16(i),arr(i in 0..1) u16(i))\nfn main() -> i64 = len(f())'),
    ('concat-mixed', 1, False, 'fn f() -> Arr u16 _ = concat(arr(i in 0..1) u16(i),"a")\nfn main() -> i64 = 0'),
    ('large-divisor', 0, True, 'fn main() -> i64 = if 9223372036854775807 > 0 then 12 / 9223372036854775807 else 0'),
    ('large-negative-divisor', 0, True, 'fn main() -> i64 = 12 / -9223372036854775808'),
    ('large-index-unproven', 1, False, 'fn main() -> i64 = i64("x"[9223372036854775807])'),
    ('large-affine-index', 0, True, 'fn main(n:i64) -> i64 = check n==1 in i64("x"[9223372036854775807*(n-1)])'),
    ('big-affine-index', 0, True, 'fn main(n:i64) -> i64 = check n==1 in i64("x"[9223372036854775807*(9223372036854775807*(n-1))])'),
    ('big-affine-counterexample', 1, False, 'fn main(n:i64) -> i64 = check n>=1 in i64("x"[9223372036854775807*(9223372036854775807*(n-1))])'),
    ('nested-array', 0, True, 'fn f() -> Arr Arr u8 _ _ = arr(i in 0..1) "a"\nfn main() -> i64 = 0'),
    ('nested-index', 0, True, 'fn main() -> i64 = let a=arr(i in 0..2) "hi" in i64(a[1][1])'),
    ('nested-index-out', 1, False, 'fn main() -> i64 = let a=arr(i in 0..2) "hi" in i64(a[1][2])'),
    ('nested-param', 0, True, 'fn f(a:Arr Arr u8 _ n) -> i64 = n\nfn main() -> i64 = f(arr(i in 0..2) "hi")'),
    ('nested-param-shape', 1, False, 'fn f(a:Arr Arr u8 _ n) -> i64 = n\nfn main() -> i64 = f("hi")'),
    ('nested-return', 0, True, 'fn f() -> Arr Arr u8 _ (2) = arr(i in 0..2) "hi"\nfn main() -> i64 = let b=f()[0] in check len(b)>1 in i64(b[1])'),
    ('nested-push', 0, True, 'fn main() -> i64 = let a=arr(i in 0..2) "hi" in let b=push(a,"ok") in i64(b[2][0])'),
    ('nested-push-shape', 1, False, 'fn main() -> i64 = let a=arr(i in 0..2) "hi" in len(push(a,0))'),
    ('nested-push-length', 1, False, 'fn main() -> i64 = let a=arr(i in 0..2) "hi" in len(push(a,"x"))'),
    ('nested-set', 0, True, 'fn main() -> i64 = let a=arr(i in 0..2) "hi" in let b=set(a,1,"ok") in i64(b[1][0])'),
    ('nested-branches', 1, False, 'fn main(x:i64) -> i64 = len(if x>0 then arr(i in 0..2) "hi" else arr(i in 0..2) "x")'),
    ('nested-ragged', 0, True, 'fn main() -> i64 = let a=arr(i in 0..3) arr(j in 0..i) u8(j) in let b=a[2] in check len(b)>0 in i64(b[0])'),
    ('nested-uniform-symbolic', 0, True, 'fn f(n:i64{n>0}) -> i64 = let a=arr(i in 0..2) arr(j in 0..n) u8(j) in i64(a[0][0])\nfn main() -> i64 = f(2)'),
    ('nested-ragged-distinct', 1, False, 'fn main() -> i64 = let a=arr(i in 0..2) arr(j in 0..i) u8(j) in\n  let b=a[1] in let c=a[0] in check len(b)>0 in i64(c[0])'),
    ('nested-ragged-branch', 1, False, 'fn main() -> i64 = let a=arr(i in 0..2) if i==0 then "" else "x" in\n  let b=a[1] in let c=a[0] in check len(b)>0 in i64(c[0])'),
    ('nested-ragged-push', 1, False, 'fn main() -> i64 = let a=arr(i in 0..2) arr(j in 0..i) u8(j) in\n  let b=arr(i in 0..1) "x" in let c=push(b,a[0]) in i64(c[1][0])'),
    ('record', 0, True, 'type Point = { x:i64 }\nfn main() -> i64 = let p=Point { x=1 } in p.x'),
    ('record-missing-field', 1, False, 'type Point = { x:i64,y:i64 }\nfn main() -> i64 = let p=Point { x=1 } in p.x'),
    ('record-field-type', 1, False, 'type Point = { x:i64 }\nfn main() -> i64 = let p=Point { x=true } in p.x'),
    ('record-unknown-field', 1, False, 'type Point = { x:i64 }\nfn main() -> i64 = let p=Point { x=1 } in p.y'),
    ('record-update', 0, True, 'type Point = { x:i64 }\nfn main() -> i64 = let p=Point { x=1 } in (p with { x=2 }).x'),
    ('record-update-type', 1, False, 'type Point = { x:i64 }\nfn main() -> i64 = let p=Point { x=1 } in (p with { x=false }).x'),
    ('record-param', 0, True, 'type Point = { x:i64 }\nfn f(borrow p:Point) -> i64 = p.x\nfn main() -> i64 = f(Point { x=1 })'),
    ('record-return', 0, True, 'type Point = { x:i64 }\nfn f() -> Point = Point { x=1 }\nfn main() -> i64 = f().x'),
    ('record-distinct', 1, False, 'type A = { x:i64 }\ntype B = { x:i64 }\nfn f(a:A) -> i64 = a.x\nfn main() -> i64 = f(B { x=1 })'),
    ('record-array', 0, True, 'type Point = { x:i64 }\nfn main() -> i64 = let a=arr(i in 0..3) Point { x=i } in a[1].x'),
    ('record-array-field', 0, True, 'type Text = { bytes:Arr u8 _ }\nfn main() -> i64 = let t=Text { bytes="hi" } in let a=t.bytes in check len(a)>0 in i64(a[0])'),
    ('record-projection', 0, True, 'type Text = { bytes:Arr u8 _ }\nfn f(t:Text) -> i64 = if len(t.bytes)>0 then i64(t.bytes[0]) else 0\nfn main() -> i64 = f(Text { bytes="hi" })'),
    ('record-projection-distinct', 1, False, 'type Text = { bytes:Arr u8 _ }\nfn f(a:Text,b:Text) -> i64 = check len(a.bytes)>0 in i64(b.bytes[0])\nfn main() -> i64 = f(Text { bytes="hi" },Text { bytes="" })'),
    ('record-projection-update', 1, False, 'type Text = { bytes:Arr u8 _ }\nfn f(a:Text) -> i64 = check len(a.bytes)>0 in let b=a with { bytes="" } in i64(b.bytes[0])\nfn main() -> i64 = f(Text { bytes="hi" })'),
    ('record-array-field-size', 1, False, 'type Text = { bytes:Arr u8 n }\nfn main() -> i64 = 0'),
    ('record-nested', 0, True, 'type Inner = { x:i64 }\ntype Outer = { value:Inner }\nfn main() -> i64 = let a=Outer { value=Inner { x=1 } } in a.value.x'),
    ('record-sum', 0, True, 'type Point = { x:i64,y:f64 }\nfn main() -> i64 = let p=sum(i in 0..3) Point { x=i,y=f64(i) } in p.x'),
    ('record-recursion', 1, False, 'type Link = { next_link:Link }\nfn main() -> i64 = 0'),
    ('record-duplicate-field', 1, False, 'type Point = { x:i64,x:i64 }\nfn main() -> i64 = 0'),
    ('generic-record', 0, True, 'type Box<T> = { value:T }\nfn main() -> i64 = 0'),
    ('effect', 0, True, 'effect fn main() -> unit = noop()'),
    ('effect-call', 0, True, 'effect(fs) fn work() -> i64 = 7\neffect(fs) fn main() -> i64 = work()'),
    ('effect-pure-call', 1, False, 'effect fn work() -> i64 = 7\nfn main() -> i64 = work()'),
    ('effect-comprehension', 1, False, 'effect fn work() -> i64 = 7\neffect fn main() -> i64 = sum(i in 0..1) work()'),
    ('effect-check', 1, False, 'effect fn work() -> bool = true\neffect fn main() -> i64 = check work() in 7'),
    ('effect-capability', 1, False, 'effect(fs) fn work() -> i64 = 7\neffect(time) fn main() -> i64 = work()'),
    ('effect-transitive', 1, False, 'effect(fs,net) fn first() -> i64 = 7\neffect fn second() -> i64 = first()\neffect(env) fn main() -> i64 = second()'),
    ('effect-unknown-capability', 1, False, 'effect(zebra,alpha) fn main() -> i64 = 7'),
    ('refinement', 0, True, 'fn main(x:i64{x>=0}) -> i64 = x'),
    ('refined-index', 0, True, 'fn f(a:Arr u8 n,i:i64{0<=i && i<n}) -> i64 = i64(a[i])\nfn main() -> i64 = f("hi",1)'),
    ('refined-index-missing', 1, False, 'fn f(a:Arr u8 n,i:i64{0<=i && i<n}) -> i64 = i64(a[i])\nfn main() -> i64 = f("hi",2)'),
    ('refined-array-parameter', 0, True, 'fn f(a:Arr u8 n{n>=1}) -> i64 = i64(a[0])\nfn main() -> i64 = f("hi")'),
    # Python's substitution drops the actual boolean formula and keeps the
    # declaration-time length on len(a). The native checker substitutes both.
    ('refined-array-length', 0, False, 'fn f(a:Arr u8 _{len(a)>=1}) -> i64 = i64(a[0])\nfn main() -> i64 = f("hi")'),
    ('refined-array-length-fail', 1, False, 'fn f(a:Arr u8 _{len(a)>=1}) -> i64 = i64(a[0])\nfn main() -> i64 = f("")'),
    ('refined-array-missing', 1, False, 'fn f(a:Arr u8 n{n>=1}) -> i64 = i64(a[0])\nfn main() -> i64 = f("")'),
    ('refinement-type', 1, False, 'fn main(x:i64{1}) -> i64 = x'),
    ('postcondition-type', 1, False, 'fn main() -> i64{1} = 0'),
    ('postcondition', 0, True, 'fn index() -> i64{result==1} = 1\nfn main() -> i64 = let i=index() in i64("hi"[i])'),
    ('postcondition-direct', 0, True, 'fn index() -> i64{result==1} = 1\nfn main() -> i64 = i64("hi"[index()])'),
    ('postcondition-if', 0, True, 'fn main(x:i64) -> i64{result>=0} = if x>=0 then x else 0'),
    ('postcondition-fail', 1, False, 'fn main() -> i64{result>0} = 0'),
    ('postcondition-distinct-calls', 1, False, 'fn idx(x:i64) -> i64{result==x} = x\nfn main() -> i64 = let a=idx(0) in let b=idx(2) in i64("hi"[b])'),
    ('disjunctive-index', 0, True, 'fn main(i:i64) -> i64 = if i==0 || i==1 then i64("hi"[i]) else 0'),
    ('disjunctive-index-unproven', 1, False, 'fn main(i:i64) -> i64 = if i==0 || i==2 then i64("hi"[i]) else 0'),
    ('nonzero-guard', 0, True, 'fn main(i:i64) -> i64 = if i!=0 then 12/i else 0'),
    ('boolean-refinement', 0, False, 'fn f(b:bool{b}) -> i64 = 1\nfn main() -> i64 = f(true)'),
    ('boolean-refinement-fail', 1, False, 'fn f(b:bool{b}) -> i64 = 1\nfn main() -> i64 = f(false)'),
    ('loop-scalar', 0, True, 'fn main() -> i64 = loop(i=0) while i<4 next(i+1) yield i'),
    ('loop-next-type', 1, False, 'fn main() -> i64 = loop(i=0) while i<4 next(false) yield i'),
    ('loop-condition-type', 1, False, 'fn main() -> i64 = loop(i=0) while i next(i+1) yield i'),
    ('loop-initial-type', 1, False, 'fn main() -> i64 = loop(i:bool=0) while i next(false) yield 1'),
    ('loop-invariant', 0, True, 'fn main() -> i64{result>=0} = loop(i:i64{i>=0}=0) while i<4 next(i+1) yield i'),
    ('loop-invariant-type', 1, False, 'fn main() -> i64 = loop(i:i64{1}=0) while i<4 next(i+1) yield i'),
    ('loop-invariant-initial', 1, False, 'fn main() -> i64 = loop(i:i64{i>=0}=-1) while i<4 next(i+1) yield i'),
    ('loop-invariant-next', 1, False, 'fn main() -> i64 = loop(i:i64{i>=0}=0) while i<4 next(i-1) yield i'),
    ('loop-array-preserved', 0, True, 'fn main() -> Arr u8 (2) = loop(i:i64{i>=0}=0,a="hi") while i<len(a) next(i+1,set(a,i,\'!\')) yield a'),
    ('loop-array-widened', 0, True, 'fn main() -> Arr u8 _ = loop(a="") while len(a)<4 next(push(a,\'!\')) yield a'),
    ('loop-array-widened-index', 0, True, 'fn main() -> i64 = loop(a="x",i:i64{i>=0}=0) while i<len(a) && i<4 next(push(a,a[i]),i+1) yield len(a)'),
    ('loop-array-widened-bad-index', 1, False, 'fn main() -> i64 = loop(a="x",i=0) while i<4 next(push(a,a[i]),i+1) yield len(a)'),
    ('allocation-stats', 0, True, 'fn main() -> i64 = if allocation_stats_enabled() then 1 else 0'),
    ('allocation-stats-arity', 1, False, 'fn main() -> i64 = if allocation_stats_enabled(1) then 1 else 0'),
    ('spawn-thread', 0, True, 'effect(unsafe) fn main() -> i64 = spawn_thread(null(),null())'),
    ('spawn-thread-pure', 1, False, 'fn main() -> i64 = spawn_thread(null(),null())'),
    ('spawn-thread-type', 1, False, 'effect(unsafe) fn main() -> i64 = spawn_thread(null(),0)'),
    ('fiber-swap', 0, True, 'effect(unsafe) fn main() -> unit = fiber_swap(null(),null())'),
    ('fiber-init-arity', 1, False, 'effect(unsafe) fn main() -> unit = fiber_init(null(),null(),null())'),
    ('bitwise-builtin', 0, True, 'fn main(x:i64) -> i64 = i64("abcd"[bit_and(x,3)])'),
    ('bitwise-builtin-type', 1, False, 'fn main() -> i64 = bit_and(3,true)'),
    ('sqrt-builtin-type', 1, False, 'fn main() -> f64 = sqrt(1)'),
    ('raw-memory', 0, True, 'effect(unsafe) fn main() -> i64 = let p=stack_alloc(8) in let w=store_i64(p,0,42) in load_i64(p,0)'),
    ('raw-memory-pure', 1, False, 'fn main() -> i64 = load_i64(null(),0)'),
    ('raw-memory-capability', 1, False, 'effect(fs) fn main() -> i64 = load_i64(null(),0)'),
    ('raw-memory-type', 1, False, 'effect(unsafe) fn main() -> i64 = load_i64(0,0)'),
    ('raw-memory-transitive', 1, False, 'effect fn leaf() -> i64 = load_i64(null(),0)\neffect fn middle() -> i64 = leaf()\neffect(fs) fn main() -> i64 = middle()'),
    ('runtime-state', 0, True, 'effect(unsafe) fn main() -> i64 = load_i64(runtime_state(),40)'),
    ('runtime-state-arity', 1, False, 'effect(unsafe) fn main() -> i64 = ptr_to_i64(runtime_state(1))'),
    ('runtime-state-capability', 1, False, 'effect(env) fn main() -> i64 = ptr_to_i64(runtime_state())'),
    ('atomic-store-type', 1, False, 'effect(unsafe) fn main() -> unit = atomic_store_i32(null(),0,1)'),
    ('address-function', 0, True, 'fn f() -> i64 = 42\neffect(unsafe) fn main() -> i64 = ptr_to_i64(addr(f))'),
    ('address-value', 1, False, 'effect(unsafe) fn main() -> i64 = let v=1 in ptr_to_i64(addr(v))'),
    ('data-temporary', 1, False, 'effect(unsafe) fn main() -> i64 = ptr_to_i64(data(concat("a","b")))'),
    ('data-nested', 1, False, 'effect(unsafe) fn main() -> i64 = let a=arr(i in 0..1) "x" in ptr_to_i64(data(a))'),
    ('view-length', 0, True, 'effect(unsafe) fn main() -> i64 = let a=view(data("abc"),3) in i64(a[2])'),
    ('view-negative-length', 1, False, 'effect(unsafe) fn main() -> i64 = len(view(null(),-1))'),
    ('byte-uninit-length', 0, True, 'effect(unsafe) fn main() -> Arr u8 (8) = byte_uninit(8)'),
    ('byte-uninit-unproven', 1, False, 'effect(unsafe) fn main(n:i64) -> i64 = len(byte_uninit(n))'),
    ('generic-inferred', 0, True, 'fn id<T>(x:T) -> T = x\nfn main() -> i64 = id(42)'),
    ('generic-array-shape', 0, True, 'fn id<T>(x:T) -> T = x\nfn main() -> i64 = len(id("abc"))'),
    ('generic-record-argument', 0, True, 'type Box<T> = {value:T}\nfn get<T>(x:Box<T>) -> T = x.value\nfn main() -> i64 = get(Box::<i64> {value=42})'),
    ('generic-unused-template', 0, True, 'type Box<T> = {value:T}\nfn broken<T>(x:T) -> i64 = true\nfn main() -> i64 = 42'),
    ('generic-conflict', 1, False, 'fn pick<T>(x:T,y:T) -> T = x\nfn main() -> i64 = pick(1,false)'),
    ('generic-missing', 1, False, 'fn make<T>() -> i64 = 1\nfn main() -> i64 = make()'),
    ('generic-record-arity', 1, False, 'type Box<T> = {value:T}\nfn main() -> i64 = (Box::<i64,bool> {value=1}).value'),
    ('generic-array-record-argument', 0, True, 'type Box<T> = {value:T}\nfn get<T>(a:Arr Box<T> n) -> i64 = n\nfn main() -> i64 = get(arr(i in 0..3) Box::<i64> {value=i})'),
    ('generic-enum', 0, True, 'enum Choice<T> { Missing, Present(T) }\nfn main() -> i64 = match Present(42) { Missing => 0, Present(value) => value }'),
    ('enum-inactive-storage', 0, True, 'type Box = {bytes:Arr u8 _}\nenum Choice { Empty, Present(Box) }\nfn main() -> i64 = match Empty() { Empty => 0, Present(value) => len(value.bytes) }'),
    ('enum-duplicate-arm', 1, False, 'enum Choice { A, B }\nfn main() -> i64 = match A() { A => 0, A => 1, B => 2 }'),
    ('enum-nonexhaustive', 1, False, 'enum Choice { A, B }\nfn main() -> i64 = match A() { A => 0 }'),
    ('enum-binding-arity', 1, False, 'enum Choice { A(i64), B }\nfn main() -> i64 = match A(1) { A => 0, B => 1 }'),
    ('enum-unreachable-arm', 1, False, 'enum Choice { A, B }\nfn main() -> i64 = match A() { _ => 0, A => 1 }'),
    ('enum-storage-private', 1, False, 'enum Choice { A, B }\nfn main() -> i64 = A().__tag'),
    ('enum-literal-private', 1, False, 'enum Choice { A, B }\nfn main() -> i64 = let a=Choice { __tag=0 } in 1'),
    ('result-propagation', 0, True, 'enum Result<T,E> { Err(E), Ok(T) }\nfn source() -> Result<i64,i64> = Err::<i64,i64>(-1)\nfn convert() -> Result<Arr u8 _,i64> = let x=source()? in Ok::<Arr u8 _,i64>(arr(i in 0..1) u8(x))\nfn main() -> i64 = match convert() { Err(code) => code, Ok(text) => len(text) }'),
    ('result-mismatched-error', 1, False, 'enum Result<T,E> { Ok(T), Err(E) }\nfn source() -> Result<i64,i64> = Err::<i64,i64>(-1)\nfn convert() -> Result<i64,bool> = let x=source()? in Ok::<i64,bool>(x)\nfn main() -> i64 = 1'),
    ('result-bare-propagation', 1, False, 'enum Result<T,E> { Ok(T), Err(E) }\nfn main() -> i64 = Ok::<i64,i64>(1)?'),
    ('unused-empty-enum', 1, False, 'enum Empty<T> {}\nfn main() -> i64 = 0'),
    ('generic-resource', 1, False, 'resource type Box<T> = {value:T} drop close\neffect fn close(x:Box<i64>) -> unit = noop()\nfn main() -> i64 = 0'),
    ('fork-arity', 1, False, 'effect(unsafe) fn main() -> i64 = fork_syscall(0)'),
    ('fork-effect', 1, False, 'fn main() -> i64 = fork_syscall()'),
    ('clamped-local-postcondition', 0, True, 'effect(unsafe) fn main() -> i64{result>=1,result<=256} = let p=runtime_state() in let cached=load_i64(p,1600) in if cached>=1 && cached<=256 then cached else let n=if load_ptr(p,0)==null() then load_i64(p,40) else load_i64(p,64) in let bounded=if n<1 then 1 else if n>256 then 256 else n in let saved=store_i64(p,1600,bounded) in bounded'),
    ('record-array-branches', 0, True, 'type Box = {value:i64}\nfn choose(x:i64) -> Arr Box (1) = if x>0 then arr(i in 0..1) Box {value=x} else arr(i in 0..1) Box {value=0}\nfn main() -> i64 = choose(42)[0].value'),
    ('resource-borrow', 0, True, RESOURCE + 'effect(process) fn main() -> i64 = using x=make() in observe(x)'),
    ('resource-move', 0, True, RESOURCE + 'effect(process) fn main() -> i64 = using x=make() in using y=x in take(y)'),
    ('resource-use-after-move', 1, False, RESOURCE + 'effect(process) fn main() -> i64 = using x=make() in let done=take(x) in observe(x)'),
    ('resource-branch-move', 1, False, RESOURCE + 'effect(process) fn main(n:i64) -> i64 = using x=make() in let done=if n>0 then take(x) else 0 in observe(x)'),
    ('resource-borrowed-move', 1, False, RESOURCE + 'effect(process) fn bad(x:Owner) -> i64 = take(x)\nfn main() -> i64 = 0'),
    ('resource-contained', 1, False, RESOURCE + 'type Bad = {items:Arr Owner _}\nfn main() -> i64 = 0'),
    ('resource-return-borrow', 1, False, RESOURCE + 'fn bad(x:Owner) -> Owner = x\nfn main() -> i64 = 0'),
    ('resource-cleanup-capability', 1, False, RESOURCE + 'effect fn work() -> i64 = using x=make() in observe(x)\neffect(fs) fn main() -> i64 = work()'),
    ('resource-loop-local', 0, True, RESOURCE + 'effect(process) fn main() -> i64 = using x=make() in let n=loop(x=0) while x<3 next(x+1) yield x in n+observe(x)'),
)


def compare(neoc, path, native_status, python_ok):
    native = subprocess.run([neoc, 'check', str(ROOT), str(path)], capture_output=True, text=True, timeout=30)
    reference = subprocess.run([str(ROOT / 'neoc.sh'), 'check', str(path)], capture_output=True, text=True, timeout=30)
    report = json.loads(reference.stdout)
    assert (reference.returncode, report['ok']) == (0 if python_ok else 1, python_ok), report
    if native_status == 0 and not python_ok:
        assert not report.get('errors') and any(
            o['kind'] == 'precondition' and o['status'] == 'unproven' for o in report['obligations']
        ), report
    assert native.returncode == native_status and not native.stderr, native
    if native_status == 0:
        assert native.stdout == '(ok)\n', native.stdout
    elif native_status == 1:
        if not report.get('errors'):
            locations = {
                f"(unproven {path} {o['pos'][0]}:{o['pos'][1]} {o['kind']})\n"
                for o in report['obligations'] if o['status'] == 'unproven'
            }
            assert native.stdout in locations, (native.stdout, locations)
            return
        error = report['errors'][0]
        assert error['kind'] in ('type', 'language'), error
        # The native checker reports the location and types without rendering the argument AST.
        message = re.sub(r'^argument .+ has type ', 'argument has type ', error['msg'])
        message = re.sub(r'^concat: argument .+ must be ', 'concat: argument must be ', message)
        line, col = error['pos']
        assert native.stdout == f"(error {error.get('file') or path} {line}:{col} {message})\n", (native.stdout, error)
    else:
        assert native.stdout.startswith('(unsupported '), native.stdout


def run_case(neoc, root, case):
    name, status, ok, source = case
    path = root / f'{name}.neo'
    path.write_text(source + '\n', encoding='utf-8')
    try:
        compare(neoc, path, status, ok)
    except AssertionError as exc:
        raise AssertionError(f'{name}: {exc}') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('neoc', type=Path)
    args = parser.parse_args()
    neoc = args.neoc.resolve()
    with TemporaryDirectory(prefix='neo-check-diff-') as tmp:
        root = Path(tmp).resolve()
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(partial(run_case, neoc, root), CASES))

        lib = root / 'lib.neo'
        entry = root / 'entry.neo'
        entry.write_text('import "lib.neo" as lib\nfn main() -> i64 = lib::twice(2)\n', encoding='utf-8')
        lib.write_text('pub fn twice(x:i64) -> i64 = x + x\n', encoding='utf-8')
        compare(neoc, entry, 0, True)
        lib.write_text('pub fn twice(x:i64) -> i64 = x + false\n', encoding='utf-8')
        compare(neoc, entry, 1, False)

        lib.write_text('pub sealed type Token = {value:i64}\npub fn token() -> Token = Token {value=42} with {value=43}\n', encoding='utf-8')
        sealed = (
            (0, True, 'lib::token().value'),
            (1, False, '(lib::Token {value=1}).value'),
            (1, False, '(lib::token() with {value=1}).value'),
        )
        for status, ok, expr in sealed:
            entry.write_text(f'import "lib.neo" as lib\nfn main() -> i64 = {expr}\n', encoding='utf-8')
            compare(neoc, entry, status, ok)

        lib.write_text('pub enum Choice<T> { Missing, Present(T) }\npub fn make<T>(x:T) -> Choice<T> = Present(x)\n', encoding='utf-8')
        entry.write_text('import "lib.neo" as lib\nfn main() -> i64 = match lib::make(42) { lib::Missing => 0, lib::Present(x) => x }\n', encoding='utf-8')
        compare(neoc, entry, 0, True)

    print(f'{len(CASES) + 3 + len(sealed)} checker cases matched the expected Python comparison')


if __name__ == '__main__':
    main()
