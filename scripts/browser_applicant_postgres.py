"""Disposable PostgreSQL applicant HTTP acceptance; never reuses an existing service."""
import hashlib,io,json,os,secrets,signal,subprocess,sys,tarfile,time,uuid
from pathlib import Path
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1]
BACKEND=subprocess.check_output(['git','rev-parse',os.environ.get('CTM_APPLICANT_PG_REF','9b7abce1079370add53ccbfb47a42631e158fff2')],cwd=ROOT,text=True).strip()
INTEGRATED=os.environ.get('CTM_APPLICANT_PG_INTEGRATED')=='true'
PREFIX=os.environ.get('CTM_APPLICANT_PG_EVIDENCE','postgres-recovered')
assert PREFIX.replace('-','').isalnum()
FRONTEND=BACKEND if INTEGRATED else '83e537d'
pending=subprocess.check_output(['docker','ps','--filter','label=ctm.applicant.acceptance','--format','{{.Names}}'],text=True,timeout=10).strip()
if pending:raise RuntimeError('An earlier applicant test container still needs cleanup; no new container started: '+pending)
identity=uuid.uuid4().hex;name='ctm-applicant-test-'+identity[:12]
target=ROOT/'.tmp'/('applicant-postgres-'+identity);target.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',BACKEND],cwd=ROOT))) as bundle:bundle.extractall(target,filter='data')
# Keep the integrated shared UI/report-version fixes rather than overlay an old backend shell.
paths=['static/ctm','tribunal/templates/tribunal/shell.html']
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',FRONTEND,*paths],cwd=ROOT))) as bundle:bundle.extractall(target,filter='data')
assets={}
for source in (ROOT/'static/ctm').glob('applicant*.js'):
    contents=(target/'static/ctm'/source.name).read_bytes() if INTEGRATED else source.read_bytes()
    if not INTEGRATED:(target/'static/ctm'/source.name).write_bytes(contents)
    assets[source.name]=hashlib.sha256(contents).hexdigest()
