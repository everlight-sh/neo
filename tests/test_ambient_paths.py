"""Facts from a call's return refinement hold only where the call ran.

A callee's postcondition can constrain its arguments (result > x and result < 5
imply x < 4). Such a fact must never prove a goal on a path where the call was
not evaluated: another branch, the far side of a short-circuit, or after a loop
or comprehension that may run zero times. Conditions the prover cannot express
(a bool variable) never match one another.
"""
import unittest
from neoc import syntax as S
from neoc.check import Checker
from neoc.graph import hash_program


def statuses(source, fn):
    program = S.parse(source); hash_program(program); checker = Checker(program); checker.run()
    assert not getattr(checker, 'errors', []), checker.errors
    found = [o['status'] for o in checker.obligations if o['fn'].endswith(fn) and o['kind'] in ('bounds', 'postcondition', 'precondition')]
    assert found, 'no obligations to judge'
    return found


def proven(source, fn='g'): return all(status == 'proven' for status in statuses(source, fn))
def rejected(source, fn='g'): return any(status == 'unproven' for status in statuses(source, fn))


# f returns only when x < 4 (the check traps otherwise), so its result facts imply x < 4.
F = 'fn f(x : i64) -> i64 {result > x, result < 5} = check x < 4 in x + 1\n'
R = 'type R = { pos : i64 }\n'
MAIN = '\nfn main() -> i64 = 0'


class Unsound(unittest.TestCase):
    def test_a_branch_fact_does_not_prove_the_other_branch(self):
        self.assertTrue(rejected(F + 'fn g(xs:Arr i64 n,x:i64{x >= 0,n >= 4}) -> i64 = if x < 4 then f(x) else xs[x]' + MAIN))

    def test_the_original_report(self):
        self.assertTrue(rejected('fn f(x : i64{x < 4}) -> i64 {result > x, result < 5} = x + 1\n'
                                'fn g(xs : Arr i64 n, x : i64) -> i64 = if x < 4 then f(x) else xs[x]' + MAIN))

    def test_field_reads_do_not_carry_branch_facts(self):
        self.assertTrue(rejected(F + R + 'fn g(xs:Arr i64 n,r:R{n >= 4}) -> i64 = if r.pos >= 0 && r.pos < 4 then f(r.pos) else xs[r.pos]' + MAIN))

    def test_a_short_circuit_operand_does_not_prove_the_else_branch(self):
        self.assertTrue(rejected(F + 'fn g(xs:Arr i64 n,x:i64,m:i64{x >= 0,n >= 4}) -> i64 = if m > 0 && f(x) > 0 then 0 else xs[x]' + MAIN))

    def test_a_loop_body_does_not_prove_code_after_the_loop(self):
        self.assertTrue(rejected(F + 'fn g(xs:Arr i64 n,x:i64,m:i64{x >= 0,n >= 4}) -> i64 = '
                                'let s = loop(i = 0,t = 0) while i < m next(i + 1,f(x)) yield t in xs[x]' + MAIN))

    def test_a_comprehension_body_does_not_prove_code_after_it(self):
        self.assertTrue(rejected(F + 'fn g(xs:Arr i64 n,x:i64,m:i64{x >= 0,n >= 4,m >= 0}) -> i64 = '
                                'let a = arr(i in 0..m) f(x) in xs[x]' + MAIN))

    def test_unknown_conditions_never_match(self):
        # A bool variable is not a linear fact; then and else must still stay apart,
        # and a later test of the same variable does not reuse the earlier branch.
        self.assertTrue(rejected(F + 'fn g(xs:Arr i64 n,x:i64,c:bool{x >= 0,n >= 4}) -> i64 = if c then f(x) else xs[x]' + MAIN))
        self.assertTrue(rejected(F + 'fn g(xs:Arr i64 n,x:i64,c:bool{x >= 0,n >= 4}) -> i64 = '
                                'let y = (if c then f(x) else 0) in if c then xs[x] else y' + MAIN))


class StillProven(unittest.TestCase):
    def test_a_fact_proves_code_the_call_dominates(self):
        self.assertTrue(proven(F + 'fn g(xs:Arr i64 n,x:i64{x >= 0,n >= 4}) -> i64 = let y = f(x) in xs[x] + y' + MAIN))

    def test_a_fact_holds_wherever_its_condition_holds_again(self):
        self.assertTrue(proven(F + 'fn g(xs:Arr i64 n,x:i64,m:i64{x >= 0,n >= 4}) -> i64 = '
                               'let y = (if m > 0 then f(x) else 0) in if m > 0 then xs[x] else y' + MAIN))

    def test_a_short_circuit_operand_proves_the_guarded_code(self):
        self.assertTrue(proven(F + 'fn g(xs:Arr i64 n,x:i64{n >= 4}) -> i64 = check x >= 0 && f(x) < 5 in xs[x]' + MAIN))

    def test_branch_facts_reach_the_if_result(self):
        source = ('fn g(c:i64,n:i64) -> i64 {result >= 1, result <= 256} = '
                  'if c >= 1 && c <= 256 then c else let b = if n < 1 then 1 else if n > 256 then 256 else n in b' + MAIN)
        self.assertTrue(proven(source))

    def test_lengths_and_refinements_are_not_path_conditions(self):
        source = ('fn g(n:i64{n >= 2}) -> i64 {result >= 0} = '
                  'let marks = arr(k in 0..n + 1) k >= 2 in sum(k in 0..n + 1) if marks[k] then 1 else 0' + MAIN)
        self.assertTrue(proven(source))


if __name__ == '__main__':
    unittest.main()
