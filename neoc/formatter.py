"""Token-preserving spacing. Deliberate line breaks and comment text survive."""
import re
from . import syntax as S

TOKEN=re.compile(r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[;\#][^\n]*|[^\W\d]\w*|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\.\.\.|::|=>|->|\.\.|==|!=|<=|>=|&&|\|\||\S)''')


def formatted(source):
    before=[(t.kind,t.text) for t in S.lex(source)]
    # Multiline literals deliberately retain their byte-for-byte contents.
    if any('\n' in m.group() for m in TOKEN.finditer(source) if m.group()[:1] in ('"',"'")):
        return source
    output=[];blanks=0
    for line in source.splitlines():
        matches=list(TOKEN.finditer(line));tokens=[m.group() for m in matches]
        if not tokens:
            blanks+=1
            if blanks<=2:output.append('')
            continue
        blanks=0;indent=len(line)-len(line.lstrip(' \t'));prefix=line[:indent].expandtabs(2)
        indent=' '*((len(prefix)+1)//2*2);generic=set();stack=[]
        for i,t in enumerate(tokens):
            if t=='<' and i and matches[i-1].end()==matches[i].start() and (tokens[i-1]=='::' or tokens[i-1][-1:].isalnum()):stack.append(i)
            elif t=='>' and stack:generic.update((stack.pop(),i))
        result='';unary=False
        for i,t in enumerate(tokens):
            previous=tokens[i-1] if i else '';space=bool(result)
            if t.startswith((';','#')):
                result+=('  ' if result else '')+t.rstrip();break
            if t in (')',']',',','.',':','::','?') or previous in ('(','[','.','::'):space=False
            if t=='(' and previous and (previous[-1:].isalnum() or previous in (')',']','>')) and previous not in ('loop','sum','arr','effect'):space=False
            if t=='[':space=False
            if i in generic and t=='<':space=False
            if i in generic and t=='>':space=False
            if i-1 in generic and previous=='<':space=False
            if unary:space=False
            result+=(' ' if space else '')+t
            unary=t=='!' or t=='-' and (not previous or previous in ('(',',','=','=>','then','else','in','+','-','*','/','%','&&','||'))
        output.append(indent+result)
    result='\n'.join(output).rstrip()+'\n'
    # A missing lexical case must never rewrite the meaning of a program.
    after=[(t.kind,t.text) for t in S.lex(result)]
    return result if before==after else source
