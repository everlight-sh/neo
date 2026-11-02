import unittest
from neoc import syntax as S
from neoc.graph import hash_program
from neoc.check import Checker,CheckError
from neoc.elaborate import ElaborationError
from neoc.reference import Reference


class LanguageTypes(unittest.TestCase):
    def program(self,source):
        p=S.parse(source);hash_program(p);Checker(p).run();return p

    def test_multiple_specializations_and_nested_owned_alternatives(self):
        p=self.program('''
enum Option<T> { None, Some(T) }
type Box<T> = { value: T }
fn identity<T>(x: T) -> T = x
fn unwrap<T>(x: Option<T>, fallback: T) -> T
  = match x { Some(value) => value, None => fallback }
fn main () -> i64
  = let a = Box::<Arr u8 _> { value = identity::<Arr u8 _>("hello") } in
    let b = unwrap::<i64>(Some::<i64>(identity::<i64>(37)),0) in len(a.value) + b
''')
        self.assertEqual(Reference(p).call('main',[]),42)
        self.assertEqual(sum(f.name.startswith('identity__') for f in p.fns),2)

    def test_exhaustiveness_arity_and_private_representation(self):
        for body,message in [
            ('match Some::<i64>(1) { None => 0 }','non-exhaustive'),
            ('match Some::<i64>(1) { Some(a,b) => a, None => 0 }','arity'),
            ('match Some::<i64>(1) { Some(a) => a, Some(b) => b, None => 0 }','duplicate'),
            ('match Some::<i64>(1) { _ => 0, Some(a) => a }','unreachable'),
            ('Some::<i64>(1).__tag','private'),
        ]:
            with self.subTest(body=body),self.assertRaises((ElaborationError,CheckError)) as caught:
                self.program('enum Option<T> { None, Some(T) } fn main () -> i64 = '+body)
            self.assertIn(message,str(caught.exception.errors))

    def test_wrong_payload_type_is_rejected_by_native_checker(self):
        with self.assertRaises(CheckError):self.program('enum Option<T> { None, Some(T) } fn main () -> i64 = match Some::<i64>("bad") { None => 0, Some(x) => x }')

    def test_error_bind_short_circuits_and_allows_different_success_type(self):
        source='''
enum Result<T,E> { Ok(T), Err(E) }
fn number(n:i64) -> Result<i64,Arr u8 _>
  = if n > 0 then Ok::<i64,Arr u8 _>(n) else Err::<i64,Arr u8 _>("bad")
fn convert(n:i64) -> Result<Arr u8 _,Arr u8 _>
  = let value = number(n)? in
    check value > 0 in Ok::<Arr u8 _,Arr u8 _>("done")
fn main(n:i64) -> i64 = match convert(n) { Ok(text) => len(text), Err(text) => 0 - len(text) }
'''
        p=self.program(source)
        self.assertEqual(Reference(p).call('main',[3]),4)
        self.assertEqual(Reference(p).call('main',[0]),-3)

    def test_recursive_types_and_runaway_specialization_are_diagnostics(self):
        with self.assertRaises(ElaborationError):self.program('type Infinite<T> = { child: Infinite<T> } fn main () -> Infinite<i64> = Infinite::<i64> { child = 0 }')
    def test_inferred_array_shape_does_not_capture_caller_lengths(self):
        p=self.program('''type Box<T> = { value:T }
fn choose<T>(a:T,b:T) -> T = a
fn box<T>(value:T) -> Box<T> = Box::<T> { value=value }
fn sizes(a:Arr u8 n,b:Arr u8 m) -> i64 = len(box(choose(a,b)).value)
fn main() -> i64 = sizes("hello","different")
''')
        self.assertEqual(Reference(p).call('main',[]),5)
    def test_unit_success_payloads_are_regular_values(self):
        p=self.program('''enum Result<T,E> { Ok(T),Err(E) }
type Box<T> = { value:T }
fn status() -> Result<unit,unit> = Ok::<unit,unit>(noop())
fn changed() -> Result<i64,unit> = let done=status()? in Ok::<i64,unit>(42)
fn main() -> i64 = let box=Box::<unit> { value=noop() } in let ignored=box.value in match changed() { Ok(value) => value,Err(error) => 0 }
''')
        self.assertEqual(Reference(p).call('main',[]),42)


if __name__=='__main__':unittest.main()
