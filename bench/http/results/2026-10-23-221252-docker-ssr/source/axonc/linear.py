"""Linear integer arithmetic: facts, obligations, Fourier-Motzkin proofs.

Everything is normalised to constraints of the form  lin <= 0  over integer
variables. Strict inequalities are tightened (a < b  ==>  a - b + 1 <= 0),
which makes rational Fourier-Motzkin *sound* for proving integer goals
(it may fail to prove some true goals; then the agent must add a `check`).
"""
from __future__ import annotations
from fractions import Fraction
from itertools import product
from typing import Dict, List, Optional, Tuple

class Lin:
    """Linear expression: sum(coef * var) + const, exact rationals."""
    __slots__ = ("terms", "const")
    def __init__(self, terms: Optional[Dict[str, Fraction]] = None, const=0):
        self.terms = {k: v for k, v in (terms or {}).items() if v != 0}
        self.const = Fraction(const)
    @staticmethod
    def var(name: str) -> "Lin": return Lin({name: Fraction(1)})
    @staticmethod
    def num(c) -> "Lin": return Lin({}, c)
    def __add__(self, o: "Lin") -> "Lin":
        t = dict(self.terms)
        for k, v in o.terms.items(): t[k] = t.get(k, Fraction(0)) + v
        return Lin(t, self.const + o.const)
    def __sub__(self, o: "Lin") -> "Lin": return self + o.scale(-1)
    def scale(self, k) -> "Lin":
        k = Fraction(k)
        return Lin({a: b * k for a, b in self.terms.items()}, self.const * k)
    def is_const(self) -> bool: return not self.terms
    def vars(self): return set(self.terms)
    def __eq__(self, o): return isinstance(o, Lin) and self.terms == o.terms and self.const == o.const
    def __hash__(self): return hash((tuple(sorted(self.terms.items())), self.const))
    def __str__(self):
        parts = []
        for k in sorted(self.terms):
            c = self.terms[k]
            if c == 1: parts.append(k)
            elif c == -1: parts.append(f"-{k}")
            else: parts.append(f"{c}*{k}")
        if self.const != 0 or not parts: parts.append(str(self.const))
        return " + ".join(parts).replace("+ -", "- ")

# A formula is a tree: ("atom", Lin) meaning lin <= 0, ("and", [..]), ("or", [..]), ("true",), ("false",)
Formula = tuple

def atom(l: Lin) -> Formula: return ("atom", l)
UNK = ("unk",)      # a boolean we know nothing about (floats, calls): carries no facts either way

def and_(*fs) -> Formula:
    fs = [f for f in fs if f != ("true",) and f != UNK]
    if any(f == ("false",) for f in fs): return ("false",)
    return ("true",) if not fs else (fs[0] if len(fs) == 1 else ("and", list(fs)))
def or_(*fs) -> Formula:
    if any(f == UNK for f in fs): return UNK
    fs = [f for f in fs if f != ("false",)]
    if any(f == ("true",) for f in fs): return ("true",)
    return ("false",) if not fs else (fs[0] if len(fs) == 1 else ("or", list(fs)))

def cmp(op: str, a: Lin, b: Lin) -> Formula:
    """Formula for `a op b` over integers, as lin<=0 atoms."""
    if op == "<":  return atom(a - b + Lin.num(1))
    if op == "<=": return atom(a - b)
    if op == ">":  return atom(b - a + Lin.num(1))
    if op == ">=": return atom(b - a)
    if op == "==": return and_(atom(a - b), atom(b - a))
    if op == "!=": return or_(cmp("<", a, b), cmp(">", a, b))
    raise ValueError(op)

def neg(f: Formula) -> Formula:
    k = f[0]
    if k == "true": return ("false",)
    if k == "false": return ("true",)
    if k == "unk": return UNK
    if k == "and": return or_(*[neg(x) for x in f[1]])
    if k == "or": return and_(*[neg(x) for x in f[1]])
    # not (l <= 0)  ==  l > 0  ==  -l + 1 <= 0   (integers)
    return atom(f[1].scale(-1) + Lin.num(1))

def formula_str(f: Formula) -> str:
    k = f[0]
    if k == "true": return "true"
    if k == "false": return "false"
    if k == "unk": return "?"
    if k == "atom": return f"{f[1]} <= 0"
    j = " && " if k == "and" else " || "
    return "(" + j.join(formula_str(x) for x in f[1]) + ")"

MAX_DNF = 256

