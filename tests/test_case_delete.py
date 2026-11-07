"""#176 / D-0044: admin, president and secretary can delete a case.

ctm_delete_case(case_id, reason) removes the case and everything that belongs
only to it, and leaves exactly one audit entry: case number, actor, time and
reason, with no case content. Members and applicants are refused.
"""
import hashlib

import pytest
from django.apps import apps
from django.db import DatabaseError, connection

from tribunal import models as m
from tribunal.db.context import database_settings
from tribunal.services.applications import submit_application
from tribunal.services.council import save_note
from tribunal.services.decisions import (approve_decision, attest_signature, cast_vote, issue_decree,
                                         record_decision, release_decree)
from tribunal.services.files import private_path, write_private_original
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db
PDF = b"%PDF-1.4\nSynthetic test signed-original bytes\n%%EOF"


@pytest.fixture
def decided(ready_application, people, settings, tmp_path):
    """A case taken through filing, notes, votes, approval, a signed decree and its release."""
    settings.MEDIA_ROOT = tmp_path
    app = ready_application
    submit_application(app.owner, app.pk, "delete-case", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    save_note(people["admin"], app.proceeding_id, "Synthetic note")
    decision = record_decision(people["admin"], app.proceeding_id, "diss-both", "Recorded grounds",
                               {str(app.party_id): "certificate"})
    cast_vote(people["member"], decision.pk, "approve")
    approve_decision(people["president"], decision.pk)
    attachment = m.Attachment.objects.create(case=app.case, proceeding=app.proceeding, category="DEC", visibility="council")
    file = m.FileVersion.objects.create(attachment=attachment, number=1, object_key="certificates/delete.pdf",
        original_name="signed.pdf", display_name="signed.pdf", mime_type="application/pdf",
        byte_count=len(PDF), sha256=hashlib.sha256(PDF).hexdigest(), actor=people["admin"])
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    write_private_original(private_path(file.object_key), PDF)
    attest_signature(people["president"], file.pk, people["president"].pk, "signed_scan", {"confirmed_signed": True})
    decree = issue_decree(people["admin"], decision.pk, file.pk, people["president"].pk, "en")
    release_decree(people["admin"], decree.pk, app.party_id)
    return app.case


def delete(granted_roles, actor, case_id, reason="Loaded by mistake"):
    with granted_roles("ctm_app", actor), connection.cursor() as cursor:
        cursor.execute("SELECT public.ctm_delete_case(%s, %s)", [str(case_id), reason])


def case_rows(case_id):
    """Every table with a direct case_id column, counted for this case (as owner)."""
    counts = {}
    with connection.cursor() as cursor:
        cursor.execute("""SELECT c.table_name FROM information_schema.columns c
            JOIN information_schema.tables t ON t.table_schema=c.table_schema AND t.table_name=c.table_name
            WHERE c.table_schema='public' AND c.column_name='case_id' AND t.table_type='BASE TABLE'""")
        for (table,) in cursor.fetchall():
            cursor.execute(f'SELECT count(*) FROM public."{table}" WHERE case_id=%s', [str(case_id)])
            counts[table] = cursor.fetchone()[0]
    return {table: n for table, n in counts.items() if n}


@pytest.mark.parametrize("role", ["admin", "president", "secretary"])
def test_admin_president_and_secretary_delete_a_decided_case(granted_roles, people, decided, role):
    case_id, number = decided.pk, decided.number
    assert m.Vote.objects.exists() and m.Decree.objects.exists() and m.NoteRevision.objects.exists()
    delete(granted_roles, people[role], case_id)
    assert not m.Case.objects.filter(pk=case_id).exists()
    assert case_rows(case_id) == {}
    for model in [m.Party, m.Proceeding, m.Application, m.AnswerRevision, m.Attachment, m.FileVersion,
                  m.CaseNote, m.NoteRevision, m.DecisionRevision, m.Vote, m.PresidentialApproval,
                  m.Decree, m.DecreeRelease]:
        assert not model.objects.exists(), model.__name__
    trace = list(m.AuditEvent.objects.filter(action="case_deleted").values("actor_id", "case_id", "source", "source_id", "metadata"))
    assert trace == [{"actor_id": people[role].pk, "case_id": None, "source": "tribunal.case", "source_id": case_id,
                      "metadata": {"case_number": number, "reason": "Loaded by mistake"}}]


@pytest.mark.parametrize("role", ["member", "applicant"])
def test_member_and_applicant_cannot_delete_a_case(granted_roles, people, decided, role):
    with pytest.raises(DatabaseError):
        delete(granted_roles, people[role], decided.pk)
    assert m.Case.objects.filter(pk=decided.pk).exists()
    assert not m.AuditEvent.objects.filter(action="case_deleted").exists()


def test_inactive_admin_cannot_delete_a_case(granted_roles, people, decided):
    m.Account.objects.filter(pk=people["admin"].pk).update(is_active=False)
    with pytest.raises(DatabaseError):
        delete(granted_roles, people["admin"], decided.pk)
    assert m.Case.objects.filter(pk=decided.pk).exists()


def test_reason_is_optional_and_bounded(granted_roles, people, ready_application):
    submit_application(ready_application.owner, ready_application.pk, "delete-reason", {"accepted": True, "name": "John Smith"})
    ready_application.refresh_from_db()
    case_id = ready_application.case_id
    assert case_id
    with pytest.raises(DatabaseError):
        delete(granted_roles, people["admin"], case_id, reason="x" * 501)
    delete(granted_roles, people["admin"], case_id, reason=None)
    assert m.AuditEvent.objects.get(action="case_deleted").metadata["reason"] is None


def test_unknown_case_is_refused(granted_roles, people):
    with pytest.raises(DatabaseError):
        delete(granted_roles, people["admin"], "00000000-0000-4000-8000-000000000176")


def test_history_stays_immutable_outside_the_function(people, decided):
    # The bypass lives only inside ctm_delete_case. Setting the old purge context
    # by hand, even as the table owner with an admin actor, no longer opens the
    # history triggers.
    from django.db import transaction
    from tribunal.db.context import database_actor
    for statement in ["DELETE FROM public.tribunal_vote", "DELETE FROM public.tribunal_answerrevision"]:
        with pytest.raises(DatabaseError), transaction.atomic(), database_actor(people["admin"]), \
                database_settings({"ctm.admin_purge_case": str(decided.pk)}), connection.cursor() as cursor:
            cursor.execute(statement)
    assert m.Vote.objects.exists() and m.AnswerRevision.objects.exists()


def test_every_case_owned_model_is_in_the_delete_function():
    # Guards the dependency list: any model reachable from Case by foreign keys
    # (staying out of accounts, people and sessions) must be deleted by name.
    with connection.cursor() as cursor:
        cursor.execute("SELECT prosrc FROM pg_proc WHERE oid='public.ctm_delete_case(uuid,text)'::regprocedure")
        body = cursor.fetchone()[0]
    models = list(apps.get_app_config("tribunal").get_models())
    owned, changed = {"tribunal_case"}, True
    shared = {"tribunal_account", "tribunal_person", "tribunal_councilsession"}
    while changed:
        changed = False
        for model in models:
            table = model._meta.db_table
            if table in owned or table in shared:
                continue
            if any(f.is_relation and f.many_to_one and f.related_model is not None
                   and f.related_model._meta.db_table in owned for f in model._meta.get_fields()):
                owned.add(table)
                changed = True
    missing = sorted(table for table in owned if f"public.{table} " not in body and f"public.{table}\n" not in body)
    assert missing == []


def test_delete_function_is_executable_only_by_the_app_role():
    with connection.cursor() as cursor:
        cursor.execute("""SELECT coalesce(r.rolname, 'PUBLIC') FROM pg_proc p,
            LATERAL aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) access
            LEFT JOIN pg_roles r ON r.oid = access.grantee
            WHERE p.oid = 'public.ctm_delete_case(uuid,text)'::regprocedure
              AND access.privilege_type = 'EXECUTE' AND access.grantee <> p.proowner""")
        assert [row[0] for row in cursor.fetchall()] == ["ctm_app"]
