"""Isolated VM-only probe. Never reads operational Redis credentials."""
import os
import secrets
import subprocess
from pathlib import Path

root=Path('/opt/ctm-validation')
password=secrets.token_hex(24)
env=root/'broker-test.env'
env.write_text((root/'test.env').read_text()+f'\nREDIS_URL=redis://:{password}@ctm-validation-redis:6379/15\nCTM_TASKS_EAGER=false\nCTM_ISOLATED_VALIDATION=true\nDJANGO_SETTINGS_MODULE=ctm.settings_postgres_test\n')
os.chmod(env,0o600)
redis='ctm-validation-redis'
worker='ctm-validation-worker'
try:
    subprocess.run(['docker','run','-d','--name',redis,'--network','deploy_ctm-internal','redis:7.4-bookworm','redis-server','--requirepass',password,'--appendonly','no'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['docker','run','-d','--name',worker,'--network','deploy_ctm-internal','--env-file',str(env),'ctm-application:validation','celery','-A','ctm','worker','--pool=solo','--concurrency=1','--queues=default','--loglevel=WARNING'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['docker','run','--rm','--network','deploy_ctm-internal','--env-file',str(env),'ctm-application:validation','python','manage.py','smoke_worker'],check=True)
finally:
    for name in [worker,redis]:
        subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    env.unlink(missing_ok=True)
