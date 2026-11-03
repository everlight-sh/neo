"""Textual projection of Neo: lexer, AST, parser.

The text form is a *projection* of the content-addressed graph (see graph.py);
it exists so models and humans can emit/audit programs. Names never reach the
graph: variables are hashed by binder distance, functions by content hash,
record fields by position.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------- types
@dataclass(frozen=True)
class TInt:
    def __str__(self): return "i64"
@dataclass(frozen=True)
class TFloat:
    def __str__(self): return "f64"
@dataclass(frozen=True)
class TBool:
    def __str__(self): return "bool"
@dataclass(frozen=True)
class TByte:
    def __str__(self): return "u8"
@dataclass(frozen=True)
class TU16:
    def __str__(self): return "u16"
@dataclass(frozen=True)
class TInt32:
    def __str__(self): return "i32"
@dataclass(frozen=True)
class TPtr:
    def __str__(self): return "ptr"
@dataclass(frozen=True)
class TUnit:
    def __str__(self): return "unit"
@dataclass(frozen=True)
class TRec:
    name: str
    fields: Tuple[Tuple[str, Any], ...]      # (field name, scalar type) in declaration order
    args: Tuple[Any, ...] = ()
    def __str__(self): return self.name + ('<' + ', '.join(map(str,self.args)) + '>' if self.args else '')
    def index(self, f: str) -> int:
        for k, (n, _) in enumerate(self.fields):
            if n == f: return k
        raise KeyError(f)
@dataclass(frozen=True)
class TRef:
    resource: Any
    def __str__(self):return 'Ref<'+str(self.resource)+'>'
@dataclass(frozen=True)
class TFn:
    params: tuple
    ret: Any
    capabilities: Optional[tuple] = None
    def __post_init__(self):
        if self.capabilities is not None:object.__setattr__(self,"capabilities",tuple(sorted(set(self.capabilities))))
    def __str__(self):
        prefix='Fn' if self.capabilities is None else 'Effect<'+','.join(self.capabilities)+'>'
        return prefix+'('+', '.join(map(str,self.params))+')->'+str(self.ret)
@dataclass(frozen=True)
class TArr:
    elem: Any
    size: Any          # str (size variable or "_") or expr node in source; Lin after checking
    def __str__(self): return f"Arr {self.elem} {self.size if isinstance(self.size, str) else '(…)'}"

I64, F64, BOOL, U8 = TInt(), TFloat(), TBool(), TByte()
I32, PTR, UNIT = TInt32(), TPtr(), TUnit()
U16 = TU16()           # UTF-16 code units: unsigned 16-bit, like u8 a wrapping conversion target
SCALARS = (I64, F64, BOOL, U8, U16)

# ---------------------------------------------------------------- AST
@dataclass
class Node:
    pos: Tuple[int, int] = field(default=(0, 0), kw_only=True)
    ty: Any = field(default=None, kw_only=True)        # filled by checker
    hash: str = field(default="", kw_only=True)        # filled by graph.py

@dataclass
class Num(Node):    value: int
@dataclass
class Flt(Node):    value: float
@dataclass
class BoolLit(Node): value: bool
@dataclass
class Str(Node):    value: bytes          # "..." literal: Arr u8 k
@dataclass
class Byte(Node):   value: int            # 'c' literal: u8
@dataclass
class Var(Node):    name: str
@dataclass
class Bin(Node):    op: str; left: Node; right: Node
@dataclass
class Un(Node):     op: str; expr: Node
@dataclass
class Index(Node):  arr: Node; idx: Node
@dataclass
class Call(Node):
    name: str
    args: List[Node]
    type_args: Tuple[Any, ...] = ()
@dataclass
class Let(Node):    name: str; value: Node; body: Node
@dataclass
class If(Node):     cond: Node; then: Node; els: Node
@dataclass
class Sum(Node):    var: str; lo: Node; hi: Node; body: Node
@dataclass
class ArrC(Node):   var: str; lo: Node; hi: Node; body: Node
@dataclass
class Loop(Node):
    names: List[str]; inits: List[Node]; cond: Node; nexts: List[Node]; yld: Node
    annots: List[Any] = field(default_factory=list)   # per state: None or (type, [preds]) = loop invariant
@dataclass
class Check(Node):  pred: Node; body: Node
@dataclass
class Len(Node):    expr: Node
@dataclass
class Cast(Node):   to: Any; expr: Node
@dataclass
class RecLit(Node): tname: str; fields: List[Tuple[str, Node]]
@dataclass
class Field(Node):  expr: Node; name: str
@dataclass
class With(Node):   expr: Node; fields: List[Tuple[str, Node]]
@dataclass
class Match(Node):
    expr: Node
    arms: List[Tuple[str, List[str], Node]]
@dataclass
class Try(Node): expr: Node
@dataclass
class Using(Node): name: str; value: Node; body: Node

@dataclass
class Param:
    name: str
    ty: Any
    preds: List[Node]
    pos: Tuple[int, int] = (0, 0)
    owned: bool = False
    borrowed: bool = False

@dataclass
class Fn:
    name: str
    params: List[Param]
    ret: Any
    body: Node
    ret_preds: List[Node] = field(default_factory=list)   # refinements on `result`
    pos: Tuple[int, int] = (0, 0)
    hash: str = ""
    effect: bool = False
    external: bool = False
    exported: bool = False
    variadic: bool = False
    capabilities: Optional[Tuple[str, ...]] = None
    type_params: Tuple[str, ...] = ()
    cold: bool = False     # rarely called: never inlined, calls to it are unlikely paths
    inline: bool = False   # always inlined into callers, whatever NEO_INLINE_BUDGET says

@dataclass
class TypeDecl:
    name: str
    fields: List[Tuple[str, Any]]
    pos: Tuple[int, int] = (0, 0)
    sealed: bool = False
    type_params: Tuple[str, ...] = ()
    variants: Optional[List[Tuple[str, List[Any]]]] = None
    resource_drop: Optional[str] = None

@dataclass
class Program:
    types: List[TypeDecl]
    fns: List[Fn]
    imports: List[Tuple[str, Tuple[int, int], Optional[str]]] = field(default_factory=list)

# ---------------------------------------------------------------- lexer
KEYWORDS = {"fn", "let", "in", "if", "then", "else", "sum", "arr", "loop", "while",
            "next", "yield", "check", "true", "false", "len", "i64", "f64", "u8", "u16", "bool", "Arr",
            "type", "with", "effect", "extern", "export", "ptr", "i32", "unit", "import", "sealed",
            "enum", "match", "as", "move", "pub", "private", "resource", "drop", "using"}
SYMBOLS = ["...", "::", "=>", "->", "..", "==", "!=", "<=", ">=", "&&", "||", "?",
           "(", ")", "{", "}", "[", "]", ",", ":", "=", "<", ">", "+", "-", "*", "/", "%", "!", "."]

@dataclass
class Tok:
    kind: str      # IDENT, INT, FLOAT, STR, CHAR, KW, SYM, EOF
    text: str
    pos: Tuple[int, int]

class SyntaxError_(Exception):
    def __init__(self, msg, pos):
        super().__init__(f"{pos[0]}:{pos[1]}: {msg}")
        self.pos = pos; self.msg = msg

def lex(src: str) -> List[Tok]:
    toks, i, line, col = [], 0, 1, 1
    n = len(src)
    def adv(k=1):
        nonlocal i, line, col
        for _ in range(k):
            if src[i] == "\n": line += 1; col = 1
            else: col += 1
            i += 1
    while i < n:
        c = src[i]
        if c in " \t\r\n": adv(); continue
        if c == ";" or c == "#":
            while i < n and src[i] != "\n": adv()
            continue
        pos = (line, col)
        if c == '"' or c == "'":
            quote = c; adv(); buf = bytearray()
            while i < n and src[i] != quote:
                ch = src[i]
                if ch == "\\":
                    adv()
                    if i >= n: raise SyntaxError_("unterminated escape", pos)
                    e = src[i]; adv()
                    m = {"n": 10, "r": 13, "t": 9, "0": 0, "\\": 92, '"': 34, "'": 39}
                    if e == "x":
                        buf.append(int(src[i:i + 2], 16)); adv(2)
                    elif e in m: buf.append(m[e])
                    else: raise SyntaxError_(f"bad escape \\{e}", pos)
                else:
                    buf.extend(ch.encode("utf-8")); adv()
            if i >= n: raise SyntaxError_("unterminated literal", pos)
            adv()
            if quote == "'":
                if len(buf) != 1: raise SyntaxError_("byte literal must be exactly one byte", pos)
                toks.append(Tok("CHAR", str(buf[0]), pos))
            else:
                toks.append(Tok("STR", buf.decode("latin-1"), pos))
            continue
        if c.isdigit():
            j = i
            while j < n and src[j].isdigit(): j += 1
            is_float = False
            if j + 1 < n and src[j] == "." and src[j + 1].isdigit():
                is_float = True; j += 1
                while j < n and src[j].isdigit(): j += 1
            if j < n and src[j] in "eE" and is_float:
                k = j + 1
                if k < n and src[k] in "+-": k += 1
                if k < n and src[k].isdigit():
                    j = k
                    while j < n and src[j].isdigit(): j += 1
            text = src[i:j]; adv(j - i)
            toks.append(Tok("FLOAT" if is_float else "INT", text, pos)); continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"): j += 1
            text = src[i:j]; adv(j - i)
            toks.append(Tok("KW" if text in KEYWORDS else "IDENT", text, pos)); continue
        for s in SYMBOLS:
            if src.startswith(s, i):
                adv(len(s)); toks.append(Tok("SYM", s, pos)); break
        else:
            raise SyntaxError_(f"unexpected character {c!r}", pos)
    toks.append(Tok("EOF", "", (line, col)))
    return toks

# ---------------------------------------------------------------- parser
class Parser:
    def __init__(self, toks: List[Tok], type_names=()):
        self.toks = toks; self.i = 0
        # record type names are needed to recognise `Name { ... }` literals
        self.type_names = {toks[k + 1].text for k in range(len(toks) - 1)
                           if toks[k].kind == "KW" and toks[k].text in ("type","enum") and toks[k + 1].kind == "IDENT"}
        self.type_names.update(type_names)

    @property
    def tok(self) -> Tok: return self.toks[self.i]
    def peek(self, k=1) -> Tok: return self.toks[min(self.i + k, len(self.toks) - 1)]
    def at(self, kind, text=None):
        t = self.tok
        return t.kind == kind and (text is None or t.text == text)
    def at_sym(self, s): return self.at("SYM", s)
    def at_kw(self, s): return self.at("KW", s)
    def next(self) -> Tok:
        t = self.tok; self.i += 1; return t
    def expect(self, kind, text=None) -> Tok:
        if not self.at(kind, text):
            want = text or kind
            raise SyntaxError_(f"expected {want!r}, got {self.tok.text!r}", self.tok.pos)
        return self.next()
    def ident(self) -> str: return self.expect("IDENT").text

    def program(self) -> Program:
        types, fns, imports = [], [], []
        while not self.at("EOF"):
            if self.at_kw("import"):
                pos = self.next().pos
                path=self.expect("STR").text.encode('latin-1').decode('utf-8');alias=None
                if self.at_kw('as'):self.next();alias=self.ident()
                imports.append((path,pos,alias))
            else:
                visible=True
                if self.at_kw('private') or self.at_kw('pub'):visible=self.next().text=='pub'
                if self.at_kw("type") or self.at_kw("sealed") or self.at_kw('enum') or self.at_kw('resource'):
                    declaration=self.type_decl();types.append(declaration)
                else:declaration=self.fn();fns.append(declaration)
                declaration.visible=visible
        return Program(types, fns, imports)

    def type_decl(self) -> TypeDecl:
        resource=self.at_kw('resource')
        if resource:self.next()
        sealed = self.at_kw('sealed')
        if sealed: self.next()
        if self.at_kw('enum'):
            pos=self.next().pos;name=self.ident();params=self.type_parameters()
            self.expect('SYM','{');variants=[]
            while not self.at_sym('}'):
                variant=self.ident();payload=[]
                if self.at_sym('('):
                    self.next()
                    while not self.at_sym(')'):
                        payload.append(self.type_())
                        if self.at_sym(','):self.next()
                        elif not self.at_sym(')'):self.expect('SYM',')')
                    self.next()
                variants.append((variant,payload))
                if self.at_sym(','):self.next()
                elif not self.at_sym('}'):self.expect('SYM','}')
            self.next()
            return TypeDecl(name,[],pos,True,params,variants)
        pos = self.expect("KW", "type").pos
        name = self.ident(); params=self.type_parameters(); self.expect("SYM", "="); self.expect("SYM", "{")
        fields = []
        while not self.at_sym("}"):
            f = self.ident(); self.expect("SYM", ":"); fields.append((f, self.type_()))
            if self.at_sym(","): self.next()
        self.expect("SYM", "}")
        declaration=TypeDecl(name, fields, pos, sealed or resource,params)
        if resource:
            self.expect('KW','drop');declaration.resource_drop=self.qualified_ident()
        return declaration

    def type_parameters(self):
        if not self.at_sym('<'):return ()
        self.next();names=[self.ident()]
        while self.at_sym(','):self.next();names.append(self.ident())
        self.expect('SYM','>')
        if len(set(names))!=len(names):raise SyntaxError_('duplicate type parameter',self.tok.pos)
        return tuple(names)

    def type_arguments(self):
        self.expect('SYM','<');types=[self.type_()]
        while self.at_sym(','):self.next();types.append(self.type_())
        self.expect('SYM','>');return tuple(types)

    def qualified_ident(self):
        name=self.ident()
        while self.at_sym('::') and self.peek().kind=='IDENT':
            self.next();name+='::'+self.ident()
        return name

    def preds_block(self) -> List[Node]:
        preds = []
        if self.at_sym("{"):
            self.next()
            while True:
                preds.append(self.expr())
                if self.at_sym(","): self.next(); continue
                break
            self.expect("SYM", "}")
        return preds

    def fn(self) -> Fn:
        external = exported = effect = False
        capabilities = None
        # Contextual modifiers, so `cold`/`inline` stay ordinary identifiers elsewhere.
        cold = inline = False
        while self.at('IDENT') and self.tok.text in ('cold', 'inline') and self.peek().kind in ('KW', 'IDENT') \
                and self.peek().text in ('fn', 'effect', 'cold', 'inline'):
            word = self.next()
            if word.text == 'cold': cold = True
            else: inline = True
        if cold and inline: raise SyntaxError_('a function cannot be both cold and inline', self.tok.pos)
        if self.at_kw("extern"): self.next(); external = effect = True
        elif self.at_kw("export"): self.next(); exported = True
        if self.at_kw("effect"):
            self.next(); effect = True
            if self.at_sym('('):
                self.next(); caps = []
                while not self.at_sym(')'):
                    caps.append(self.ident())
                    if self.at_sym(','): self.next()
                    elif not self.at_sym(')'): self.expect('SYM', ')')
                self.next(); capabilities = tuple(caps)
        pos = self.expect("KW", "fn").pos
        name = self.ident();type_params=self.type_parameters()
        self.expect("SYM", "(")
        params = []
        variadic = False
        while not self.at_sym(")"):
            if self.at_sym("..."):
                self.next(); variadic = True; break
            ppos = self.tok.pos
            owned=self.at_kw('move')
            if owned:self.next()
            # Contextual modifier: existing arithmetic bindings named `borrow`
            # remain ordinary identifiers outside a parameter declaration.
            borrowed=self.at('IDENT','borrow') and self.peek().kind=='IDENT'
            if borrowed:self.next()
            if owned and borrowed:raise SyntaxError_('parameter cannot be both move and borrow',ppos)
            pname = self.ident(); self.expect("SYM", ":")
            pty = self.type_()
            preds = self.preds_block()
            params.append(Param(pname, pty, preds, ppos,owned,borrowed))
            if self.at_sym(","): self.next()
        self.expect("SYM", ")")
        self.expect("SYM", "->")
        ret = self.type_()
        ret_preds = self.preds_block()
        if external:
            return Fn(name, params, ret, Num(0, pos=pos), ret_preds, pos,
                      effect=effect, external=True, variadic=variadic,type_params=type_params)
        if variadic: raise SyntaxError_("only extern functions may be variadic", pos)
        self.expect("SYM", "=")
        body = self.expr()
        return Fn(name, params, ret, body, ret_preds, pos, effect=effect, exported=exported, capabilities=capabilities,type_params=type_params,cold=cold,inline=inline)

    def type_(self):
        t = self.next()
        if t.kind == "KW" and t.text == "i64": return I64
        if t.kind == "KW" and t.text == "f64": return F64
        if t.kind == "KW" and t.text == "bool": return BOOL
        if t.kind == "KW" and t.text == "u8": return U8
        if t.kind == "KW" and t.text == "u16": return U16
        if t.kind == "KW" and t.text == "i32": return I32
        if t.kind == "KW" and t.text == "ptr": return PTR
        if t.kind == "KW" and t.text == "unit": return UNIT
        if t.kind=='IDENT' and t.text=='Ref':
            self.expect('SYM','<');inner=self.type_();self.expect('SYM','>');return TRef(inner)
        if t.kind == "IDENT" and t.text in ('Fn','Effect'):
            caps=None
            if t.text=='Effect':
                self.expect('SYM','<');items=[]
                while not self.at_sym('>'):
                    items.append(self.ident())
                    if self.at_sym(','):self.next()
                    elif not self.at_sym('>'):self.expect('SYM','>')
                self.next();caps=tuple(sorted(set(items)))
            self.expect('SYM','(');params=[]
            while not self.at_sym(')'):
                params.append(self.type_())
                if self.at_sym(','):self.next()
                elif not self.at_sym(')'):self.expect('SYM',')')
            self.next();self.expect('SYM','->');return TFn(tuple(params),self.type_(),caps)
        if t.kind == "IDENT":
            name=t.text
            while self.at_sym('::') and self.peek().kind=='IDENT':self.next();name+='::'+self.ident()
            return TRec(name, (), self.type_arguments() if self.at_sym('<') else ())
        if t.kind == "KW" and t.text == "Arr":
            elem = self.type_()
            if self.at_sym("("):                       # size expression, e.g. Arr u8 (n + m)
                self.next(); size = self.add(); self.expect("SYM", ")")
            else:
                size = self.ident()                    # a size variable, or `_` for "unknown to the caller"
            return TArr(elem, size)
        raise SyntaxError_(f"expected type, got {t.text!r}", t.pos)

    # expr := keyword forms | or_expr
    def expr(self) -> Node:
        return self.or_()

    def or_(self) -> Node:
        e = self.and_()
        while self.at_sym("||"):
            pos = self.next().pos; r = self.and_()
            e = Bin("||", e, r, pos=pos)
        return e
    def and_(self) -> Node:
        e = self.cmp()
        while self.at_sym("&&"):
            pos = self.next().pos; r = self.cmp()
            e = Bin("&&", e, r, pos=pos)
        return e
    def cmp(self) -> Node:
        e = self.add()
        if self.tok.kind == "SYM" and self.tok.text in ("<", "<=", ">", ">=", "==", "!="):
            t = self.next(); r = self.add()
            e = Bin(t.text, e, r, pos=t.pos)
        return e
    def add(self) -> Node:
        e = self.mul()
        while self.tok.kind == "SYM" and self.tok.text in ("+", "-"):
            t = self.next(); r = self.mul()
            e = Bin(t.text, e, r, pos=t.pos)
        return e
    def mul(self) -> Node:
        e = self.unary()
        while self.tok.kind == "SYM" and self.tok.text in ("*", "/", "%"):
            t = self.next(); r = self.unary()
            e = Bin(t.text, e, r, pos=t.pos)
        return e
    def unary(self) -> Node:
        if self.at_sym("-"):
            pos = self.next().pos; e = self.unary()
            if isinstance(e, Num): return Num(-e.value, pos=pos)
            if isinstance(e, Flt): return Flt(-e.value, pos=pos)
            return Un("-", e, pos=pos)
        if self.at_sym("!"):
            pos = self.next().pos; return Un("!", self.unary(), pos=pos)
        return self.postfix()
    def postfix(self) -> Node:
        e = self.atom()
        while True:
            if self.at_sym("["):
                pos = self.next().pos; idx = self.expr(); self.expect("SYM", "]")
                e = Index(e, idx, pos=pos)
            elif self.at_sym("."):
                pos = self.next().pos; e = Field(e, self.ident(), pos=pos)
            elif self.at_kw("with"):
                pos = self.next().pos; e = With(e, self.field_inits(), pos=pos)
            elif self.at_sym('?'):
                pos=self.next().pos;e=Try(e,pos=pos)
            else:
                return e

    def field_inits(self) -> List[Tuple[str, Node]]:
        self.expect("SYM", "{")
        fields = []
        while not self.at_sym("}"):
            f = self.ident(); self.expect("SYM", "="); fields.append((f, self.expr()))
            if self.at_sym(","): self.next()
        self.expect("SYM", "}")
        return fields

    def range_header(self):
        """'(' IDENT 'in' expr '..' expr ')'"""
        self.expect("SYM", "(")
        v = self.ident(); self.expect("KW", "in")
        lo = self.add(); self.expect("SYM", ".."); hi = self.add()
        self.expect("SYM", ")")
        return v, lo, hi

    def atom(self) -> Node:
        t = self.tok
        if t.kind == "INT": self.next(); return Num(int(t.text), pos=t.pos)
        if t.kind == "FLOAT": self.next(); return Flt(float(t.text), pos=t.pos)
        if t.kind == "STR": self.next(); return Str(t.text.encode("latin-1"), pos=t.pos)
        if t.kind == "CHAR": self.next(); return Byte(int(t.text), pos=t.pos)
        if t.kind == "KW":
            if t.text == 'match':
                self.next();value=self.expr();self.expect('SYM','{');arms=[]
                while not self.at_sym('}'):
                    variant=self.qualified_ident();names=[]
                    if self.at_sym('('):
                        self.next()
                        while not self.at_sym(')'):
                            names.append(self.ident())
                            if self.at_sym(','):self.next()
                            elif not self.at_sym(')'):self.expect('SYM',')')
                        self.next()
                    self.expect('SYM','=>');body=self.expr();arms.append((variant,names,body))
                    if self.at_sym(','):self.next()
                    elif not self.at_sym('}'):self.expect('SYM','}')
                self.next();return Match(value,arms,pos=t.pos)
            if t.text in ("true", "false"): self.next(); return BoolLit(t.text == "true", pos=t.pos)
            if t.text in ("let","using"):
                self.next(); name = self.ident(); self.expect("SYM", "=")
                val = self.expr(); self.expect("KW", "in"); body = self.expr()
                return (Using if t.text=='using' else Let)(name, val, body, pos=t.pos)
            if t.text == "if":
                self.next(); c = self.expr(); self.expect("KW", "then"); a = self.expr()
                self.expect("KW", "else"); b = self.expr()
                return If(c, a, b, pos=t.pos)
            if t.text in ("sum", "arr"):
                self.next(); v, lo, hi = self.range_header(); body = self.expr()
                cls = Sum if t.text == "sum" else ArrC
                return cls(v, lo, hi, body, pos=t.pos)
            if t.text == "check":
                self.next(); pred = self.expr(); self.expect("KW", "in"); body = self.expr()
                return Check(pred, body, pos=t.pos)
            if t.text == "len":
                self.next(); self.expect("SYM", "("); e = self.expr(); self.expect("SYM", ")")
                return Len(e, pos=t.pos)
            if t.text in ("i64", "f64", "u8", "u16", "i32"):
                self.next(); self.expect("SYM", "("); e = self.expr(); self.expect("SYM", ")")
                return Cast({"i64": I64, "f64": F64, "u8": U8, "u16": U16, "i32": I32}[t.text], e, pos=t.pos)
            if t.text == "loop":
                self.next(); self.expect("SYM", "(")
                names, inits, annots = [], [], []
                while True:
                    names.append(self.ident())
                    ann = None
                    if self.at_sym(":"):                       # loop invariant: name : type{preds}
                        self.next(); ty = self.type_(); ann = (ty, self.preds_block())
                    annots.append(ann)
                    self.expect("SYM", "="); inits.append(self.expr())
                    if self.at_sym(","): self.next(); continue
                    break
                self.expect("SYM", ")")
                self.expect("KW", "while"); cond = self.expr()
                self.expect("KW", "next"); self.expect("SYM", "(")
                nexts = [self.expr()]
                while self.at_sym(","): self.next(); nexts.append(self.expr())
                self.expect("SYM", ")")
                self.expect("KW", "yield"); yld = self.expr()
                if len(nexts) != len(names):
                    raise SyntaxError_("loop: next arity differs from state arity", t.pos)
                return Loop(names, inits, cond, nexts, yld, annots, pos=t.pos)
            raise SyntaxError_(f"unexpected keyword {t.text!r}", t.pos)
        if t.kind == "IDENT":
            name=self.qualified_ident();type_args=()
            if self.at_sym('::') and self.peek().text=='<':self.next();type_args=self.type_arguments()
            if self.at_sym("(") :
                self.next(); args = []
                while not self.at_sym(")"):
                    args.append(self.expr())
                    if self.at_sym(","): self.next()
                self.expect("SYM", ")")
                return Call(name, args, type_args,pos=t.pos)
            if self.at_sym("{") and (name in self.type_names or type_args or '::' in name):
                value=RecLit(name, self.field_inits(), pos=t.pos);value.type_args=type_args;return value
            if type_args:raise SyntaxError_('type arguments require a call or record constructor',t.pos)
            return Var(name, pos=t.pos)
        if t.kind == "SYM" and t.text == "(":
            self.next(); e = self.expr(); self.expect("SYM", ")"); return e
        raise SyntaxError_(f"unexpected token {t.text!r}", t.pos)

def parse(src: str, type_names=()) -> Program:
    return Parser(lex(src), type_names).program()

# ---------------------------------------------------------------- pretty (for diagnostics)
def show(e: Node) -> str:
    if isinstance(e, Num): return str(e.value)
    if isinstance(e, Flt): return repr(e.value)
    if isinstance(e, BoolLit): return "true" if e.value else "false"
    if isinstance(e, Str): return repr(e.value.decode("latin-1"))
    if isinstance(e, Byte): return repr(chr(e.value))
    if isinstance(e, Var): return e.name
    if isinstance(e, Bin): return f"({show(e.left)} {e.op} {show(e.right)})"
    if isinstance(e, Un): return f"{e.op}{show(e.expr)}"
    if isinstance(e, Index): return f"{show(e.arr)}[{show(e.idx)}]"
    if isinstance(e, Call): return f"{e.name}({', '.join(show(a) for a in e.args)})"
    if isinstance(e, Len): return f"len({show(e.expr)})"
    if isinstance(e, Cast): return f"{e.to}({show(e.expr)})"
    if isinstance(e, Let): return f"let {e.name} = {show(e.value)} in …"
    if isinstance(e, If): return f"if {show(e.cond)} then … else …"
    if isinstance(e, Sum): return f"sum({e.var} in {show(e.lo)}..{show(e.hi)}) …"
    if isinstance(e, ArrC): return f"arr({e.var} in {show(e.lo)}..{show(e.hi)}) …"
    if isinstance(e, Loop): return f"loop({', '.join(e.names)}) …"
    if isinstance(e, Check): return f"check {show(e.pred)} in …"
    if isinstance(e, RecLit): return f"{e.tname} {{…}}"
    if isinstance(e, Field): return f"{show(e.expr)}.{e.name}"
    if isinstance(e, With): return f"{show(e.expr)} with {{…}}"
    return type(e).__name__

_CHILD_FIELDS: Dict[type, Tuple[str, ...]] = {}

def children(e: Node) -> List[Node]:
    out = []
    fields = _CHILD_FIELDS.get(type(e))
    if fields is None:
        fields = _CHILD_FIELDS[type(e)] = tuple(f for f in e.__dataclass_fields__ if f not in ("pos", "ty", "hash", "annots"))
    for fld in fields:
        v = getattr(e, fld)
        if isinstance(v, Node): out.append(v)
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, Node): out.append(x)
                elif isinstance(x, tuple) and len(x) == 2 and isinstance(x[1], Node): out.append(x[1])
    if isinstance(e, Loop):
        for a in e.annots or []:
            if a is not None: out.extend(a[1])
    if isinstance(e,Match):out.extend(arm[2] for arm in e.arms)
    return out