def dnf(f: Formula) -> List[List[Lin]]:
    """List of conjunctions (each a list of lin<=0)."""
    k = f[0]
    if k == "true" or k == "unk": return [[]]
    if k == "false": return []
    if k == "atom": return [[f[1]]]
    if k == "or":
        out = []
        for x in f[1]: out.extend(dnf(x))
        return out[:MAX_DNF]
    # and: cartesian product
    acc = [[]]
    for x in f[1]:
        d = dnf(x)
        acc = [a + b for a in acc for b in d]
        if len(acc) > MAX_DNF: acc = acc[:MAX_DNF]
    return acc

# ------------------------------------------------------------ Fourier-Motzkin
FM_LIMIT = 4000

def fm_unsat(cons: List[Lin]) -> Optional[bool]:
    """True if the conjunction of lin<=0 is unsatisfiable over the rationals
    (hence over the integers). False if satisfiable over rationals. None if
    the search blew up."""
    cons = list(cons)
    while True:
        # constant contradictions / drop trivial
        keep = []
        for c in cons:
            if c.is_const():
                if c.const > 0: return True
            else:
                keep.append(c)
        cons = keep
        if not cons: return False
        # pick the variable with the fewest pos*neg combinations
        vs = set()
        for c in cons: vs |= c.vars()
        best, best_cost = None, None
        for v in vs:
            p = sum(1 for c in cons if c.terms.get(v, 0) > 0)
            n = sum(1 for c in cons if c.terms.get(v, 0) < 0)
            cost = p * n - p - n
            if best_cost is None or cost < best_cost: best, best_cost = v, cost
        v = best
        pos = [c for c in cons if c.terms.get(v, 0) > 0]
        negs = [c for c in cons if c.terms.get(v, 0) < 0]
        rest = [c for c in cons if v not in c.terms]
        new = rest
        for p in pos:
            for q in negs:
                # p: a*v + P <= 0 (a>0)  ;  q: -b*v + Q <= 0 (b>0)
                a, b = p.terms[v], -q.terms[v]
                comb = p.scale(b) + q.scale(a)     # eliminates v
                new.append(comb)
        if len(new) > FM_LIMIT: return None
        cons = new

def implies(facts_dnf: List[List[Lin]], goal: Lin) -> Optional[bool]:
    """Do the facts (DNF) imply goal <= 0?  For every disjunct D:
    D ∧ ¬goal must be unsat.  Returns None when FM gives up."""
    if not facts_dnf:          # facts are contradictory: anything follows
        return True
    not_goal = goal.scale(-1) + Lin.num(1)
    for D in facts_dnf:
        r = fm_unsat(D + [not_goal])
        if r is None: return None
        if r is False: return False
    return True

# ------------------------------------------------------------ counterexamples
def counterexample(facts_dnf: List[List[Lin]], goal: Lin, limit_vars=7) -> Optional[Dict[str, int]]:
    """Small brute-force model of  facts ∧ ¬goal  for diagnostics."""
    vs = set(goal.vars())
    for D in facts_dnf:
        for c in D: vs |= c.vars()
    vs = sorted(vs)
    if len(vs) > limit_vars: return None
    not_goal = goal.scale(-1) + Lin.num(1)
    def sat(cons, env):
        for c in cons:
            val = c.const + sum(k * env[v] for v, k in c.terms.items())
            if val > 0: return False
        return True
    domain = [0, 1, -1, 2, 3, 4, 5, 8, -2, 10, 100]
    for vals in product(domain, repeat=len(vs)):
        env = dict(zip(vs, vals))
        if not sat([not_goal], env): continue
        for D in facts_dnf:
            if sat(D, env):
                return {k: int(v) for k, v in env.items()}
    return None


def entails(facts: Formula, goal: Formula):
    """facts ⇒ goal ?  Returns (status, counterexample) with status in
    proven / unproven / unknown."""
    d = dnf(and_(facts, neg(goal)))
    for D in d:
        r = fm_unsat(D)
        if r is None: return "unknown", None
        if r is False: return "unproven", model(D)
    return "proven", None

def model(cons: List[Lin], limit_vars=7) -> Optional[Dict[str, int]]:
    """Small brute-force integer model of a conjunction, for diagnostics."""
    vs = set()
    for c in cons: vs |= c.vars()
    vs = sorted(vs)
    if len(vs) > limit_vars: return None
    domain = [0, 1, -1, 2, 3, 4, 5, 8, -2, 10, 100]
    for vals in product(domain, repeat=len(vs)):
        env = dict(zip(vs, vals))
        ok = True
        for c in cons:
            if c.const + sum(k * env[v] for v, k in c.terms.items()) > 0: ok = False; break
        if ok: return {k: int(v) for k, v in env.items()}
    return None
