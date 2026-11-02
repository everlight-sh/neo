import unittest
from fractions import Fraction
from itertools import combinations
import random
from neoc.linear import Lin, cmp, or_, and_, entails, fm_unsat

class ProverTests(unittest.TestCase):
    def test_branch_limit_never_silently_proves_a_false_goal(self):
        x=Lin.var('x')
        facts=or_(*[cmp('==',x,Lin.num(i)) for i in range(300)])
        self.assertNotEqual(entails(facts,cmp('<',x,Lin.num(299)))[0],'proven')
    def test_normalization_preserves_contradictions(self):
        x=Lin.var('x')
        self.assertTrue(fm_unsat([x.scale(2)-Lin.num(2),x.scale(-3)+Lin.num(6)]))
        self.assertFalse(fm_unsat([x-Lin.num(2),x.scale(-1)+Lin.num(1)]))
    def test_constant_goals_do_not_exhaust_a_branch_budget(self):
        x=Lin.var('x');facts=or_(*[cmp('==',x,Lin.num(i)) for i in range(300)])
        self.assertEqual(entails(facts,cmp('!=',Lin.num(-1),Lin.num(0)))[0],'proven')

    def test_rational_halfspaces_against_independent_vertex_oracle(self):
        # A bounded 2D rational polytope is feasible iff one of its vertices
        # satisfies every halfspace. No elimination algorithm is used here.
        rng = random.Random(261026)
        for _ in range(300):
            constraints = [(Fraction(1), Fraction(0), Fraction(-3)),
                           (Fraction(-1), Fraction(0), Fraction(-3)),
                           (Fraction(0), Fraction(1), Fraction(-3)),
                           (Fraction(0), Fraction(-1), Fraction(-3))]
            constraints += [tuple(Fraction(rng.randint(-5, 5), rng.randint(1, 5)) for _ in range(3)) for _ in range(5)]
            feasible = False
            for (a,b,c),(d,e,f) in combinations(constraints, 2):
                determinant = a*e-b*d
                if not determinant: continue
                x,y = (b*f-c*e)/determinant, (c*d-a*f)/determinant
                if all(p*x+q*y+r <= 0 for p,q,r in constraints):
                    feasible = True; break
            actual = fm_unsat([Lin({'x':a,'y':b},c) for a,b,c in constraints])
            self.assertEqual(actual, not feasible, constraints)

    def test_arbitrary_precision_scaling_preserves_sign_and_tight_bounds(self):
        x = Lin.var('x'); magnitude = 1 << 180
        self.assertTrue(fm_unsat([(x-Lin.num(1)).scale(Fraction(1,magnitude)),
                                  (Lin.num(2)-x).scale(magnitude)]))
        self.assertFalse(fm_unsat([(x-Lin.num(1)).scale(Fraction(1,magnitude)),
                                   (Lin.num(1)-x).scale(magnitude)]))

if __name__=='__main__':unittest.main()
