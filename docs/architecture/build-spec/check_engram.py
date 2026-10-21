"""Read-only MCP handshake/project discovery; writes only a verification report."""
import json
import os
import queue
import subprocess
import threading
from pathlib import Path

ROOT=Path(__file__).resolve().parent
exe=Path(os.environ['LOCALAPPDATA'])/'Programs/Engram/3.5.1/engram.exe'
proc=subprocess.Popen([str(exe),'mcp','--tools=agent'],cwd=ROOT.parents[2],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8')
lines=queue.Queue()


def read():
    for line in proc.stdout:
        lines.put(line)


threading.Thread(target=read,daemon=True).start()


def send(message):
    proc.stdin.write(json.dumps(message)+'\n')
    proc.stdin.flush()


def receive(identifier):
    for _ in range(30):
        try:
            payload=json.loads(lines.get(timeout=1))
        except queue.Empty:
            continue
        if payload.get('id')==identifier:
            assert 'error' not in payload,payload
            return payload['result']
    raise TimeoutError(f'MCP response {identifier} timed out')


try:
    send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'ctm-install-validation','version':'1'}}})
    initialized=receive(1)
    send({'jsonrpc':'2.0','method':'notifications/initialized'})
    send({'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}})
    tools=receive(2)['tools']
    assert any(t['name']=='mem_current_project' for t in tools)
    send({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'mem_current_project','arguments':{}}})
    project=receive(3)
    assert not project.get('isError'),project
    assert 'ctm' in json.dumps(project).lower(),project
    result={'status':'passed','core_version':'3.5.1','mcp_server':initialized.get('serverInfo'),
            'tool_count':len(tools),'current_project_check':'ctm','read_only_handshake':True,
            'memory_writes_tested':False,'desktop_reload_required':True}
    (ROOT/'engram-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
finally:
    proc.stdin.close()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.terminate()
