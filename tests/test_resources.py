import unittest
from neoc.syntax import parse
from neoc.check import Checker,CheckError
from neoc.graph import hash_program

PRELUDE='''
resource type Handle = { number:i64 } drop release
effect fn release(h:Handle) -> unit = noop()
effect fn create() -> Handle = Handle { number = 1 }
fn borrow(h:Handle) -> i64 = h.number
effect fn consume(move h:Handle) -> unit = noop()
'''


class Resources(unittest.TestCase):
    def check(self,body):
        p=parse(PRELUDE+body);hash_program(p);Checker(p).run();return p

    def test_scoped_borrows_and_transfer(self):
        p=self.check('effect fn main() -> i64 = using h = create() in let a = borrow(h) in let moved = consume(h) in a')
        self.assertTrue(any(getattr(f.body,'resource_scope',False) for f in p.fns if f.name=='consume'))

    def test_consumed_resources_mark_runtime_ownership_transfer(self):
        from neoc import syntax as S
        p=self.check('effect fn main() -> unit = using h = create() in if true then consume(h) else noop()')
        def moves(node):
            return int(getattr(node,'resource_move',False))+sum(moves(child) for child in S.children(node))
        self.assertGreaterEqual(sum(moves(fn.body) for fn in p.fns),2)

    def test_factory_can_construct_new_owner_after_nested_cleanup(self):
        self.check('effect fn factory()->Handle=using temporary=create() in Handle {number=borrow(temporary)+1} effect fn main()->i64=using owner=factory() in borrow(owner)')
        self.check('effect fn factory(flag:bool)->Handle=using outer=create() in using inner=create() in if flag then Handle {number=1} else Handle {number=2} effect fn main()->i64=using owner=factory(true) in borrow(owner)')

    def test_factory_cleanup_does_not_allow_owner_escape(self):
        for body in [
            'effect fn factory()->Handle=using temporary=create() in temporary fn main()->i64=0',
            'effect fn factory()->Handle=using outer=create() in using inner=create() in outer fn main()->i64=0',
            'effect fn factory()->Handle=using temporary=create() in let alias=temporary in alias fn main()->i64=0',
        ]:
            with self.subTest(body=body),self.assertRaises(CheckError):self.check(body)

    def test_use_after_move_borrow_escape_and_repeating_moves(self):
        for body,diagnostic in [
            ('effect fn main() -> i64 = using h = create() in let a = consume(h) in borrow(h)','after move'),
            ('effect fn main() -> i64 = let h = create() in borrow(h)','using'),
            ('effect fn escape() -> Handle = using h = create() in h effect fn main() -> i64 = 0','escape'),
            ('effect fn escape(h:Handle) -> unit = consume(h) effect fn main() -> i64 = 0','borrowed'),
            ('effect fn main() -> i64 = using h = create() in let a = if true then consume(h) else noop() in borrow(h)','after move'),
            ('effect fn main() -> i64 = using h = create() in loop(i=0) while i < 2 next(let x=consume(h) in i+1) yield i','repeating'),
            ('type Box = { owner:Handle } effect fn main() -> i64 = 0','stored'),
        ]:
            with self.subTest(body=body),self.assertRaises(CheckError) as caught:self.check(body)
            self.assertIn(diagnostic,str(caught.exception.errors))


if __name__=='__main__':unittest.main()

class ResourceReferences(unittest.TestCase):
    PRELUDE='''
resource type Arena={token:i64} drop arena_drop
effect(fs,net,process) fn arena_drop(arena:Arena)->unit=noop()
effect(process) fn arena_new()->Arena=Arena { token=1 }
effect fn rt_arena_register(token:i64,value:ptr,finalizer:ptr)->i64=0
effect fn rt_arena_lookup(token:i64,key:i64)->ptr=null()
effect fn rt_arena_release(token:i64,key:i64)->unit=noop()
resource type Handle={value:i64} drop release
effect(fs) fn release(handle:Handle)->unit=noop()
effect(process) fn create()->Handle=Handle { value=42 }
fn inspect(handle:Handle)->i64=handle.value
'''
    def check(self, body):
        p=parse(self.PRELUDE+body);hash_program(p);Checker(p).run();return p

    def test_handles_are_storable_and_borrows_are_immediate(self):
        self.check('''type State={handle:Ref<Handle>}
effect(fs,net,process) fn main()->i64=using arena=arena_new() in using value=create() in
let state=State { handle=adopt(value,arena) } in inspect(borrow_ref(state.handle))''')

    def test_resource_reference_cannot_escape_as_borrow_or_be_moved_twice(self):
        for body in [
            'effect(fs,net,process) fn main()->i64=using arena=arena_new() in using value=create() in let held=adopt(value,arena) in inspect(value)',
            'effect(fs,net,process) fn main()->i64=using arena=arena_new() in using value=create() in let held=adopt(value,arena) in let borrowed=borrow_ref(held) in inspect(borrowed)',
            'effect(fs,net,process) fn move_borrow(value:Handle,arena:Arena)->Ref<Handle> = adopt(value,arena) fn main()->i64=0',
            'fn invalid(value:Ref<i64>)->i64=0 fn main()->i64=0',
            'effect(fs,net,process) fn main()->i64=ref_null()',
        ]:
            with self.subTest(body=body), self.assertRaises(CheckError):self.check(body)
