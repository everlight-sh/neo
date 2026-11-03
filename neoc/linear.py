"""Linear integer arithmetic: facts, obligations, Fourier-Motzkin proofs.

Everything is normalised to constraints of the form  lin <= 0  over integer
variables. Strict inequalities are tightened (a < b  ==>  a - b + 1 <= 0),
which makes rational Fourier-Motzkin *sound* for proving integer goals
(it may fail to prove some true goals; then the agent must add a `check`).
"""
from __future__ import annotations
from fractions import Fraction
from functools import wraps
from itertools import product, islice
from math import gcd, lcm
from time import perf_counter
from typing import Dict, List, Optional, Tuple

def exact_number(value):
    if isinstance(value, int): return value
    value = Fraction(value)
    return value.numerator if value.denominator == 1 else value


class Lin:
    """Linear expression: sum(coef * var) + const, exact rationals."""
    __slots__ = ("terms", "const", "integer")
    def __init__(self, terms: Optional[Dict[str, Fraction]] = None, const=0):
        self.terms = {k: exact_number(v) for k, v in (terms or {}).items() if v != 0}
        self.const = exact_number(const)
        self.integer = None  # integer_constraint's answer, once asked
    @staticmethod
    def var(name: str) -> "Lin": return Lin({name: 1})
    @staticmethod
    def num(c) -> "Lin": return Lin({}, c)
    def __add__(self, o: "Lin") -> "Lin":
        t = dict(self.terms)
        for k, v in o.terms.items(): t[k] = t.get(k, 0) + v
        return Lin(t, self.const + o.const)
    def __sub__(self, o: "Lin") -> "Lin": return self + o.scale(-1)
    def scale(self, k) -> "Lin":
        k = exact_number(k)
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

def atom(l: Lin) -> Formula:
    if l.is_const():return ('true',) if l.const<=0 else ('false',)
    return ("atom", l)
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
MODEL_BUDGET = 10000

class ProofLimit(Exception): pass

def dnf(f: Formula) -> List[List[Lin]]:
    """List of conjunctions (each a list of lin<=0)."""
    k = f[0]
    if k == "true" or k == "unk": return [[]]
    if k == "false": return []
    if k == "atom": return [[f[1]]]
    if k == "or":
        out = []
        for x in f[1]:
            out.extend(dnf(x))
            if len(out)>MAX_DNF: raise ProofLimit('DNF branch limit')
        return out
    # and: cartesian product
    acc = [[]]
    for x in f[1]:
        d = dnf(x)
        if len(acc)*len(d)>MAX_DNF: raise ProofLimit('DNF product limit')
        acc = [a + b for a in acc for b in d]
    return acc

# ------------------------------------------------------------ Fourier-Motzkin
FM_LIMIT = 4000

def integer_constraint(c: Lin):
    """Clear rational denominators by positive scaling, without rounding.

    Fourier-Motzkin needs exact arithmetic, but not Fraction allocations at
    every elimination. A primitive integer tuple represents the very same
    rational half-space (including its sign).
    """
    denominator = lcm(c.const.denominator, *(v.denominator if isinstance(v, Fraction) else 1 for v in c.terms.values()))
    terms = {name: int(value * denominator) for name, value in c.terms.items()}
    return primitive_constraint(terms, int(c.const * denominator))


