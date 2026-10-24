"""Review candidate: integrated104e4fd plus named applicant module and minimal hook."""
import hashlib,io,json,os,subprocess,sys,tarfile,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REF='104e4fd06c6cde1ae4cdb76ba5f9ab47b8d336fc'
BACKEND=subprocess.check_output(['git','rev-parse',os.environ.get('CTM_APPLICANT_REVIEW_BACKEND',REF)],cwd=ROOT,text=True).strip()
target=ROOT/'.tmp'/('applicant-linked-review-'+uuid.uuid4().hex);target.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',BACKEND],cwd=ROOT))) as bundle:
    bundle.extractall(target,filter='data')
if BACKEND!=REF:
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',REF,'static/ctm','tribunal/templates/tribunal/shell.html'],cwd=ROOT))) as bundle:bundle.extractall(target,filter='data')
editor='static/ctm/applicant.js';editor_bytes=(ROOT/editor).read_bytes();(target/editor).write_bytes(editor_bytes)
module='static/ctm/applicant-appeals.js';patch='docs/implementation/applicant/linked-petition-integration.patch'
module_bytes=(ROOT/module).read_bytes();patch_bytes=(ROOT/patch).read_bytes()
(target/module).write_bytes(module_bytes)
review_patch=target/'review-hook.patch';review_patch.write_bytes(patch_bytes)
subprocess.run(['git','init','--quiet',str(target)],check=True)
subprocess.run(['git','apply',str(review_patch)],cwd=target,check=True)
env={**os.environ,'CTM_TEST_BACKEND_SHA':BACKEND,'CTM_APPLICANT_LINKED_ENTRY':'true'}
run=subprocess.run([sys.executable,str(ROOT/'scripts/browser_applicant_api.py'),'--run',str(target)],cwd=target,env=env)
if run.returncode:raise SystemExit(run.returncode)
data=json.loads((target/'result.json').read_text(encoding='utf-8'))
data['review_candidate']={'base':REF,'backend':BACKEND,'overlaid_editor':editor,'editor_sha256':hashlib.sha256(editor_bytes).hexdigest(),'overlaid_module':module,'module_sha256':hashlib.sha256(module_bytes).hexdigest(),'hook_patch':patch,'hook_sha256':hashlib.sha256(patch_bytes).hexdigest(),'unmodified_integration':False}
(ROOT/'docs/implementation/applicant'/('backend-validation-api-result.json' if BACKEND!=REF else 'linked-petition-api-result.json')).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
