"""Exercise the shipped council JS payload against the real revision HTTP contract."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from tests.test_authoring_continuation import authored_report, filed, login  # noqa: F401


@pytest.mark.django_db
@pytest.mark.skipif(shutil.which('node') is None, reason='Node required for real council payload integration')
def test_council_revision_payload_binds_version_and_recovers_receipt(client, authored_report, people):
    login(client, people['admin'])
    url = f'/api/reports/{authored_report.pk}/revisions/'
    latest = client.get(url).json()['items'][0]
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const context = {window:{}};
for (const file of ['council.js','council-case.js','council-decree.js','council-media.js'])
  vm.runInNewContext(fs.readFileSync(`static/ctm/${file}`,'utf8'),context);
const c = context.window.CTMCouncil, latest = JSON.parse(fs.readFileSync(0,'utf8'));
const draft = c.revisionDraft({questions:[{code:'AUTHOR-Q'}]},latest);
draft.answers['AUTHOR-Q'] = 'Integrated correction';
process.stdout.write(JSON.stringify(c.revisionPayload(latest,draft)));
"""
    process = subprocess.run(
        [shutil.which('node'), '-e', script], input=json.dumps(latest),
        text=True, capture_output=True, check=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    payload = json.loads(process.stdout)
    first = client.post(url, payload, content_type='application/json')
    assert first.status_code == 201, first.content
    assert first.json()['version'] == latest['version'] + 1
    assert client.post(url, payload, content_type='application/json').json() == first.json()
    conflict = client.post(url, {**payload, 'answers': {'AUTHOR-Q':'Concurrent change'}}, content_type='application/json')
    assert conflict.status_code == 409
    assert authored_report.revisions.count() == 2
