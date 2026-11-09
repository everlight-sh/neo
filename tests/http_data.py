"""Independent inert-data escaping and attribute-boundary oracle."""
import json,subprocess
from html.parser import HTMLParser
import usability_smoke as smoke

class InertData(HTMLParser):
    def __init__(self):super().__init__();self.tags=[];self.text=[];self.attributes=[]
    def handle_starttag(self,tag,attrs):self.tags.append(tag);self.attributes.append(dict(attrs))
    def handle_data(self,data):self.text.append(data)

def main():
    binary=smoke.build('http-data','tests/fixtures/http_data.neo')
    result=subprocess.run(smoke.RUNNER+[str(binary),'0'],capture_output=True,check=True)
    parser=InertData();parser.feed(result.stdout.decode())
    assert parser.tags==['template'] and parser.attributes==[{'data-web-data':'rows-a_2'}]
    assert json.loads(''.join(parser.text))=={'note':'</template><script>bad()</script> & café "quotes"','count':10000}
    for mode in (1,2,3):
        rejected=subprocess.run(smoke.RUNNER+[str(binary),str(mode)],capture_output=True)
        assert rejected.returncode!=0 and not rejected.stdout
    print('PASS inert native page data: markup/entity/quote round trip and invalid-name rejection')

if __name__=='__main__':main()