def primitive_constraint(terms, constant):
    terms = {name: value for name, value in terms.items() if value}
    divisor = gcd(abs(constant), *terms.values())
    if divisor > 1:
        terms = {name: value // divisor for name, value in terms.items()}
        constant //= divisor
    return terms, constant


# Answers by constraint set: FM's answer, its limit included, does not depend
# on the order of the constraints or on duplicates among them.
DECIDED: Dict[frozenset, Optional[bool]] = {}

def keyed(terms, constant):
    return terms, constant, (frozenset(terms.items()), constant)

def fm_unsat(cons: List[Lin]) -> Optional[bool]:
    """True if the conjunction of lin<=0 is unsatisfiable over the rationals
    (hence over the integers). False if satisfiable over rationals. None if
    the search blew up."""
    for c in cons:
        if c.integer is None: c.integer = keyed(*integer_constraint(c))
    cons = [c.integer for c in cons]
    query = frozenset(c[2] for c in cons)
    if query in DECIDED: return DECIDED[query]
    if len(DECIDED) > 1 << 16: DECIDED.clear()
    answer = DECIDED[query] = eliminate(cons)
    return answer

def eliminate(cons) -> Optional[bool]:
    """Fourier-Motzkin over (terms, constant, key) integer constraints."""
    while True:
        # constant contradictions / drop trivial
        keep = []; seen = set()
        counts = {}
        for c in cons:
            terms = c[0]
            if not terms:
                if c[1] > 0: return True
            else:
                if c[2] in seen: continue
                seen.add(c[2]); keep.append(c)
                for variable, coefficient in terms.items():
                    count = counts.get(variable)
                    if count is None: count = counts[variable] = [0, 0]
                    count[coefficient < 0] += 1
        cons = keep
        if not cons: return False
        # pick the variable with the fewest pos*neg combinations
        v = min(counts, key=lambda name: (counts[name][0] * counts[name][1] - sum(counts[name]), name))
        pos = []; negs = []; new = []
        for c in cons:
            coefficient = c[0].get(v, 0)
            if coefficient > 0: pos.append(c)
            elif coefficient < 0: negs.append(c)
            else: new.append(c)
        others = [({name: value for name, value in q[0].items() if name != v}, -q[0][v], q[1]) for q in negs]
        for p in pos:
            # p: a*v + P <= 0 (a>0)  ;  q: -b*v + Q <= 0 (b>0)
            a = p[0][v]
            scaled = [(name, value) for name, value in p[0].items() if name != v]
            for q_terms, b, q_constant in others:
                terms = {name: value * b for name, value in scaled}
                for name, value in q_terms.items(): terms[name] = terms.get(name, 0) + value * a
                terms, constant = primitive_constraint(terms, p[1] * b + q_constant * a)
                new.append((terms, constant, (frozenset(terms.items()), constant)))
                if len(new)>FM_LIMIT:return None
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
    for vals in islice(product(domain, repeat=len(vs)), MODEL_BUDGET):
        env = dict(zip(vs, vals))
        if not sat([not_goal], env): continue
        for D in facts_dnf:
            if sat(D, env):
                return {k: int(v) for k, v in env.items()}
    return None


def conjuncts(f: Formula, out: list) -> list:
    if f[0] == "and":
        for x in f[1]: conjuncts(x, out)
    elif f[0] != "true": out.append(f)
    return out

def formula_vars(f: Formula) -> set:
    if f[0] == "atom": return f[1].vars()
    if f[0] in ("and", "or"): return set().union(*[formula_vars(x) for x in f[1]])
    return set()

def relevant(facts: Formula, goal: Formula) -> Formula:
    """The conjuncts of facts connected to the goal's variables through shared variables."""
    parts = conjuncts(facts, [])
    names = [formula_vars(p) for p in parts]
    keep = [not n for n in names]          # variable-free conjuncts (false) always stay
    want = set(formula_vars(goal)); changed = True
    while changed:
        changed = False
        for i, n in enumerate(names):
            if not keep[i] and n & want: keep[i] = True; want |= n; changed = True
    return and_(*[p for p, k in zip(parts, keep) if k])

# Seconds spent deciding entailments in this process, for build reports.
SPENT = [0.0]

def timed(decide):
    @wraps(decide)
    def run(*args, **kwargs):
        started = perf_counter()
        try: return decide(*args, **kwargs)
        finally: SPENT[0] += perf_counter() - started
    return run

@timed
def entails(facts: Formula, goal: Formula, diagnostics=True):
    """facts ⇒ goal ?  Returns (status, counterexample) with status in
    proven / unproven / unknown."""
    # Loop guards/refinements often already contain the exact obligation.
    # Only atoms guaranteed on every branch may justify this shortcut.
    def guaranteed(formula):
        kind=formula[0]
        if kind=='atom':return {formula[1]}
        if kind=='and':return set().union(*(guaranteed(child) for child in formula[1]))
        if kind=='or':
            children=[guaranteed(child) for child in formula[1]]
            return set.intersection(*children) if children else set()
        return set()
    known=guaranteed(facts)
    def explicit(formula):
        kind=formula[0]
        if kind=='true':return True
        if kind=='atom':return formula[1] in known
        if kind=='and':return all(explicit(child) for child in formula[1])
        if kind=='or':return any(explicit(child) for child in formula[1])
        return False
    if explicit(goal):return 'proven',None
    try: d = dnf(and_(facts, neg(goal)))
    except ProofLimit:
        # Long else-if chains (opcode dispatch) accumulate one disjunctive
        # `op != k` fact per arm, whose DNF exceeds the branch limit. Facts
        # sharing no variables with the goal cannot help prove it; dropping
        # facts only weakens the hypothesis, so only `proven` is reported.
        try: d = dnf(and_(relevant(facts, goal), neg(goal)))
        except ProofLimit: return 'unknown', None
        return ('proven', None) if all(fm_unsat(D) is True for D in d) else ('unknown', None)
    for D in d:
        r = fm_unsat(D)
        if r is None: return "unknown", None
        if r is False: return "unproven", model(D) if diagnostics else None
    return "proven", None

def model(cons: List[Lin], limit_vars=7) -> Optional[Dict[str, int]]:
    """Small brute-force integer model of a conjunction, for diagnostics."""
    vs = set()
    for c in cons: vs |= c.vars()
    vs = sorted(vs)
    if len(vs) > limit_vars: return None
    constraints = [integer_constraint(c) for c in cons]
    domain = [0, 1, -1, 2, 3, 4, 5, 8, -2, 10, 100]
    for vals in islice(product(domain, repeat=len(vs)), MODEL_BUDGET):
        env = dict(zip(vs, vals))
        ok = True
        for terms, constant in constraints:
            if constant + sum(k * env[v] for v, k in terms.items()) > 0: ok = False; break
        if ok: return {k: int(v) for k, v in env.items()}
    return None
