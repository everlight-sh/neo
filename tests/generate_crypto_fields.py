"""Regenerate the unrolled field arithmetic in the standard-library crypto modules.

Each module keeps its generated functions between `; generated: begin NAME`
and `; generated: end NAME` lines; this script rewrites only those regions.
Run it after changing a limb layout here, then rerun the crypto vector tests.

  x25519.neo  GF(2^255-19), ten signed limbs in radix 2^25.5 (ref10's layout):
              products of carried limbs stay below 2^62, so wrapping i64
              arithmetic is exact.
  p256.neo    Montgomery products modulo the P-256 prime and group order, nine
              unsigned 29-bit limbs, R = 2^261: a column holds at most 18
              products below 2^58, so every running sum stays below 2^63.
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
OFFSETS = [0, 26, 51, 77, 102, 128, 153, 179, 204, 230]
def width(i): return 26 if i % 2 == 0 else 25
FE = 'XFe'

def xf_carry():
    """ref10's carry chain: signed limbs bounded by 1.01*2^25 (even) / 2^24 (odd) after it."""
    order = [0, 4, 1, 5, 2, 6, 3, 7, 4, 8, 9, 0]
    lines = []
    for k in order:
        w = width(k); nxt = (k + 1) % 10
        lines.append(f'let c=arithmetic_shift_right(wrapping_add(h{k},{1 << (w - 1)}),{w}) in '
                     f'let h{nxt}=wrapping_add(h{nxt},{mul("c", 19) if k == 9 else "c"}) in let h{k}=wrapping_sub(h{k},shift_left(c,{w})) in')
    body = '\n    '.join(lines)
    fields = ','.join(f'f{i}=h{i}' for i in range(10))
    params = ','.join(f'h{i}:i64' for i in range(10))
    return (f'private fn xf_carry({params}) -> {FE}\n  = {body}\n    {FE} {{ {fields} }}')

def xf_mul():
    pre = []
    for j in range(1, 10): pre.append(f'let g{j}_19={mul(f"g.f{j}", 19)} in')
    for i in range(1, 10, 2): pre.append(f'let f{i}_2=shift_left(f.f{i},1) in')
    hs = []
    for k in range(10):
        terms = []
        for i in range(10):
            j = (k - i) % 10
            a = f'f{i}_2' if i % 2 == 1 and j % 2 == 1 else f'f.f{i}'
            b = f'g{j}_19' if i + j >= 10 else f'g.f{j}'
            terms.append(mul(a, b))
        hs.append(add(terms))
    args = ','.join(hs)
    return (f'private fn xf_mul(f:{FE},g:{FE}) -> {FE}\n  = ' + '\n    '.join(pre) +
            f'\n    xf_carry(' + ',\n      '.join(hs) + ')')

def xf_sq():
    pre = []
    for i in range(10):
        pre.append(f'let d{i}=shift_left(f.f{i},1) in')
    for i in range(1, 10):
        pre.append(f'let s{i}={mul(f"f.f{i}", 19)} in')
        pre.append(f'let t{i}={mul(f"f.f{i}", 38)} in')
    names = {1: 'f.f{}', 2: 'd{}', 19: 's{}', 38: 't{}'}
    hs = []
    for k in range(10):
        terms = []
        for i in range(10):
            for j in range(i, 10):
                if (i + j) % 10 != k: continue
                c = (2 if i != j else 1) * (2 if i % 2 == 1 and j % 2 == 1 else 1) * (19 if i + j >= 10 else 1)
                a = 'd{}'.format(i) if i != j else 'f.f{}'.format(i)
                rest = c // (2 if i != j else 1)
                terms.append(mul(a, names[rest].format(j)))
        hs.append(add(terms))
    return (f'private fn xf_sq(f:{FE}) -> {FE}\n  = ' + '\n    '.join(pre) +
            f'\n    xf_carry(' + ',\n      '.join(hs) + ')')

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

# ---------------------------------------------------------------- regions
def region(text, name, body):
    pattern = re.compile(rf'(; generated: begin {name}\n).*?(; generated: end {name}\n)', re.S)
    if not pattern.search(text): raise SystemExit(f'missing generated region {name}')
    return pattern.sub(lambda m: m.group(1) + body + '\n' + m.group(2), text)

def main():
    path = ROOT / 'stdlib/x25519.neo'; text = path.read_text()
    w = xf_words()
    text = region(text, 'xf_carry', xf_carry())
    text = region(text, 'xf_mul', xf_mul())
    text = region(text, 'xf_sq', xf_sq())
    text = region(text, 'xf_unpack', xf_unpack())
    text = region(text, 'xf_words', f'private fn xf_bytes(h:{FE}) -> Arr u8 _\n  = let out=arr(i in 0..32) u8(0) in\n    ' +
                  ' in\n    '.join(f'let out=byte_write_le(out,{8 * k},{w[k]},8)' for k in range(4)) + ' in out')
    path.write_text(text)
    path = ROOT / 'stdlib/p256.neo'; text = path.read_text()
    if '; generated: begin p9_mont' not in text: return
    w = p9_words()
    text = region(text, 'p9_mont', p9_mont())
    text = region(text, 'p9_norm', p9_norm())
    text = region(text, 'p9_unpack', p9_unpack())
    text = region(text, 'p9_words', f'private fn p9_bytes(a:{PF}) -> Arr u8 _\n  = let out=arr(i in 0..32) u8(0) in\n    ' +
                  ' in\n    '.join(f'let out=byte_write_le(out,{8 * (3 - k)},byte_swap64({w[k]}),8)' for k in range(4)) + ' in out')
    text = region(text, 'p9_constants', p9_constants())
    path.write_text(text)
    print('regenerated x25519.neo and p256.neo field arithmetic')

if __name__ == '__main__': main()
