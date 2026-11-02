"""Masks and repeated field reads prove without `check`; unsound variants do not."""
import unittest
from neoc import syntax as S
from neoc.check import Checker
from neoc.graph import hash_program


def statuses(source):
    program = S.parse(source); hash_program(program); checker = Checker(program); checker.run()
    return [(o['kind'], o['status']) for o in checker.obligations if o['kind'] in ('bounds', 'precondition')]


def proven(source): return all(status == 'proven' for _, status in statuses(source))


R = 'type R = { pos : i64, size : i64, inner : Q } type Q = { at : i64 }\n'
MAIN = '\nfn main() -> i64 = 0'


class Masks(unittest.TestCase):
    def test_constant_mask_bounds_an_index(self):
        self.assertTrue(proven('fn get(xs:Arr i64 n,h:i64{n >= 16}) -> i64 = xs[bit_and(h,15)]' + MAIN))
        self.assertTrue(proven('fn get(xs:Arr i64 n,h:i64{n >= 64}) -> i64 = xs[bit_and(63,h)]' + MAIN))
        # Both operands constant-free on one side: the smaller mask bounds it.
        self.assertTrue(proven('fn get(xs:Arr i64 n,h:i64{n >= 8}) -> i64 = xs[bit_and(bit_and(h,255),7)]' + MAIN))
        self.assertTrue(proven('fn get(xs:Arr u8 n,h:i64) -> i64 = if n > 255 then i64(xs[bit_and(shift_right(h,8),255)]) else 0' + MAIN))

    def test_masks_that_do_not_bound_stay_unproven(self):
        for body in ['xs[bit_and(h,16)]',          # 16 is not below len 16
                     'xs[bit_and(h,-1)]',          # a negative mask keeps the sign bit
                     'xs[bit_and(h,m)]',           # unknown mask
                     'xs[bit_or(h,15)]',
                     'xs[bit_xor(h,15)]',
                     'xs[bit_and(h,15) + 1]']:     # 16 is out of range
            with self.subTest(body=body):
                self.assertFalse(proven('fn get(xs:Arr i64 n,h:i64,m:i64{n == 16}) -> i64 = ' + body + MAIN))


class FieldReads(unittest.TestCase):
    def test_a_guard_on_one_read_proves_another(self):
        self.assertTrue(proven(R + 'fn get(r:R,xs:Arr i64 n) -> i64 = if r.pos >= 0 && r.pos < n then xs[r.pos] else 0' + MAIN))
        self.assertTrue(proven(R + 'fn get(r:R,xs:Arr i64 n) -> i64 = if r.inner.at >= 0 && r.inner.at < n then xs[r.inner.at] else 0' + MAIN))
        # A let-bound record and a loop-state record are single immutable values too.
        self.assertTrue(proven(R + 'fn get(xs:Arr i64 n,k:i64) -> i64 = let r = R { pos = k, size = 0, inner = Q { at = 0 } } in if r.pos >= 0 && r.pos < n then xs[r.pos] else 0' + MAIN))
        self.assertTrue(proven(R + '''fn walk(xs:Arr i64 n) -> i64
  = loop(r = R { pos = 0, size = 0, inner = Q { at = 0 } }, t = 0) while r.pos >= 0 && r.pos < n
      next(r with { pos = r.pos + 1 }, t + xs[r.pos]) yield t''' + MAIN))

    def test_different_values_are_not_equated(self):
        for body in ['if r.pos >= 0 && r.pos < n then xs[s.pos] else 0',               # another binding
                     'if r.pos >= 0 && r.pos < n then xs[r.size] else 0',               # another field
                     'if r.pos >= 0 && r.pos < n then let r = s in xs[r.pos] else 0',  # shadowed
                     'if r.pos >= 0 && r.pos < n then let t = r with { pos = n } in xs[t.pos] else 0',
                     'if r.inner.at >= 0 && r.inner.at < n then xs[s.inner.at] else 0',
                     'if r.pos >= 0 && r.pos < n then xs[r.pos + 1] else 0']:
            with self.subTest(body=body):
                self.assertFalse(proven(R + 'fn get(r:R,s:R,xs:Arr i64 n) -> i64 = ' + body + MAIN))

    def test_loop_states_are_not_equated_across_iterations(self):
        # The guard holds for the old state; the index reads the successor.
        self.assertFalse(proven(R + '''fn walk(xs:Arr i64 n) -> i64
  = loop(r = R { pos = 0, size = 0, inner = Q { at = 0 } }, t = 0) while r.pos >= 0 && r.pos < n
      next(r with { pos = r.pos + 1 }, let q = r with { pos = r.pos + 1 } in t + xs[q.pos]) yield t''' + MAIN))


if __name__ == '__main__':
    unittest.main()