patch=(ROOT/'docs/implementation/applicant/linked-petition-integration.patch').read_bytes();patch_path=target/'review-hook.patch';patch_path.write_bytes(patch)
subprocess.run(['git','init','--quiet',str(target)],check=True)
# Current integrated shell already contains the linked-petition hook; no patch applied.
FRONTEND=subprocess.check_output(['git','rev-parse',FRONTEND],cwd=ROOT,text=True).strip()
password=secrets.token_hex(24);app_password=secrets.token_hex(24)
started=False
try:
    started=True  # A timed-out launch may still have created this exact labelled container.
    try:
        launch=subprocess.run(['docker','run','-d','--rm','--name',name,'--label','ctm.applicant.acceptance='+identity,'-p','127.0.0.1::5432','-e','POSTGRES_PASSWORD='+password,'postgres:16'],capture_output=True,text=True,timeout=30)
    except subprocess.TimeoutExpired:
        raise RuntimeError('Disposable PostgreSQL launch timed out; checking owned-container cleanup.') from None
    if launch.returncode:raise RuntimeError('Disposable PostgreSQL start failed: '+launch.stderr)
    started=True
    print('Started isolated applicant PostgreSQL container; existing services untouched.',flush=True)
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        try:probe=subprocess.run(['docker','exec',name,'pg_isready','-U','postgres'],capture_output=True,timeout=3)
        except subprocess.TimeoutExpired:continue
        if probe.returncode==0:break
        time.sleep(.5)
    else:raise RuntimeError('Disposable PostgreSQL did not become ready within30seconds.')
    binding=subprocess.check_output(['docker','port',name,'5432/tcp'],text=True,timeout=5).strip();assert binding.startswith('127.0.0.1:')
    port=int(binding.rsplit(':',1)[1]);owner=f'postgresql://postgres:{password}@127.0.0.1:{port}/postgres';app=f'postgresql://ctm_app:{app_password}@127.0.0.1:{port}/postgres'
    with psycopg.connect(owner,autocommit=True,connect_timeout=10) as connection:
        connection.execute(sql.SQL('CREATE ROLE ctm_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT PASSWORD {}').format(sql.Literal(app_password)))
        connection.execute("ALTER ROLE ctm_app SET statement_timeout='15s'")
        connection.execute("ALTER ROLE ctm_app SET lock_timeout='5s'")
        connection.execute('CREATE ROLE ctm_worker NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT')
    env={**os.environ,'CTM_TEST_BACKEND_SHA':BACKEND,'CTM_APPLICANT_HISTORY_DENIAL_CONTRACT':'hidden404','CTM_APPLICANT_LINKED_ENTRY':'true','CTM_APPLICANT_POSTGRES_OWNER_URL':owner,'CTM_APPLICANT_POSTGRES_APP_URL':app}
    process=subprocess.Popen([sys.executable,str(ROOT/'scripts/browser_applicant_api.py'),'--run',str(target)],cwd=target,env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0,start_new_session=os.name!='nt')
    try:code=process.wait(timeout=180)
    except subprocess.TimeoutExpired:
        if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=15)
        else:os.killpg(process.pid,signal.SIGKILL)
        code=124
    result_file=target/('result.json' if code==0 else 'partial-result.json')
    if result_file.exists():
        data=json.loads(result_file.read_text(encoding='utf-8'))
        if code!=0:data['failure']={'type':data.get('failure',{}).get('type','Failure'),'detail':'See sanitized acceptance report; raw DEBUG response omitted.'}
        data['review_candidate']={'backend':BACKEND,'integrated_frontend':FRONTEND,'applicant_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'module_sha256':assets,'hook_applied':False,'history_denial_contract':'hidden404','published_integration':INTEGRATED}
        destination=ROOT/'docs/implementation/applicant'/(PREFIX+'-result.json' if code==0 else PREFIX+'-interrupted.json')
        destination.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    focused=target/'postgres-focused-result.json'
    if focused.exists():
        data=json.loads(focused.read_text(encoding='utf-8'))
        if data.get('failure'):data['failure']={'type':data['failure'].get('type','Failure'),'detail':'See sanitized acceptance report; raw DEBUG response omitted.'}
        data['review_candidate']={'backend':BACKEND,'integrated_frontend':FRONTEND,'module_sha256':assets,'hook_applied':False,'history_denial_contract':'hidden404','published_integration':INTEGRATED}
        (ROOT/'docs/implementation/applicant'/(PREFIX+'-focused-result.json')).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    if code:raise SystemExit(code)
finally:
    if started:
        cleanup={"container":name,"owner_label":identity,"state":"pending"}
        try:
            inspected=subprocess.run(['docker','inspect','-f','{{index .Config.Labels "ctm.applicant.acceptance"}}',name],capture_output=True,text=True,timeout=10)
            def remaining():
                return subprocess.check_output(['docker','ps','-a','--filter','name=^/'+name+'$','--format','{{.Names}}'],text=True,timeout=5).strip()
            if inspected.returncode:
                if remaining():raise RuntimeError('Cannot verify ownership of existing test container; cleanup refused.')
                cleanup['state']='absent'
            else:
                if inspected.stdout.strip()!=identity:raise RuntimeError('Container ownership mismatch; cleanup refused.')
                stopped=subprocess.run(['docker','stop','-t','5',name],capture_output=True,text=True,timeout=20)
                if stopped.returncode:raise RuntimeError('Owned test-container cleanup failed: '+stopped.stderr)
                if remaining():
                    removed=subprocess.run(['docker','rm',name],capture_output=True,text=True,timeout=10)
                    if removed.returncode or remaining():raise RuntimeError('Owned test container stopped but removal could not be verified.')
                cleanup['state']='removed'
                print('Verified removal of only the owned disposable applicant container.',flush=True)
        except Exception as error:
            cleanup.update(state='blocked',error=type(error).__name__,detail=str(error)[:1000])
            raise
        finally:
            (target/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n',encoding='utf-8')
            (ROOT/'docs/implementation/applicant'/(PREFIX+'-cleanup.json')).write_text(json.dumps(cleanup,indent=2)+'\n',encoding='utf-8')
