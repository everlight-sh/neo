"""Soundness boundaries for whole-program interval propagation."""
import unittest

from neoc import syntax as S, ranges as R
from neoc.check import Checker
from neoc.graph import hash_program


def analyze(source):
    p = S.parse(source); hash_program(p)
    Checker(p).run()
    analysis = R.Analysis(p.fns); nodes = analysis.run()
    return p, analysis, nodes


class RangeTests(unittest.TestCase):
    def test_modulo_bounds_are_signed(self):
        self.assertEqual(R.binary('%', R.TOP, (17, 17)), (-16, 16))
        self.assertEqual(R.binary('%', (0, R.MAX), (17, 17)), (0, 16))
        self.assertEqual(R.binary('%', (R.MIN, -1), (17, 17)), (-16, 0))

    def test_wrap_discards_arithmetic_bounds(self):
        self.assertEqual(R.binary('+', (R.MAX, R.MAX), (1, 1)), R.TOP)
        self.assertEqual(R.binary('-', (R.MIN, R.MIN), (1, 1)), R.TOP)
        self.assertEqual(R.binary('*', (R.MAX, R.MAX), (2, 2)), R.TOP)

    def test_all_call_sites_join_before_optimization(self):
        _, a, _ = analyze('fn reduce(x : i64) -> i64 = x % 17 fn main(x : i64) -> i64 = reduce(x % 17) + reduce(x)')
        self.assertEqual(a.inputs['reduce'], [R.TOP])

    def test_array_elements_flow_through_a_loop(self):
        _, a, _ = analyze('fn step(a : Arr i64 n) -> Arr i64 n = arr(i in 0..n) (a[i] * 2) % 17 fn main(n : i64{n > 0}) -> i64 = let a = loop(a = arr(i in 0..n) i % 17, k = 0) while k < 8 next(step(a), k + 1) yield a in a[0]')
        self.assertEqual(a.inputs['step'], [(0, 16)])
        self.assertEqual(a.outputs['step'], (0, 16))

    def test_loop_widens_growing_values(self):
        _, a, _ = analyze('fn reduce(x : i64) -> i64 = x % 17 fn main(n : i64) -> i64 = loop(x = 1, i = 0) while i < n next(x * 2, i + 1) yield reduce(x)')
        self.assertEqual(a.inputs['reduce'], [R.TOP])

    def test_effect_call_boundary_is_unknown(self):
        _, a, _ = analyze('fn reduce(x : i64) -> i64 = x % 17 effect fn main(x : i64) -> i64 = reduce(x % 17)')
        self.assertEqual(a.inputs['reduce'], [R.TOP])

    def test_exported_function_is_unknown(self):
        _, a, _ = analyze('export fn reduce(x : i64) -> i64 = x % 17 fn main(x : i64) -> i64 = reduce(x % 17)')
        self.assertEqual(a.inputs['reduce'], [R.TOP])

    def test_address_taken_function_is_unknown(self):
        _, a, _ = analyze('fn reduce(x : i64) -> i64 = x % 17 effect fn main() -> i64 = let p = addr(reduce) in 0')
        self.assertEqual(a.inputs['reduce'], [R.TOP])

    def test_array_update_joins_element_ranges(self):
        _, a, _ = analyze('fn read(a : Arr i64 n{n > 0}) -> i64 = a[0] fn main(x : i64) -> i64 = let a = arr(i in 0..2) i % 17 in read(set(a, 0, x))')
        self.assertEqual(a.inputs['read'], [R.TOP])

    def test_guard_refines_both_sides_of_a_disjunction(self):
        _, a, _ = analyze('fn calculate(n : i64) -> i64 = n * 123 fn main(n : i64) -> i64 = if n < 1 || n > 1000000 then 0 else calculate(n)')
        self.assertEqual(a.inputs['calculate'], [(1, 1000000)])

    def test_refinement_does_not_cross_a_branch_join(self):
        _, a, _ = analyze('fn calculate(n : i64) -> i64 = n % 17 fn main(n : i64) -> i64 = let x = if n < 1 || n > 1000000 then n else 1 in calculate(x)')
        self.assertEqual(a.inputs['calculate'], [R.TOP])


if __name__ == '__main__': unittest.main()
