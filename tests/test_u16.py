"""u16: UTF-16 code units as a scalar and array element type."""
import re
import unittest
from neoc import syntax as S
from neoc.check import Checker, CheckError
from neoc.graph import hash_program
from neoc.llvm import LLVMGen
from neoc.reference import Reference


def checked(source):
    program = S.parse(source); hashes = hash_program(program); checker = Checker(program); checker.run()
    return program, hashes, checker


def unproven(checker):
    return [o for o in checker.obligations if o['status'] not in ('proven', 'checked')]


class U16(unittest.TestCase):
    def test_values_follow_u8_conversions(self):
        p, _, ck = checked('''
fn units(t:Arr u8 n) -> Arr u16 n = arr(i in 0..n) u16(i64(t[i]) + 65280)
fn at(s:Arr u16 n,i:i64) -> i64 = if i>=0 && i<n then i64(s[i]) else -1
fn bigger(a:u16,b:u16) -> u16 = if a > b then a else b
fn main() -> i64
  = let s = units("ab") in let s2 = push(set(s,0,u16(70000)),u16(-1)) in let j = concat(s,s2) in
    at(j,0) + at(j,2) * 100000 + at(j,4) * 10000000000 + i64(bigger(u16(65535),u16(1))) * 0 + len(j)''')
        self.assertEqual(unproven(ck), [])
        # 65280+97, 70000 mod 65536, 65535 (wrapped -1); len 5
        self.assertEqual(Reference(p).call('main', []), (65280 + 97) + 4464 * 100000 + 65535 * 10000000000 + 5)

    def test_lowering_is_sixteen_bit_and_unsigned(self):
        p, hashes, _ = checked('''
fn lt(a:u16,b:u16) -> bool = a < b
fn widen(a:u16) -> i64 = i64(a)
fn narrow(a:i64) -> u16 = u16(a)
fn join(a:Arr u16 n,b:Arr u16 m) -> Arr u16 _ = concat(a,b)
fn get(a:Arr u16 n,i:i64) -> u16 = if i>=0 && i<n then a[i] else u16(0)
fn main() -> i64 = if lt(narrow(1),narrow(2)) then widen(get(join(arr(i in 0..2) u16(i),arr(i in 0..3) u16(i)),4)) else 0''')
        ir = LLVMGen(p.fns, hashes, 'x86_64-unknown-linux-gnu').program()
        def body(name):
            key = next(k for k in ('@ax_' + name + '__seq(', '@ax_' + name + '__par(') if k in ir)
            start = ir.index(key); return ir[start:ir.index('\n}', start)]
        self.assertIn('icmp ult i16', body('lt'))
        self.assertIn('zext i16', body('widen'))
        self.assertIn('trunc i64', body('narrow'))
        self.assertIn('load i16', body('get'))
        join = body('join')
        self.assertIn('getelementptr inbounds i16', join)
        self.assertRegex(join, r'mul nuw nsw i64 %t\d+, 2')
        self.assertNotIn('getelementptr inbounds i8, ptr', join)

    def test_unsound_or_mistyped_programs_are_rejected(self):
        for body, message in [
            ('let a = u16(1) in let b = u16(2) in i64(a + b)', 'operator +'),
            ('i64(u16(1.5))', 'cannot cast'),
            ('let a = u16(1) in if a < u8(2) then 1 else 0', 'comparison'),
            ('let a = u16(1) in if a == 1 then 1 else 0', 'equality'),
            ('len(concat("ab", arr(i in 0..2) u16(i)))', 'concat'),
            ('len(concat(arr(i in 0..2) u16(i), "ab"))', 'concat'),
            ('len(set(arr(i in 0..2) u16(i), 0, u8(1)))', 'set: value'),
            ('len(push(arr(i in 0..2) u16(i), 1))', 'push value'),
            ('len(byte_write_le(arr(i in 0..2) u16(i), 0, 1, 1))', 'byte array'),
            ('i64(u16(arr(i in 0..2) u16(i)))', 'cannot cast'),
        ]:
            with self.subTest(body=body), self.assertRaises(CheckError) as caught:
                checked('fn main() -> i64 = ' + body)
            self.assertIn(message, str(caught.exception.errors))

    def test_unproven_indexing_is_reported(self):
        _, _, ck = checked('fn get(a:Arr u16 n,i:i64) -> i64 = i64(a[i]) fn main() -> i64 = get(arr(k in 0..3) u16(k),1)')
        self.assertEqual([o['kind'] for o in unproven(ck)], ['bounds'])
        _, _, ck = checked('fn put(a:Arr u16 n,i:i64{i>=0}) -> Arr u16 n = set(a,i,u16(1)) fn main() -> i64 = len(put(arr(k in 0..3) u16(k),1))')
        self.assertEqual([o['kind'] for o in unproven(ck)], ['bounds'])


if __name__ == '__main__':
    unittest.main()
