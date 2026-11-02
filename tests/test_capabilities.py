import unittest
from neoc import syntax as S
from neoc.graph import hash_program
from neoc.check import Checker, CheckError

def checked(source):
    p=S.parse(source);hash_program(p);Checker(p).run();return p

class CapabilitiesTests(unittest.TestCase):
    def test_declared_transitive_effects(self):
        checked('effect(fs) fn read () -> i64 = 2 effect(fs) fn main () -> i64 = read()')
        with self.assertRaises(CheckError):
            checked('effect(fs) fn read () -> i64 = 2 effect(net) fn main () -> i64 = read()')
        with self.assertRaises(CheckError):
            checked('effect(fs) fn read () -> i64 = 2 effect fn wrapper () -> i64 = read() effect(net) fn main () -> i64 = wrapper()')

    def test_raw_pointer_access_requires_explicit_unsafe(self):
        with self.assertRaises(CheckError): checked('effect(fs) fn main () -> i64 = load_i64(null(),0)')
        checked('effect(unsafe) fn main () -> i64 = load_i64(null(),0)')
        with self.assertRaises(CheckError): checked('extern fn identity () -> i64 effect(fs) fn main () -> i64 = identity()')
        checked('extern fn identity () -> i64 effect(unsafe) fn main () -> i64 = identity()')

    def test_effectful_handlers_are_opt_in(self):
        checked('effect(fs) fn page (r: Arr u8 n) -> Arr u8 _ = "ok" effect(fs,net) fn main () -> i64 = serve_effect(8080,page)')
        with self.assertRaises(CheckError):
            checked('effect(fs) fn page (r: Arr u8 n) -> Arr u8 _ = "ok" effect(net) fn main () -> i64 = serve_effect(8080,page)')

if __name__=='__main__':unittest.main()
