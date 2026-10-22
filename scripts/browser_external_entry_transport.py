"""Disposable localhost-only browser transport check using in-memory test settings."""
import os,sys,threading,uuid,json,argparse
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler
parser=argparse.ArgumentParser(description='Browser redirect/fragment transport only; no form acceptance.')
parser.add_argument('--boot-html',type=Path,default=Path(__file__).resolve().parents[1]/'static/ctm/external-report.html')
args=parser.parse_args()
if not args.boot_html.is_file():
    parser.error('Provide the council-owned external-report.html from the exact tested council commit')
os.environ['DJANGO_SETTINGS_MODULE']='ctm.settings_test' 
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from django.core.wsgi import get_wsgi_application
from playwright.sync_api import sync_playwright
application=get_wsgi_application()
seen=[]
class Quiet(WSGIRequestHandler):
    def log_message(self,*args): pass

def serve(environ,start_response):
    seen.append(environ['PATH_INFO']+('?' + environ['QUERY_STRING'] if environ['QUERY_STRING'] else ''))
    if environ['PATH_INFO']=='/static/ctm/external-report.html':
        content=args.boot_html.read_bytes()
        start_response('200 OK',[('Content-Type','text/html'),('Referrer-Policy','no-referrer')])
        return [content]
    return application(environ,start_response)
server=make_server('localhost',0,serve,handler_class=Quiet)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
request_id=str(uuid.uuid4());token='synthetic-browser-fragment-only'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(java_script_enabled=False)
        page=context.new_page()
        page.goto(f'http://localhost:{server.server_port}/external/reports/{request_id}/#r={request_id}&t={token}')
        assert page.url==f'http://localhost:{server.server_port}/static/ctm/external-report.html#r={request_id}&t={token}'
        assert all(token not in url and '#' not in url for url in seen)
        assert seen[0]==f'/external/reports/{request_id}/'
        assert '/static/ctm/external-report.html' in seen
        browser.close()
    print(json.dumps({'passed':True,'scope':'actual backend browser redirect and fragment transport only; JavaScript disabled; no form/capability acceptance','requests_without_fragment_or_token':len(seen)}))
finally:
    server.shutdown();server.server_close()
