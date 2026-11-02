"""Regenerate the unrolled field arithmetic in the standard-library crypto modules.

Each module keeps its generated functions between `; generated: begin NAME`
and `; generated: end NAME` lines; this script rewrites only those regions.
Run it after changing a limb layout here, then rerun the crypto vector tests.

  x25519.neo  GF(2^255-19), five unsigned limbs in radix 2^51 with 128-bit
              columns (hi and lo words, from wrapping_mul and mul_high):
              limbs below 2^53 give columns below 2^113.
  p256.neo    Montgomery products modulo the P-256 prime and group order, nine
              unsigned 29-bit limbs, R = 2^261: a column holds at most 18
              products below 2^58, so every running sum stays below 2^63.
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
LIMBS, BITS = 9, 29
MASK = (1 << BITS) - 1
PF = 'P9'

def p9_mont():
    """Finely integrated product scanning: a*b/R mod m for a,b < 4m, result < 2m."""
    s = LIMBS
    lines = ['let acc=0 in']
    for i in range(2 * s - 1):
        terms = ['acc']
        lo, hi = max(0, i - s + 1), min(i, s - 1)
        for j in range(lo, hi + 1):
            terms.append(mul(f'a.l{j}', f'b.l{i - j}'))
            if j < i and i - j < s: terms.append(mul(f'q{j}', f'm.l{i - j}'))
        lines.append(f'let acc={add(terms)} in')
        if i < s:
            lines.append(f'let q{i}=bit_and(wrapping_mul(bit_and(acc,{MASK}),inverse),{MASK}) in')
            lines.append(f'let acc=shift_right(wrapping_add(acc,wrapping_mul(q{i},m.l0)),{BITS}) in')
        else:
            lines.append(f'let r{i - s}=bit_and(acc,{MASK}) in let acc=shift_right(acc,{BITS}) in')
    fields = ','.join(f'l{k}=r{k}' for k in range(s - 1)) + f',l{s - 1}=acc'
    return (f'private fn p9_mont(a:{PF},b:{PF},m:{PF},inverse:i64) -> {PF}\n  = ' + '\n    '.join(lines) +
            f'\n    {PF} {{ {fields} }}')

def p9_times_limb(q, limb):
    """q*limb for a P-256 prime limb, as shifts: every limb is 0, 2^a or 2^a-2^b."""
    if limb == 0: return None
    if limb & (limb - 1) == 0: return f'shift_left({q},{limb.bit_length() - 1})'
    high = limb.bit_length(); low = (1 << high) - limb
    assert low & (low - 1) == 0, limb
    low_term = q if low == 1 else f'shift_left({q},{low.bit_length() - 1})'
    return f'wrapping_sub(shift_left({q},{high}),{low_term})'

def p9_field(square):
    """p9_mont specialised to the P-256 prime: -p^-1 mod 2^29 is 1, so each
    quotient digit is the column's low limb, and the prime's limbs are sparse
    sums of powers of two, so q*m needs shifts instead of multiplications.
    Every term is the same nonnegative product as in p9_mont, so the bounds
    are unchanged. The square adds each cross product once, doubled."""
    s = LIMBS
    m = [(P >> (BITS * i)) & MASK for i in range(s)]
    assert (-pow(P, -1, 1 << BITS)) % (1 << BITS) == 1 and m[0] == MASK
    lines = ['let acc=0 in']
    if square: lines.append(' '.join(f'let d{j}=shift_left(a.l{j},1) in' for j in range(s - 1)))
    for i in range(2 * s - 1):
        terms = ['acc']
        lo, hi = max(0, i - s + 1), min(i, s - 1)
        for j in range(lo, hi + 1):
            if not square: terms.append(mul(f'a.l{j}', f'b.l{i - j}'))
            elif j < i - j: terms.append(mul(f'd{j}', f'a.l{i - j}'))
            elif j == i - j: terms.append(mul(f'a.l{j}', f'a.l{j}'))
            if j < i and i - j < s:
                term = p9_times_limb(f'q{j}', m[i - j])
                if term: terms.append(term)
        lines.append(f'let acc={add(terms)} in')
        if i < s:
            lines.append(f'let q{i}=bit_and(acc,{MASK}) in let acc=wrapping_add(shift_right(acc,{BITS}),q{i}) in')
        else:
            lines.append(f'let r{i - s}=bit_and(acc,{MASK}) in let acc=shift_right(acc,{BITS}) in')
    fields = ','.join(f'l{k}=r{k}' for k in range(s - 1)) + f',l{s - 1}=acc'
    head = f'private fn p9_field_square(a:{PF}) -> {PF}' if square else f'private fn p9_field_mont(a:{PF},b:{PF}) -> {PF}'
    return head + '\n  = ' + '\n    '.join(lines) + f'\n    {PF} {{ {fields} }}'

def p9_norm():
    """Signed limbs to limbs 0..7 in [0,2^29) and a signed top limb."""
    lines = []
    for k in range(LIMBS - 1):
        lines.append(f'let c=arithmetic_shift_right(l{k},{BITS}) in let l{k}=bit_and(l{k},{MASK}) in let l{k + 1}=wrapping_add(l{k + 1},c) in')
    params = ','.join(f'l{k}:i64' for k in range(LIMBS))
    fields = ','.join(f'l{k}=l{k}' for k in range(LIMBS))
    return f'private fn p9_norm({params}) -> {PF}\n  = ' + '\n    '.join(lines) + f'\n    {PF} {{ {fields} }}'

def p9_unpack():
    """Four little-endian 64-bit words (bits 0..255) into nine 29-bit limbs."""
    out = []
    for i in range(LIMBS):
        off = i * BITS; k, s = divmod(off, 64)
        expr = f'shift_right(w{k},{s})' if s else f'w{k}'
        if s + BITS > 64 and k + 1 < 4: expr = f'bit_or({expr},shift_left(w{k + 1},{64 - s}))'
        out.append(f'l{i}=bit_and({expr},{MASK})')
    return f'private fn p9_unpack(w0:i64,w1:i64,w2:i64,w3:i64) -> {PF}\n  = {PF} {{ ' + ','.join(out) + ' }'

def p9_words():
    words = []
    for k in range(4):
        parts = []
        for i in range(LIMBS):
            lo, hi = i * BITS, (i + 1) * BITS
            if hi <= 64 * k or lo >= 64 * (k + 1): continue
            if lo >= 64 * k: parts.append(f'shift_left(a.l{i},{lo - 64 * k})' if lo > 64 * k else f'a.l{i}')
            else: parts.append(f'shift_right(a.l{i},{64 * k - lo})')
        expr = parts[0]
        for p in parts[1:]: expr = f'bit_or({expr},{p})'
        words.append(expr)
    return words

def p9_constant(value):
    return f'{PF} {{ ' + ','.join(f'l{i}={(value >> (BITS * i)) & MASK}' for i in range(LIMBS)) + ' }'

P = 2**256 - 2**224 + 2**192 + 2**96 - 1
N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
R = 2**(LIMBS * BITS)

def p9_constants():
    out = []
    for name, m in (('field', P), ('order', N)):
        inverse = (-pow(m, -1, 1 << BITS)) % (1 << BITS)
        out.append(f'private fn p9_{name}() -> P256Mod\n  = P256Mod {{ modulus={p9_constant(m)},twice={p9_constant(2 * m)},\n'
                   f'      r2={p9_constant(R * R % m)},\n      one={p9_constant(R % m)},inverse={inverse} }}')
    gx = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
    gy = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5
    b = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
    out.append(f'private fn p9_curve_b() -> {PF} = {p9_constant(b * R % P)}')
    # Odd multiples 1G, 3G, ..., 15G in affine Montgomery form for the
    # verification window (public data; ordinary branches select them).
    table = []
    for k in range(1, 16, 2):
        x, y = affine_mul(k, (gx, gy))
        table.append((x * R % P, y * R % P))
    out.append(f'private fn p9_generator(index:i64) -> P9Affine\n  = ' + ' else\n    '.join(
        f'if index=={i} then P9Affine {{ x={p9_constant(x)},\n      y={p9_constant(y)} }}' for i, (x, y) in enumerate(table[:-1]))
        + f' else\n    P9Affine {{ x={p9_constant(table[-1][0])},\n      y={p9_constant(table[-1][1])} }}')
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
    if '; generated: begin p9_mont' not in text: return
    w = p9_words()
    text = region(text, 'p9_mont', p9_mont() + '\n' + p9_field(False) + '\n' + p9_field(True))
    text = region(text, 'p9_norm', p9_norm())
    text = region(text, 'p9_unpack', p9_unpack())
    text = region(text, 'p9_words', f'private fn p9_bytes(a:{PF}) -> Arr u8 _\n  = let out=arr(i in 0..32) u8(0) in\n    ' +
                  ' in\n    '.join(f'let out=byte_write_le(out,{8 * (3 - k)},byte_swap64({w[k]}),8)' for k in range(4)) + ' in out')
    text = region(text, 'p9_constants', p9_constants())
    path.write_text(text)
    path = ROOT / 'stdlib/sha256.neo'; text = path.read_text()
    path.write_text(region(text, 'sha_compress', sha_compress()))
    print('regenerated x25519.neo, p256.neo and sha256.neo arithmetic')

if __name__ == '__main__': main()
