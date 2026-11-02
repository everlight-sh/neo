"""Calls in loops that miss the forced-inlining budget are reported; `inline fn` forces it."""
import unittest
from neoc import syntax as S
from neoc.check import Checker
from neoc.graph import hash_program
from neoc.llvm import LLVMGen

BIG = ' '.join(f'let v{i} = bit_xor(wrapping_mul(v{i - 1}, {2 * i + 1}), shift_right(v{i - 1}, {i % 13 + 1})) in' for i in range(1, 30))
HELPER = 'fn mix(v0:i64) -> i64 = ' + BIG + ' v29\n'
SMALL = 'fn small(x:i64) -> i64 = bit_xor(x, 5)\n'
LOOPS = 'fn main() -> i64 = loop(i = 0, t = 0) while i < 10 next(i + 1, wrapping_add(t, wrapping_add(mix(i), small(i)))) yield t + mix(7) + sum(k in 0..4) mix(k)'


def generate(source, budget=160):
    program = S.parse(source); hashes = hash_program(program); Checker(program).run()
    gen = LLVMGen(program.fns, hashes, 'x86_64-unknown-linux-gnu', inline_budget=budget)
    return gen, gen.program()


def define(ir, name):
    return next(line for line in ir.splitlines() if line.startswith('define') and '@ax_' + name + '__' in line)


class InlineBudget(unittest.TestCase):
    def test_loop_call_sites_over_the_budget_are_listed(self):
        gen, ir = generate(HELPER + SMALL + LOOPS)
        misses = gen.inline_budget_misses
        self.assertEqual({(m['callee'], m['in']) for m in misses}, {('mix', 'loop'), ('mix', 'sum')})
        self.assertTrue(all(m['fn'] == 'main' and m['callee_nodes'] > 160 and m['inline_budget'] == 160 for m in misses))
        self.assertNotIn('alwaysinline', define(ir, 'mix'))
        self.assertIn('alwaysinline', define(ir, 'small'))
        # A call outside every loop is not a hot-loop cliff; a larger budget removes them all.
        self.assertEqual(len(misses), 2)
        self.assertEqual(generate(HELPER + SMALL + LOOPS, budget=1000)[0].inline_budget_misses, [])

    def test_inline_modifier_forces_inlining(self):
        gen, ir = generate('inline ' + HELPER + SMALL + LOOPS)
        self.assertEqual(gen.inline_budget_misses, [])
        self.assertIn('mix', gen.forced_inline)
        self.assertIn('alwaysinline', define(ir, 'mix'))
        # Effect helpers may be forced too; recursion is reported and ignored.
        gen, ir = generate('inline effect fn bump(x:i64) -> i64 = x + 1\ninline fn down(n:i64) -> i64 = if n <= 0 then 0 else down(n - 1)\n'
                           'effect fn main() -> i64 = bump(down(3))')
        self.assertIn('alwaysinline', define(ir, 'bump'))
        self.assertNotIn('alwaysinline', define(ir, 'down'))
        self.assertEqual([i['reason'] for i in gen.inline_ignored], ['recursive'])

    def test_modifier_is_contextual(self):
        program = S.parse('fn f(inline:i64) -> i64 = let cold = inline in cold + 1\nfn main() -> i64 = f(1)')
        self.assertEqual(program.fns[0].params[0].name, 'inline')
        self.assertTrue(S.parse('private inline fn g() -> i64 = 1').fns[0].inline)
        with self.assertRaises(S.SyntaxError_):
            S.parse('cold inline fn g() -> i64 = 1')


if __name__ == '__main__':
    unittest.main()
