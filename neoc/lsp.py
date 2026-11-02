"""Small stdio Language Server Protocol implementation; build-time Python only.

Full-document synchronization, type diagnostics, qualified completion, hover,
definitions, document symbols and token-preserving formatting. All offsets on
the wire are UTF-16, including documents containing non-BMP characters.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from . import syntax as S
from .modules import sources, SourceError
from .check import Checker, CheckError
from .elaborate import ElaborationError
from .packages import VERSION


def path(uri):
    parsed=urlparse(uri)
    if parsed.scheme!='file' or parsed.netloc not in ('','localhost'):raise ValueError('LSP supports local file URIs')
    return str(Path(unquote(parsed.path)).resolve())


def position(text,line,column):
    lines=text.split('\n');line=max(0,min(line,len(lines)-1));prefix=lines[line][:max(0,column)]
    return {'line':line,'character':len(prefix.encode('utf-16-le'))//2}


def offset(text,p):
    lines=text.splitlines(keepends=True) or [''];line=max(0,min(p['line'],len(lines)-1));units=0;column=0
    for char in lines[line]:
        step=2 if ord(char)>65535 else 1
        if units+step>p['character']:break
        units+=step;column+=1
    return sum(map(len,lines[:line]))+column


class Server:
    def __init__(self,send):self.send=send;self.documents={};self.index={};self.document_index={};self.scopes={};self.stopped=False

    def notify(self,method,params):self.send({'jsonrpc':'2.0','method':method,'params':params})

    def catalog(self,program,source,imports_only=False):
        index={}
        for declaration in program.types+program.fns:
            if imports_only and declaration.source==source:continue
            name=getattr(declaration,'display_name',declaration.name)
            label=('fn '+name+'('+', '.join(q.name+': '+str(q.ty) for q in declaration.params)+') -> '+str(declaration.ret)) if isinstance(declaration,S.Fn) else ('type '+name)
            index[declaration.name]={'label':label,'name':name,'source':declaration.source,'pos':declaration.pos,'kind':3 if isinstance(declaration,S.Fn) else 22}
        self.index=index;self.document_index[source]=index
        self.scopes[source]={name:value for name,value in program.entry_scope.items() if not imports_only or name!='main'}

    def analyze(self,uri):
        source=path(uri);text=self.documents[source]['text'];diagnostics=[]
        try:
            from .cli import RUNTIME, target_triple
            target=target_triple();platform='linux' if 'linux' in target else 'macos'
            binding='linux_x86_64' if platform=='linux' and target.startswith('x86_64') else platform
            runtime=['core.neo','platform_'+binding+'.neo','http.neo','handles.neo']+(['http_linux.neo','http_uring.neo'] if platform=='linux' else [])
            p=sources(source,[Path(RUNTIME)/name for name in runtime],overlays={p:d['text'] for p,d in self.documents.items()})
            self.catalog(p,source)
            checker=Checker(p,require_main=False);checker.run()
            errors=[{'file':source,'pos':o.get('pos',(1,1)),'kind':'unproven','msg':'unproven '+str(o.get('goal','obligation'))} for o in checker.obligations if o['status'] in ('unknown','unproven')]
        except SourceError as ex:
            errors=[ex.diagnostic]
            # An unfinished expression must not prevent first-open imported
            # completion. Parse just the complete import declarations.
            try:
                tokens=S.lex(text);imports=[]
                for i,token in enumerate(tokens[:-1]):
                    if token.text!='import' or token.kind!='KW' or tokens[i+1].kind!='STR':continue
                    name=tokens[i+1].text.encode('latin-1').decode('utf-8')
                    alias=' as '+tokens[i+3].text if i+3<len(tokens) and tokens[i+2].text=='as' and tokens[i+3].kind=='IDENT' else ''
                    imports.append('import '+json.dumps(name,ensure_ascii=False)+alias)
                overlay={p:d['text'] for p,d in self.documents.items()};overlay[source]='\n'.join(imports)+'\nfn main() -> i64 = 0\n'
                self.catalog(sources(source,[Path(RUNTIME)/name for name in runtime],overlays=overlay),source,imports_only=True)
            except (SourceError,S.SyntaxError_,ValueError,RecursionError):pass
        except (CheckError,ElaborationError) as ex:errors=ex.errors
        except RecursionError:errors=[{'file':source,'pos':(1,1),'kind':'limit','msg':'source nesting exceeds compiler limit'}]
        for e in errors:
            location=e.get('file',source) or source
            target=self.documents.get(location,{}).get('text',text)
            line,col=e.get('pos',(1,1));start=position(target,line-1,col-1);end=position(target,line-1,col)
            message=e.get('msg','check failed')
            if location!=source:message=location+': '+message;start={'line':0,'character':0};end=start
            diagnostics.append({'range':{'start':start,'end':end},'severity':1,'code':e.get('kind','check'),'source':'neo','message':message})
        self.notify('textDocument/publishDiagnostics',{'uri':uri,'version':self.documents[source]['version'],'diagnostics':diagnostics})

    def refresh(self):
        for source in list(self.documents):self.analyze(Path(source).as_uri())

    def handle(self,message):
        method=message.get('method');params=message.get('params',{});result=None
        if method=='initialize':
            return {'capabilities':{'positionEncoding':'utf-16','textDocumentSync':1,'completionProvider':{'triggerCharacters':[':']},'hoverProvider':True,'definitionProvider':True,'documentSymbolProvider':True,'documentFormattingProvider':True},'serverInfo':{'name':'neo','version':VERSION}}
        if method=='shutdown':self.stopped=True;return None
        if method=='exit':raise SystemExit(0 if self.stopped else 1)
        if method in ('initialized','$/cancelRequest','workspace/didChangeConfiguration'):return None
        if method=='textDocument/didOpen':
            d=params['textDocument'];self.documents[path(d['uri'])]={'text':d['text'],'version':d.get('version',0)};self.refresh();return None
        if method=='textDocument/didChange':
            d=params['textDocument'];key=path(d['uri'])
            if key not in self.documents:return None
            if d.get('version',0)<=self.documents[key]['version']:return None
            if any('range' in change for change in params['contentChanges']):raise ValueError('full-document synchronization required')
            for change in params['contentChanges']:self.documents[key]={'text':change['text'],'version':d['version']}
            self.refresh();return None
        if method=='textDocument/didClose':
            uri=params['textDocument']['uri'];self.documents.pop(path(uri),None);self.scopes.pop(path(uri),None)
            self.document_index.pop(path(uri),None)
            self.notify('textDocument/publishDiagnostics',{'uri':uri,'diagnostics':[]});self.refresh();return None
        if method.startswith('textDocument/'):
            key=path(params['textDocument']['uri']);text=self.documents.get(key,{}).get('text','');scope=self.scopes.get(key,{})
            catalog=self.document_index.get(key,{})
            index=offset(text,params.get('position',{'line':0,'character':0}));before=text[:index]
            prefix=re.search(r'[A-Za-z_][A-Za-z0-9_:]*$',before);prefix=prefix.group() if prefix else ''
            if method=='textDocument/completion':
                words=set(scope)|{'fn','type','enum','match','let','in','check','if','then','else','loop','while','next','yield','effect','move','import','private','pub','i64','f64','u8','u16','i32','bool','Arr'}
                # Keep completion usable during a parse error or the first edit.
                try:words.update(t.text for t in S.lex(text) if t.kind=='IDENT')
                except S.SyntaxError_:pass
                return [{'label':name,'kind':catalog.get(scope.get(name),{}).get('kind',14),'detail':catalog.get(scope.get(name),{}).get('label','Neo')} for name in sorted(words) if name.startswith(prefix)]
            if method in ('textDocument/hover','textDocument/definition'):
                after=re.match(r'[A-Za-z0-9_:]*',text[index:]).group();name=prefix+after;item=catalog.get(scope.get(name))
                if not item:return None
                if method.endswith('hover'):return {'contents':{'kind':'markdown','value':'```neo\n'+item['label']+'\n```'}}
                target=Path(item['source']);target_text=self.documents.get(str(target),{}).get('text')
                if target_text is None:target_text=target.read_text()
                line,col=item['pos'];p=position(target_text,line-1,col-1)
                return {'uri':target.as_uri(),'range':{'start':p,'end':p}}
            if method=='textDocument/documentSymbol':
                items=[]
                for item in catalog.values():
                    if item['source']!=key:continue
                    line,col=item['pos'];p=position(text,line-1,col-1);r={'start':p,'end':p}
                    items.append({'name':item['name'],'kind':12 if item['kind']==3 else 23,'range':r,'selectionRange':r})
                return items
            if method=='textDocument/formatting':
                from .project import formatted
                try:out=formatted(text)
                except S.SyntaxError_:return []
                return [] if out==text else [{'range':{'start':{'line':0,'character':0},'end':position(text,len(text.split('\n'))-1,len(text.split('\n')[-1]))},'newText':out}]
        if 'id' in message:raise LookupError('method not supported: '+str(method))
        return result


def command(args):
    inp=sys.stdin.buffer;out=sys.stdout.buffer
    def send(value):
        data=json.dumps(value,ensure_ascii=False).encode();out.write(b'Content-Length: '+str(len(data)).encode()+b'\r\n\r\n'+data);out.flush()
    server=Server(send)
    while True:
        length=None
        while True:
            line=inp.readline(1025)
            if not line:return
            if len(line)>1024:print('neo lsp: oversized header',file=sys.stderr);return
            if line in (b'\r\n',b'\n'):break
            name,separator,value=line.partition(b':')
            if name.lower()==b'content-length' and separator:
                try:
                    if length is not None:raise ValueError('duplicate length')
                    length=int(value)
                except ValueError:print('neo lsp: invalid Content-Length',file=sys.stderr);return
        if length is None or not 0<=length<=8*1024*1024:print('neo lsp: invalid Content-Length',file=sys.stderr);return
        data=inp.read(length)
        if len(data)!=length:return
        try:message=json.loads(data)
        except ValueError:
            send({'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'invalid JSON'}});continue
        if not isinstance(message,dict) or message.get('jsonrpc')!='2.0' or not isinstance(message.get('method'),str):
            send({'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'invalid request'}});continue
        try:result=server.handle(message)
        except SystemExit:raise
        except (ValueError,LookupError,OSError,TypeError) as ex:
            if 'id' in message:send({'jsonrpc':'2.0','id':message['id'],'error':{'code':-32601 if isinstance(ex,LookupError) and not isinstance(ex,KeyError) else -32602,'message':str(ex)}})
            else:server.notify('window/logMessage',{'type':1,'message':str(ex)})
            continue
        if 'id' in message:send({'jsonrpc':'2.0','id':message['id'],'result':result})
