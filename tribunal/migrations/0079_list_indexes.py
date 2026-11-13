"""Indexes for server-paged lists (#368, T1 of #312, design section 3).

Indexes only: no table, column, row, grant or policy changes. Built with
AddIndexConcurrently (atomic = False) so reads and writes continue while they
build; the audit table is the largest. Party(case, slot) is already a unique
constraint, so it gets no new index.

Backup: take the usual pre-deploy backup (deploy.yml does). Recovery: the
reverse drops the four indexes (RemoveIndexConcurrently), which loses no data.
Previous build: runs unchanged on the new schema, because indexes add no
columns and change no query result. If a concurrent build is interrupted it
leaves an INVALID index; drop it by name and re-run the migration.
"""
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [("tribunal", "0078_draft_session_cancel")]

    operations = [
        AddIndexConcurrently("auditevent", models.Index(fields=["-created_at", "-id"], name="audit_created_idx")),
        AddIndexConcurrently("auditevent", models.Index(fields=["case", "-created_at", "-id"], name="audit_case_created_idx")),
        AddIndexConcurrently("case", models.Index(fields=["-created_at", "-id"], name="case_created_idx")),
        AddIndexConcurrently("case", models.Index(fields=["status", "-created_at"], name="case_status_created_idx")),
    ]
