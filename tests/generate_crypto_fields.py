"""Regenerate the unrolled field arithmetic in the standard-library crypto modules.

Each module keeps its generated functions between `; generated: begin NAME`
and `; generated: end NAME` lines; this script rewrites only those regions.
Run it after changing a limb layout here, then rerun the crypto vector tests.

  x25519.neo  GF(2^255-19), five unsigned limbs in radix 2^51 with 128-bit
              columns (hi and lo words, from wrapping_mul and mul_high):
              limbs below 2^53 give columns below 2^113.
  p256.neo    Montgomery products modulo the P-256 prime and group order, four
              unsigned 64-bit limbs, R = 2^256, by product scanning into a
              three-word column (wrapping_mul and mul_high per product).
  sha256.neo  the 64 SHA-256 rounds and message schedule, unrolled.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def add(terms):
    """Nested wrapping sum of expression strings."""
    out = terms[0]
    for term in terms[1:]: out = f'wrapping_add({out},{term})'
    return out

def mul(a, b): return f'wrapping_mul({a},{b})'

# ---------------------------------------------------------------- X25519
OFFSETS = [0, 51, 102, 153, 204]
def width(i): return 51
FE = 'XFe'

def wide_sum(terms):
    """A 128-bit sum of 64x64-bit products, as nested XWide accumulations."""
    (a, b), rest = terms[0], terms[1:]
    out = f'xw_product({a},{b})'
    for a, b in rest: out = f'xw_mac({out},{a},{b})'
    return out

def xf_reduce():
    """Carries five 128-bit columns into limbs below 2^51 (f1 may exceed it by a few bits)."""
    m = (1 << 51) - 1
    return (f'private fn xf_reduce(h0:XWide,h1:XWide,h2:XWide,h3:XWide,h4:XWide) -> {FE}\n'
            f'  = let h1=xw_add(h1,xw_shift51(h0)) in let h2=xw_add(h2,xw_shift51(h1)) in let h3=xw_add(h3,xw_shift51(h2)) in\n'
            f'    let h4=xw_add(h4,xw_shift51(h3)) in let r0=wrapping_add(bit_and(h0.lo,{m}),{mul("xw_shift51(h4)", 19)}) in\n'
            f'    {FE} {{ f0=bit_and(r0,{m}),f1=wrapping_add(bit_and(h1.lo,{m}),shift_right(r0,51)),f2=bit_and(h2.lo,{m}),'
            f'f3=bit_and(h3.lo,{m}),f4=bit_and(h4.lo,{m}) }}')

def xf_mul():
    pre = ' '.join(f'let g{j}={mul(f"g.f{j}", 19)} in' for j in range(1, 5))
    hs = [wide_sum([(f'f.f{i}', f'g{(k - i) % 5}' if i > k else f'g.f{k - i}') for i in range(5)]) for k in range(5)]
    return f'private fn xf_mul(f:{FE},g:{FE}) -> {FE}\n  = {pre}\n    xf_reduce(' + ',\n      '.join(hs) + ')'

def xf_sq():
    pre = ('let d0=shift_left(f.f0,1) in let d1=shift_left(f.f1,1) in '
           f'let s3={mul("f.f3", 19)} in let s4={mul("f.f4", 19)} in let t3={mul("f.f3", 38)} in let t4={mul("f.f4", 38)} in')
    columns = [[('f.f0', 'f.f0'), ('f.f1', 't4'), ('f.f2', 't3')], [('d0', 'f.f1'), ('f.f2', 't4'), ('f.f3', 's3')],
               [('d0', 'f.f2'), ('f.f1', 'f.f1'), ('f.f3', 't4')], [('d0', 'f.f3'), ('d1', 'f.f2'), ('f.f4', 's4')],
               [('d0', 'f.f4'), ('d1', 'f.f3'), ('f.f2', 'f.f2')]]
    return f'private fn xf_sq(f:{FE}) -> {FE}\n  = {pre}\n    xf_reduce(' + ',\n      '.join(map(wide_sum, columns)) + ')'

def xf_unpack():
    """Little-endian 255-bit value (bit 255 already cleared) into unsigned limbs."""
    out = []
    for i, off in enumerate(OFFSETS):
        k, s = divmod(off, 64); w = width(i)
        expr = f'shift_right(w{k},{s})' if s else f'w{k}'
        if s + w > 64: expr = f'bit_or({expr},shift_left(w{k + 1},{64 - s}))'
        out.append(f'f{i}=bit_and({expr},{(1 << w) - 1})')
    return (f'private fn xf_unpack(w0:i64,w1:i64,w2:i64,w3:i64) -> {FE}\n  = {FE} {{ ' + ','.join(out) + ' }')

def xf_words():
    """Canonical limbs (each within its width) into four little-endian words."""
    words = []
    for k in range(4):
        parts = []
        for i, off in enumerate(OFFSETS):
            lo, hi = off, off + width(i)
            if hi <= 64 * k or lo >= 64 * (k + 1): continue
            if lo >= 64 * k: parts.append(f'shift_left(h.f{i},{lo - 64 * k})' if lo > 64 * k else f'h.f{i}')
            else: parts.append(f'shift_right(h.f{i},{64 * k - lo})')
        expr = parts[0]
        for p in parts[1:]: expr = f'bit_or({expr},{p})'
        words.append(expr)
    return words

# ---------------------------------------------------------------- P-256
PF = 'P4'
W = 1 << 64
P = 2**256 - 2**224 + 2**192 + 2**96 - 1
N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
R = 2**256

def p4_limbs(value): return [(value >> (64 * i)) % W for i in range(4)]
def p4_signed(word): return word - W if word >= 1 << 63 else word
def p4_constant(value):
    return f'{PF} {{ ' + ','.join(f'l{i}={p4_signed(w)}' for i, w in enumerate(p4_limbs(value))) + ' }'

def p4_carries():
    """Four-limb sum and difference with the carry or borrow out (0 or 1)."""
    add = ['let s0=wrapping_add(a.l0,b.l0) in let c=p4_below(s0,a.l0) in']
    sub = ['let d0=wrapping_sub(a.l0,b.l0) in let c=p4_below(a.l0,b.l0) in']
    for k in range(1, 4):
        add.append(f'let t=wrapping_add(a.l{k},b.l{k}) in let s{k}=wrapping_add(t,c) in let c=bit_or(p4_below(t,a.l{k}),p4_below(s{k},t)) in')
        sub.append(f'let t=wrapping_sub(a.l{k},b.l{k}) in let d{k}=wrapping_sub(t,c) in let c=bit_or(p4_below(a.l{k},b.l{k}),p4_below(t,c)) in')
    return (f'private fn p4_add_carry(a:{PF},b:{PF}) -> P4Carry\n  = ' + '\n    '.join(add) +
            f'\n    P4Carry {{ value={PF} {{ l0=s0,l1=s1,l2=s2,l3=s3 }},carry=c }}\n'
            f'private fn p4_sub_borrow(a:{PF},b:{PF}) -> P4Carry\n  = ' + '\n    '.join(sub) +
            f'\n    P4Carry {{ value={PF} {{ l0=d0,l1=d1,l2=d2,l3=d3 }},carry=c }}')

def p4_product(head, m, square):
    """Montgomery product a*b/2^256 mod m by finely integrated product scanning.
    Column i adds the products a_j*b_(i-j) and q_j*m_(i-j); for i < 4 the digit
    q_i = c0*(-m^-1) mod 2^64 makes q_i*m_0 cancel the low word, which is
    shifted out. For a < 2^256 and b < m the result is below 2m, and one
    subtraction reduces it. The P-256 prime has -p^-1 = 1 mod 2^64 and
    m_0 = 2^64-1, so q_i = c0 and q_i*m_0 adds exactly q_i to the next word;
    its zero limb drops out. The square adds each cross product twice."""
    ml = p4_limbs(m); inverse = (-pow(m, -1, W)) % W
    prime = m == P
    assert not prime or (inverse == 1 and ml[0] == W - 1)
    lines = ['let s=P4Acc { c0=0,c1=0,c2=0 } in']
    for i in range(7):
        lo, hi = max(0, i - 3), min(i, 3)
        for j in range(lo, hi + 1):
            if not square: lines.append(f'let s=p4_mac(s,a.l{j},b.l{i - j}) in')
            elif j < i - j: lines.append(f'let s=p4_mac2(s,a.l{j},a.l{i - j}) in')
            elif j == i - j: lines.append(f'let s=p4_mac(s,a.l{j},a.l{j}) in')
        for j in range(lo, min(i, 4)):
            if ml[i - j]: lines.append(f'let s=p4_mac(s,q{j},{p4_signed(ml[i - j])}) in')
        if i < 4 and prime: lines.append(f'let q{i}=s.c0 in let s=p4_fold(s,q{i}) in')
        elif i < 4:
            lines.append(f'let q{i}=wrapping_mul(s.c0,{p4_signed(inverse)}) in '
                         f'let s=p4_fold(s,wrapping_add(mul_high(q{i},{p4_signed(ml[0])}),if s.c0==0 then 0 else 1)) in')
        else: lines.append(f'let r{i - 4}=s.c0 in let s=p4_shift(s) in')
    return head + '\n  = ' + '\n    '.join(lines) + f'\n    p4_final({PF} {{ l0=r0,l1=r1,l2=r2,l3=s.c0 }},s.c1,{p4_constant(m)})'

def p4_products():
    return '\n'.join([p4_product(f'private fn p4_field_mul(a:{PF},b:{PF}) -> {PF}', P, False),
                      p4_product(f'private fn p4_field_square(a:{PF}) -> {PF}', P, True),
                      p4_product(f'private fn p4_order_mul(a:{PF},b:{PF}) -> {PF}', N, False)])

def p4_constants():
    out = []
    for name, m in (('field', P), ('order', N)):
        inverse = (-pow(m, -1, W)) % W
        out.append(f'private fn p4_{name}() -> P256Mod\n  = P256Mod {{ modulus={p4_constant(m)},r2={p4_constant(R * R % m)},\n'
                   f'      one={p4_constant(R % m)},inverse={p4_signed(inverse)} }}')
    gx = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
    gy = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5
    b = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
    out.append(f'private fn p4_curve_b() -> {PF} = {p4_constant(b * R % P)}')
    # Odd multiples 1G, 3G, ..., 63G for width-7 NAF verification, affine in
    # Montgomery form: x then y, limbs little-endian (public data; ordinary
    # branches select them).
    table = []
    for k in range(1, 64, 2):
        x, y = affine_mul(k, (gx, gy))
        data = b''.join(w.to_bytes(8, 'little') for v in (x * R % P, y * R % P) for w in p4_limbs(v))
        table.append(''.join(f'\\x{c:02x}' for c in data))
    out.append('private fn p4_generator_bytes(index:i64) -> Arr u8 _\n  = ' + ' else\n    '.join(
        f'if index=={i} then "{t}"' for i, t in enumerate(table[:-1])) + f' else\n    "{table[-1]}"')
    return '\n'.join(out)

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

# ---------------------------------------------------------------- SHA-256
SHA_K = [int(x, 16) for x in '''428a2f98 71374491 b5c0fbcf e9b5dba5 3956c25b 59f111f1 923f82a4 ab1c5ed5 d807aa98 12835b01 243185be 550c7dc3
72be5d74 80deb1fe 9bdc06a7 c19bf174 e49b69c1 efbe4786 0fc19dc6 240ca1cc 2de92c6f 4a7484aa 5cb0a9dc 76f988da 983e5152 a831c66d b00327c8
bf597fc7 c6e00bf3 d5a79147 06ca6351 14292967 27b70a85 2e1b2138 4d2c6dfc 53380d13 650a7354 766a0abb 81c2c92e 92722c85 a2bfe8a1 a81a664b
c24b8b70 c76c51a3 d192e819 d6990624 f40e3585 106aa070 19a4c116 1e376c08 2748774c 34b0bcb5 391c0cb3 4ed8aa4a 5b9cca4f 682e6ff3 748f82ee
78a5636f 84c87814 8cc70208 90befffa a4506ceb bef9a3f7 c67178f2'''.split()]

def sha_schedule():
    """The next 16 message-schedule words from the previous 16 (w0 oldest)."""
    word = lambda i: f'w.w{i}' if i < 16 else f'n{i - 16}'
    lines = [f'let n{j}={add([f"sha_small1({word(j + 14)})", word(j + 9), f"sha_small0({word(j + 1)})", word(j)])} in' for j in range(16)]
    return (f'private inline fn sha_schedule(w:ShaWords) -> ShaWords\n  = ' + '\n    '.join(lines) +
            '\n    ShaWords { ' + ','.join(f'w{j}=n{j}' for j in range(16)) + ' }')

def sha_rounds(base):
    """Rounds base..base+7 as straight-line SSA over the working state."""
    rot = lambda x, r: f'sha_rotr({x},{r})'
    name = lambda v, i: f'{v}{i}' if i >= 0 else f'{v}m{-i}'
    lines = ['let a0=s.a in let am1=s.b in let am2=s.c in let am3=s.d in let e0=s.e in let em1=s.f in let em2=s.g in let em3=s.h in']
    for i in range(8):
        a, b, c, d = (name('a', i - k) for k in range(4)); e, f, g, h = (name('e', i - k) for k in range(4))
        lines.append(f'let t{i}={add([h, f"bit_xor(bit_xor({rot(e, 6)},{rot(e, 11)}),{rot(e, 25)})", f"bit_xor({g},bit_and({e},bit_xor({f},{g})))", str(SHA_K[base + i]), f"w.w{(base + i) % 16}"])} in '
                     f'let a{i + 1}={add([f"t{i}", f"bit_xor(bit_xor({rot(a, 2)},{rot(a, 13)}),{rot(a, 22)})", f"bit_or(bit_and({a},{b}),bit_and({c},bit_or({a},{b})))"])} in '
                     f'let e{i + 1}=wrapping_add({d},t{i}) in')
    return (f'private inline fn sha_rounds{base}(s:Sha256State,w:ShaWords) -> Sha256State\n  = ' + '\n    '.join(lines) +
            '\n    Sha256State { a=a8,b=a7,c=a6,d=a5,e=e8,f=e7,g=e6,h=e5 }')

def sha_compress():
    """All 64 rounds and the message schedule, unrolled in eight-round pieces
    that are forced inline (one straight-line function would nest too deeply
    for the parser). Words carry garbage above bit 31 (wrapping sums keep the
    low 32 bits exact); every rotation and shift masks its input first, so each
    compiles to a 32-bit rotate, and the chaining sums are masked at the end."""
    assert len(SHA_K) == 64
    steps = ['let r=s in']
    for base in range(0, 64, 8):
        if base and base % 16 == 0: steps.append('let w=sha_schedule(w) in')
        steps.append(f'let r=sha_rounds{base}(r,w) in')
    fields = ','.join(f'{k}=sha_u32(wrapping_add(s.{k},r.{k}))' for k in 'abcdefgh')
    pieces = [sha_schedule()] + [sha_rounds(b) for b in range(0, 64, 8)]
    return '\n'.join(pieces) + f'\nprivate fn sha_compress(s:Sha256State,w:ShaWords) -> Sha256State\n  = ' + '\n    '.join(steps) + f'\n    Sha256State {{ {fields} }}'

# ---------------------------------------------------------------- regions
def region(text, name, body):
    pattern = re.compile(rf'(; generated: begin {name}\n).*?(; generated: end {name}\n)', re.S)
    if not pattern.search(text): raise SystemExit(f'missing generated region {name}')
    return pattern.sub(lambda m: m.group(1) + body + '\n' + m.group(2), text)

def main():
    path = ROOT / 'stdlib/x25519.neo'; text = path.read_text()
    w = xf_words()
    text = region(text, 'xf_reduce', xf_reduce())
    text = region(text, 'xf_mul', xf_mul())
    text = region(text, 'xf_sq', xf_sq())
    text = region(text, 'xf_unpack', xf_unpack())
    text = region(text, 'xf_words', f'private fn xf_bytes(h:{FE}) -> Arr u8 _\n  = let out=arr(i in 0..32) u8(0) in\n    ' +
                  ' in\n    '.join(f'let out=byte_write_le(out,{8 * k},{w[k]},8)' for k in range(4)) + ' in out')
    path.write_text(text)
    path = ROOT / 'stdlib/p256.neo'; text = path.read_text()
    text = region(text, 'p4_carries', p4_carries())
    text = region(text, 'p4_products', p4_products())
    text = region(text, 'p4_constants', p4_constants())
    path.write_text(text)
    path = ROOT / 'stdlib/sha256.neo'; text = path.read_text()
    path.write_text(region(text, 'sha_compress', sha_compress()))
    print('regenerated x25519.neo, p256.neo and sha256.neo arithmetic')

if __name__ == '__main__': main()
