"""Recording-policy rollback must preserve existing attributed text corrections."""
import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.reports import finalize_recording
from tribunal.services.media import correct_transcript
from tests.test_backend_followups import recorded
from tests.test_core_policy_completion import granted_roles


@pytest.mark.django_db(transaction=True)
def test_recording_policy_rollback_retains_attributed_transcript_correction(granted_roles, ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, 'recording-policy-rollback', {'accepted': True, 'name': 'John Smith'})
    app.refresh_from_db()
    recording, _ = recorded(app, people)
    run = finalize_recording(people['admin'], recording.pk)
    m.ProcessingRun.objects.filter(pk=run.pk).update(state='completed')
    original = m.TranscriptRevision.objects.create(recording=recording, run=run, language='en',
        number=1, text='Synthetic provider source for rollback test')
    try:
        MigrationExecutor(connection).migrate([('tribunal', '0050_member_administration')])
        with granted_roles('ctm_app', people['admin'], session=True):
            correction = correct_transcript(people['admin'], original.pk, 'Attributed after rollback', [], 1)
            assert correction.actor_id == people['admin'].pk and correction.number == 2
        assert m.TranscriptRevision.objects.get(pk=original.pk).text == 'Synthetic provider source for rollback test'
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes('tribunal'))
