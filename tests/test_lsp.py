import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from neoc.lsp import Server,offset,position


class Editor(unittest.TestCase):
    def test_utf16_offsets(self):
        text='; 🚀\nfn main() -> i64 = 1\n'
        self.assertEqual(offset(text,{'line':0,'character':4}),3)
        self.assertEqual(position(text,0,3),{'line':0,'character':4})

    def test_overlay_diagnostics_completion_hover_and_definition(self):
        messages=[];s=Server(messages.append)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);lib=p/'lib.neo';lib.write_text('fn answer() -> i64 = 42\n')
            main=p/'main.neo';main.write_text('fn main() -> i64 = 0\n');uri=main.as_uri()
            text='import "lib.neo" as m\nfn main() -> i64 = m::answer()\n'
            s.handle({'method':'textDocument/didOpen','params':{'textDocument':{'uri':uri,'version':1,'text':text}}})
            self.assertEqual(messages[-1]['params']['diagnostics'],[])
            params={'textDocument':{'uri':uri},'position':{'line':1,'character':25}}
            labels=[i['label'] for i in s.handle({'id':1,'method':'textDocument/completion','params':params})]
            self.assertIn('m::answer',labels)
            self.assertIn('answer',s.handle({'id':2,'method':'textDocument/hover','params':params})['contents']['value'])
            self.assertEqual(s.handle({'id':3,'method':'textDocument/definition','params':params})['uri'],lib.resolve().as_uri())
            s.handle({'method':'textDocument/didChange','params':{'textDocument':{'uri':uri,'version':2},'contentChanges':[{'text':'fn main() -> i64 = true'}]}})
            self.assertTrue(messages[-1]['params']['diagnostics'])
            self.assertEqual(main.read_text(),'fn main() -> i64 = 0\n')

    def test_stdio_protocol_keeps_stdout_clean(self):
        requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{}},{'jsonrpc':'2.0','id':2,'method':'shutdown'},{'jsonrpc':'2.0','method':'exit'}]
        data=b''
        for request in requests:
            body=json.dumps(request).encode();data+=b'Content-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body
        result=subprocess.run([sys.executable,'-m','neoc','lsp'],input=data,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        output=result.stdout;replies=[]
        while output:
            header,output=output.split(b'\r\n\r\n',1);n=int(header.split(b':')[1]);replies.append(json.loads(output[:n]));output=output[n:]
        self.assertEqual([r['id'] for r in replies],[1,2])
        self.assertTrue(replies[0]['result']['capabilities']['definitionProvider'])

    def test_first_open_completion_survives_unfinished_expression(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'lib.neo').write_text('fn answer() -> i64 = 42')
            file=root/'main.neo';text='import "lib.neo" as m\nfn main() -> i64 = m::';s=Server(lambda message:None)
            s.handle({'method':'textDocument/didOpen','params':{'textDocument':{'uri':file.as_uri(),'version':1,'text':text}}})
            result=s.handle({'id':1,'method':'textDocument/completion','params':{'textDocument':{'uri':file.as_uri()},'position':{'line':1,'character':len(text.splitlines()[1])}}})
            self.assertIn('m::answer',[item['label'] for item in result])


if __name__=='__main__':unittest.main()
