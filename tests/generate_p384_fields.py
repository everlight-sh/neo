"""Regenerate the unrolled P-384 arithmetic in stdlib/p384.neo.

The module keeps its generated functions between `; generated: begin NAME`
and `; generated: end NAME` lines; this script rewrites only those regions.
Run it after changing the layout here, then rerun tests/p384_language.py.

Values are records of six unsigned 64-bit limbs (little-endian) in Montgomery
form with R = 2^384, fully reduced below the modulus between operations.
Products use finely integrated product scanning: every column adds 128-bit
partial products (wrapping_mul for the low word, mul_high for the high word)
into a three-word accumulator, so carries are exact without 128-bit types.
The quotient digit of the prime is c0*(2^32+1) mod 2^64 (-p^-1 mod 2^64 is
2^32+1); the group order uses a constant multiplier. Each product is split
into `private inline fn` pieces of a few columns so that no function nests
more `let`s than the parser's recursion limit allows.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

S = 6                       # limbs
MASK = (1 << 64) - 1
R = 1 << (64 * S)
P = 2**384 - 2**128 - 2**96 + 2**32 - 1
N = 0xffffffffffffffffffffffffffffffffffffffffffffffffc7634d81f4372ddf581a0db248b0a77aecec196accc52973
B = 0xb3312fa7e23ee7e4988e056be3f82d19181d9c6efe8141120314088f5013875ac656398d8a2ed19d2a85c8edd3ec2aef
GX = 0xaa87ca22be8b05378eb1c71ef320ad746e1d3b628ba79b9859f741e082542a385502f25dbf55296c3a545e3872760ab7
GY = 0x3617de4a96262c6f5d9e98bf9292dc29f8f41dbd289a147ce9da3113b5f0b8c00a60b1ce1d7e819d7a431d7c90ea0e5f
GROUP = 'P6'                # limb record type
ACC = 'P6Acc'               # product-scanning accumulator and digits
PIECE_COLUMNS = [(0, 1, 2, 3), (4, 5), (6, 7), (8, 9, 10)]
GENERATOR_ODD = 32         # table entries for the width-7 generator digits

def lit(value):
    """A 64-bit pattern as a signed i64 literal."""
    value &= MASK
    return str(value - (1 << 64) if value >= 1 << 63 else value)

def limbs(value): return [(value >> (64 * i)) & MASK for i in range(S)]

def constant(value):
    assert 0 <= value < R
    return f'{GROUP} {{ ' + ','.join(f'l{i}={lit(v)}' for i, v in enumerate(limbs(value))) + ' }'

# ---------------------------------------------------------------- products
# Montgomery reduction adds q_j*m at column j for the quotient digit q_j. The
# moduli's sparse forms replace most of those products:
#   p = (2^32-1) - 2^32*2^64 - 2^128 + 2^384   (relative to column j)
#   n = n0 + n1*2^64 + n2*2^128 - 2^192 + 2^384   (n3 = n4 = n5 = 2^64-1)
# The accumulator is a signed three-word value (two's complement): reduction
# terms may be subtracted before later columns add them back, and every shift
# keeps the sign.
FIELD_TERMS = lambda: [(1, 'sub2'), (2, 'sub1'), (6, 'add1')]
ORDER_TERMS = lambda: [(1, 'mac1'), (2, 'mac2'), (3, 'sub1'), (6, 'add1')]

def check_terms():
    """The column terms rebuild each modulus exactly."""
    m = limbs(N)
    assert m[3] == m[4] == m[5] == MASK
    assert (2**32 - 1) - 2**32 * 2**64 - 2**128 + 2**384 == P
    assert m[0] + m[1] * 2**64 + m[2] * 2**128 - 2**192 + 2**384 == N
    assert (-pow(P, -1, 1 << 64)) % (1 << 64) == (1 << 32) + 1 and P & MASK == 2**32 - 1

def column(i, m, square, field):
    """Lines adding column i of a*b (or a*a) and the reduction terms of earlier
    quotient digits, then the quotient digit step (i < 6) or a result word."""
    out = []
    lo, hi = max(0, i - S + 1), min(i, S - 1)
    for j in range(lo, hi + 1):
        k = i - j
        if not square: out.append(f'let s=p6_mac(s,a.l{j},b.l{k}) in')
        elif j < k: out.append(f'let s=p6_mac2(s,a.l{j},a.l{k}) in')
        elif j == k: out.append(f'let s=p6_mac(s,a.l{j},a.l{j}) in')
    for offset, kind in (FIELD_TERMS() if field else ORDER_TERMS()):
        j = i - offset
        if not 0 <= j < S: continue
        w = f's.w{j}'
        if kind == 'sub2': out.append(f'let s=p6_sub2(s,shift_left({w},32),shift_right({w},32)) in')
        elif kind == 'sub1': out.append(f'let s=p6_sub1(s,{w}) in')
        elif kind == 'add1': out.append(f'let s=p6_add1(s,{w}) in')
        else: out.append(f'let s=p6_mac(s,{w},{lit(m[1 if kind == "mac1" else 2])}) in')
    if i < S:
        if field: out.append(f'let q=wrapping_add(s.c0,shift_left(s.c0,32)) in let s=p6_fold(s,wrapping_sub(shift_right(q,32),p6_below(shift_left(q,32),q))) with {{ w{i}=q }} in')
        else:
            inverse = (-pow(N, -1, 1 << 64)) % (1 << 64)
            out.append(f'let q=wrapping_mul(s.c0,{lit(inverse)}) in let s=p6_fold(s,mul_high(q,{lit(m[0])})) with {{ w{i}=q }} in')
    else:
        out.append(f'let s=s with {{ c0=s.c1,c1=s.c2,c2=arithmetic_shift_right(s.c2,63),w{i - S}=s.c0 }} in')
    return out

def product(name, modulus, square):
    """Montgomery product a*b/R (or a*a/R) mod modulus for inputs below it."""
    m = limbs(modulus); field = modulus == P
    params = 'a:P6' if square else 'a:P6,b:P6'
    args = 'a' if square else 'a,b'
    pieces = []
    for index, columns in enumerate(PIECE_COLUMNS[1:], 1):
        body = [line for i in columns for line in column(i, m, square, field)]
        pieces.append(f'private inline fn {name}{index}({params},s:{ACC}) -> {ACC}\n  = ' + '\n    '.join(body) + '\n    s')
    # The first columns stay in the entry function, so it is too large for
    # neoc's small-function inlining and stays one out-of-line call per product.
    head = ['let s=P6Acc { c0=0,c1=0,c2=0,w0=0,w1=0,w2=0,w3=0,w4=0,w5=0 } in']
    head += [line for i in PIECE_COLUMNS[0] for line in column(i, m, square, field)]
    head += [f'let s={name}{index}({args},s) in' for index in range(1, len(PIECE_COLUMNS))]
    # +q5 belongs to column 11, the last result word (c0 after column 10).
    entry = (f'private fn {name}({params}) -> P6\n  = ' + '\n    '.join(head) +
             f'\n    p6_final(p6_add1(s,s.w5),{constant(modulus)})')
    return '\n'.join(pieces + [entry])

def products():
    check_terms()
    # Verification never squares modulo the order, so there is no order square.
    return '\n'.join([product('p6_field_mul', P, False), product('p6_field_square', P, True),
                      product('p6_order_mul', N, False)])

# ---------------------------------------------------------------- carries
def carries():
    """Six-limb sum and difference with the carry (borrow) out. The forms are
    the ones LLVM turns into add/adc and sub/sbb chains."""
    add = ['let s0=wrapping_add(a.l0,b.l0) in let c=p6_below(s0,a.l0) in']
    sub = ['let d0=wrapping_sub(a.l0,b.l0) in let c=p6_below(a.l0,b.l0) in']
    for i in range(1, S):
        add.append(f'let t=wrapping_add(a.l{i},b.l{i}) in let s{i}=wrapping_add(t,c) in let c=bit_or(p6_below(t,a.l{i}),p6_below(s{i},t)) in')
        sub.append(f'let t=wrapping_sub(a.l{i},b.l{i}) in let d{i}=wrapping_sub(t,c) in let c=bit_or(p6_below(a.l{i},b.l{i}),p6_below(t,c)) in')
    fields = lambda v: f'{GROUP} {{ ' + ','.join(f'l{i}={v}{i}' for i in range(S)) + ' }'
    return (f'private fn p6_add_carry(a:P6,b:P6) -> P6Carry\n  = ' + '\n    '.join(add) + f'\n    P6Carry {{ value={fields("s")},carry=c }}\n'
            f'private fn p6_sub_borrow(a:P6,b:P6) -> P6Carry\n  = ' + '\n    '.join(sub) + f'\n    P6Carry {{ value={fields("d")},carry=c }}')

# ---------------------------------------------------------------- constants
def affine_add(p, q):
    if p is None: return q
    if q is None: return p
    if p[0] == q[0] and (p[1] + q[1]) % P == 0: return None
    if p == q: l = (3 * p[0] * p[0] - 3) * pow(2 * p[1], -1, P) % P
    else: l = (q[1] - p[1]) * pow(q[0] - p[0], -1, P) % P
    x = (l * l - p[0] - q[0]) % P
    return x, (l * (p[0] - x) - p[1]) % P

def affine_mul(k, p):
    out = None
    while k:
        if k & 1: out = affine_add(out, p)
        p = affine_add(p, p); k >>= 1
    return out

def constants():
    assert (GY * GY - GX ** 3 + 3 * GX - B) % P == 0
    out = [f'private fn p6_prime() -> P6 = {constant(P)}',
           f'private fn p6_order() -> P6 = {constant(N)}',
           f'private fn p6_field_r2() -> P6 = {constant(R * R % P)}',
           f'private fn p6_order_r2() -> P6 = {constant(R * R % N)}',
           f'private fn p6_field_one() -> P6 = {constant(R % P)}',
           f'private fn p6_curve_b() -> P6 = {constant(B * R % P)}']
    # Odd multiples 1G, 3G, ..., 63G in affine Montgomery form for width-7
    # NAF digits of u1 (public data; ordinary branches select them), as 96
    # bytes each: x then y, little-endian limbs.
    entries = []
    for k in range(1, 2 * GENERATOR_ODD, 2):
        x, y = affine_mul(k, (GX, GY))
        raw = b''.join(v.to_bytes(8, 'little') for v in limbs(x * R % P) + limbs(y * R % P))
        entries.append('"' + ''.join(f'\\x{b:02x}' for b in raw) + '"')
    out.append('private fn p384_generator_bytes(index:i64) -> Arr u8 _\n  = ' + ' else\n    '.join(
        f'if index=={i} then {e}' for i, e in enumerate(entries[:-1])) + f' else\n    {entries[-1]}')
    return '\n'.join(out)

# ---------------------------------------------------------------- regions
def region(text, name, body):
    pattern = re.compile(rf'(; generated: begin {name}\n).*?(; generated: end {name}\n)', re.S)
    if not pattern.search(text): raise SystemExit(f'missing generated region {name}')
    return pattern.sub(lambda m: m.group(1) + body + '\n' + m.group(2), text)

def main():
    path = ROOT / 'stdlib/p384.neo'; text = path.read_text()
    text = region(text, 'p6_carries', carries())
    text = region(text, 'p6_products', products())
    text = region(text, 'p6_constants', constants())
    path.write_text(text)
    print('regenerated p384.neo arithmetic')

if __name__ == '__main__': main()
