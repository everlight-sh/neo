"""Else-if chains over one scalar lower to an LLVM switch; deep chains still prove."""
import re
import unittest
from neoc import syntax as S
from neoc.check import Checker
from neoc.graph import hash_program
from neoc.linear import Lin, cmp, and_, neg, entails
from neoc.llvm import LLVMGen
from neoc.reference import Reference


def emit(source, switches=True):
    program = S.parse(source); hashes = hash_program(program); checker = Checker(program); checker.run()
    gen = LLVMGen(program.fns, hashes, 'x86_64-unknown-linux-gnu', switches=switches)
    return program, gen.program(), gen, checker


def body(ir, name):
    key = next(k for k in ('@ax_' + name + '__seq(', '@ax_' + name + '__par(') if k in ir)
    start = ir.index(key); return ir[start:ir.index('\n}', start)]


def chain(n, var='op'):
    return ' else '.join(f'if {var} == {k} then {k * 10 + 1}' for k in range(n)) + ' else -1'


class SwitchLowering(unittest.TestCase):
    def test_integer_chain_is_one_switch_with_every_case(self):
        p, ir, gen, _ = emit('fn f(op:i64) -> i64 = ' + chain(40) + '\nfn main() -> i64 = f(3)')
        f = body(ir, 'f')
        self.assertEqual(f.count('switch i64'), 1)
        self.assertEqual(len(re.findall(r'i64 \d+, label %case', f)), 40)
        self.assertNotIn('icmp eq', f)
        self.assertEqual({s['cases'] for s in gen.switches}, {40})   # par and seq bodies
        for op in (-1, 0, 7, 39, 40):
            self.assertEqual(Reference(p).call('f', [op]), op * 10 + 1 if 0 <= op < 40 else -1)

    def test_match_fields_bytes_and_grouped_arms(self):
        _, ir, _, _ = emit('enum E { A, B(i64), C, D(i64), F }\n'
                           'fn f(e:E) -> i64 = match e { A => 1, B(x) => x, C => 3, D(y) => y + 1, F => 5 }\n'
                           'fn g(c:u8) -> i64 = if c == \'a\' then 1 else if c == \'b\' then 2 else if c == \'c\' then 3 else if c == \'\\xff\' then 4 else 0\n'
                           'type R = { tag : i64 }\n'
                           'fn h(r:R) -> i64 = if r.tag == 0 || r.tag == 5 then 1 else if r.tag == 1 then 2 else if r.tag == 2 || r.tag == 3 then 3 else 4\n'
                           'fn main() -> i64 = f(B(2)) + g(u8(97)) + h(R { tag = 5 })')
        self.assertEqual(body(ir, 'f').count('switch i64'), 1)
        self.assertIn('i8 -1, label %case', body(ir, 'g'))   # 255 as a signed i8 literal
        self.assertEqual(body(ir, 'g').count('switch i8'), 1)
        grouped = body(ir, 'h')
        self.assertEqual(grouped.count('switch i64'), 1)
        self.assertEqual(len(re.findall(r'i64 \d+, label %case', grouped)), 5)

    def test_duplicates_are_dead_and_semantics_hold(self):
        p, ir, _, _ = emit('fn f(op:i64) -> i64 = if op == 1 then 10 else if op == 2 then 20 else if op == 1 then 99 '
                           'else if op == 3 || op == 2 then 30 else if op == 4 then 40 else 0\nfn main() -> i64 = f(1)')
        self.assertEqual(body(ir, 'f').count('switch i64'), 1)
        self.assertNotIn(' 99', body(ir, 'f'))
        self.assertEqual([Reference(p).call('f', [op]) for op in range(6)], [0, 10, 20, 30, 40, 0])

    def test_shapes_that_stay_branches(self):
        for source in ['fn f(op:i64) -> i64 = ' + chain(3),                                          # too short
                       'fn k(x:i64) -> i64 = x\nfn f(op:i64) -> i64 = ' + chain(6, 'k(op)')]:           # not a plain read
            with self.subTest(source=source):
                _, ir, _, _ = emit(source + '\nfn main() -> i64 = f(3)')
                self.assertNotIn('switch', body(ir, 'f'))
        # A binder ends a chain: the three tests before it stay compares.
        _, ir, _, _ = emit('fn f(op:i64) -> i64 = if op == 0 then 1 else if op == 1 then 2 else if op == 2 then 3 else let q = op in ' + chain(6, 'q') + '\nfn main() -> i64 = f(3)')
        self.assertEqual(body(ir, 'f').count('icmp eq'), 3)
        self.assertEqual(len(re.findall(r'i64 \d+, label %case', body(ir, 'f'))), 6)
        _, ir, _, _ = emit('fn f(op:i64) -> i64 = ' + chain(40) + '\nfn main() -> i64 = f(3)', switches=False)
        self.assertNotIn('switch', body(ir, 'f'))

    def test_chain_switches_on_the_first_scalar_only(self):
        _, ir, _, _ = emit('fn f(op:i64,x:i64) -> i64 = if op == 0 then 1 else if op == 1 then 2 else if op == 2 then 3 else if op == 3 then 4 '
                           'else if x == 0 then 5 else if x == 1 then 6 else 7\nfn main() -> i64 = f(3,1)')
        f = body(ir, 'f')
        self.assertEqual(f.count('switch i64'), 1)
        self.assertEqual(len(re.findall(r'i64 \d+, label %case', f)), 4)


class DeepChains(unittest.TestCase):
    def test_unrelated_disequalities_no_longer_exhaust_the_prover(self):
        op, sp, n = Lin.var('op'), Lin.var('sp'), Lin.var('n')
        facts = and_(*[neg(cmp('==', op, Lin.num(k))) for k in range(30)], cmp('>=', sp, Lin.num(0)), cmp('<', sp + Lin.num(2), n))
        self.assertEqual(entails(facts, and_(cmp('<=', Lin.num(0), sp + Lin.num(2)), cmp('<', sp + Lin.num(2), n)))[0], 'proven')
        # Never a false goal: sp + 3 may equal n, and op facts cannot help.
        self.assertNotEqual(entails(facts, cmp('<', sp + Lin.num(3), n))[0], 'proven')
        # Connected facts are kept: op is tied to sp.
        tied = and_(facts, cmp('==', op, sp))
        self.assertNotEqual(entails(tied, cmp('<', sp + Lin.num(3), n))[0], 'proven')

    def test_handler_bounds_prove_in_late_arms(self):
        arms = ' else '.join(f'if op == {k} then (if sp + 2 < n then st[sp + 2] else 0)' for k in range(40))
        _, _, _, checker = emit('fn f(st:Arr i64 n,sp:i64{sp >= 0},op:i64) -> i64 = ' + arms + ' else 0\nfn main() -> i64 = f(arr(i in 0..4) i,0,39)')
        bounds = [o['status'] for o in checker.obligations if o['kind'] == 'bounds']
        self.assertEqual(len(bounds), 40)
        self.assertEqual(set(bounds), {'proven'})


if __name__ == '__main__':
    unittest.main()
