"""Regenerate pinned Unicode 16 tables using CPython's Unicode 16 database."""
from pathlib import Path
import unicodedata
assert unicodedata.unidata_version=='16.0.0',unicodedata.unidata_version
ROOT=Path(__file__).resolve().parents[1]
def literal(data):return '"'+''.join('\\x%02x'%v for v in data)+'"'
fold=bytearray();ranges=[];start=None
for code in range(0x110000):
    char=chr(code);text=char.casefold()
    if text!=char:
        value=text.encode('utf8');assert len(value)<=12
        fold+=code.to_bytes(3,'little')+bytes([len(value)])+value+bytes(12-len(value))
    word=unicodedata.category(char)[0] in 'LN'
    if word and start is None:start=code
    if start is not None and (not word or code==0x10ffff):ranges.append((start,code-1 if not word else code));start=None
words=b''.join(a.to_bytes(3,'little')+b.to_bytes(3,'little') for a,b in ranges)
(ROOT/'stdlib/unicode_data.neo').write_text('; Generated from CPython Unicode 16.0.0, tests/generate_unicode_tables.py.\nfn unicode_fold_table() -> Arr u8 _ = '+literal(fold)+'\nfn unicode_word_table() -> Arr u8 _ = '+literal(words)+'\n')
print(len(fold)//16,'case fold entries;',len(ranges),'letter/number ranges')
