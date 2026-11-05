"""D-0021 database proof for a first Microsoft binding (#65, #66).

"An admin already added this member" is proved by an enrolment record that only
the enrolment insert writes, not by audit history. Every refusal looks the same.
"""
import json

import pytest
from django.db import DatabaseError, connection

from tribunal.db.context import database_settings
from tribunal.models import Account, AuditEvent
from tribunal.services.identity import enroll_council
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db

UNIFORM = "Microsoft sign-in cannot be linked to this account"


def provider(email, subject="enrolment-subject", name="microsoft"):
    return {"ctm.provider": name, "ctm.provider_subject": subject, "ctm.provider_emails": json.dumps([email])}


def bind(granted_roles, account, values):
    with granted_roles("ctm_app", session=True), database_settings(values), connection.cursor() as cursor:
        cursor.execute("SELECT public.ctm_bind_microsoft_subject(%s)", [str(account.pk)])


def refusal(granted_roles, account, values):
    with pytest.raises(DatabaseError) as raised:
        bind(granted_roles, account, values)
    account.refresh_from_db()
    assert account.microsoft_subject == ""
    return raised.value.__cause__


def enrolment(account):
    with connection.cursor() as cursor:
        cursor.execute("SELECT email, role, enrolled_by_id, bound_at IS NOT NULL FROM public.ctm_council_enrolment WHERE account_id=%s",
                       [str(account.pk)])
        return cursor.fetchone()


def test_enrolment_insert_records_the_member_and_binding_consumes_it(granted_roles, people):
    account = enroll_council(people["admin"], "Recorded.Member@lacopts.org", "Recorded", "Member", "member")
    assert enrolment(account)[:2] == ("recorded.member@lacopts.org", "member")
    assert enrolment(account)[3] is False
    bind(granted_roles, account, provider("recorded.member@lacopts.org"))
    account.refresh_from_db()
    assert account.microsoft_subject == "enrolment-subject"
    assert enrolment(account)[3] is True


def test_a_forged_enrolment_audit_row_does_not_allow_binding(granted_roles, people):
    # #66: an account created outside the enrolment path, with a hand-made
    # council_enrolled audit row by a real admin, is still refused.
    account = Account.objects.create_user(email="forged.audit@lacopts.org", role="member", first_name="Forged", last_name="Audit")
    AuditEvent.objects.create(actor=people["admin"], action="council_enrolled", source="tribunal.account",
                              source_id=account.pk, metadata={})
    assert enrolment(account) is None
    refusal(granted_roles, account, provider("forged.audit@lacopts.org"))


def test_runtime_role_cannot_read_or_write_enrolment_records(granted_roles, people):
    account = Account.objects.create_user(email="self.enrolled@lacopts.org", role="member", first_name="Self", last_name="Enrolled")
    for sql in ("INSERT INTO public.ctm_council_enrolment(account_id,email,role) VALUES (%s,'self.enrolled@lacopts.org','member')",
                "SELECT count(*) FROM public.ctm_council_enrolment WHERE account_id=%s"):
        with pytest.raises(DatabaseError):
            with granted_roles("ctm_app", session=True), connection.cursor() as cursor:
                cursor.execute(sql, [str(account.pk)])
    with connection.cursor() as cursor:
        cursor.execute("""SELECT c.relrowsecurity, c.relforcerowsecurity,
              (SELECT count(*) FROM aclexplode(coalesce(c.relacl,'{}'::aclitem[])) a WHERE a.grantee<>c.relowner)
            FROM pg_class c WHERE c.oid='public.ctm_council_enrolment'::regclass""")
        assert cursor.fetchone() == (True, True, 0)


def test_binding_needs_the_email_the_admin_enrolled(granted_roles, people):
    account = enroll_council(people["admin"], "enrolled.email@lacopts.org", "Enrolled", "Email", "member")
    with connection.cursor() as cursor:  # owner-only change, as a later data repair would be
        cursor.execute("UPDATE public.tribunal_account SET email='changed.email@lacopts.org' WHERE id=%s", [str(account.pk)])
    refusal(granted_roles, account, provider("changed.email@lacopts.org"))


def test_demoting_the_enrolling_admin_does_not_block_the_member(granted_roles, people):
    enrolling = people["admin"]
    account = enroll_council(enrolling, "kept.member@lacopts.org", "Kept", "Member", "member")
    with connection.cursor() as cursor:
        cursor.execute("UPDATE public.tribunal_account SET role='member' WHERE id=%s", [str(enrolling.pk)])
    bind(granted_roles, account, provider("kept.member@lacopts.org"))
    account.refresh_from_db()
    assert account.microsoft_subject == "enrolment-subject"


SCENARIOS = ["not_microsoft", "empty_subject", "unverified_email", "other_domain", "inactive",
             "not_enrolled", "subject_in_use", "already_consumed", "unknown_account"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_every_refusal_is_the_same_uniform_denial(granted_roles, people, scenario):
    # #65: the service maps one refusal to one normal denial; the database never
    # says which condition failed.
    email = "other.domain@example.test" if scenario == "other_domain" else "uniform.denial@lacopts.org"
    if scenario == "not_enrolled":
        account = Account.objects.create_user(email=email, role="member", first_name="Uniform", last_name="Denial")
    else:
        account = enroll_council(people["admin"], email, "Uniform", "Denial", "member")
    values = provider(email)
    if scenario == "not_microsoft":
        values = provider(email, name="google")
    elif scenario == "empty_subject":
        values = provider(email, subject="")
    elif scenario == "unverified_email":
        values["ctm.provider_emails"] = "[]"
    elif scenario == "inactive":
        with connection.cursor() as cursor:
            cursor.execute("UPDATE public.tribunal_account SET is_active=false WHERE id=%s", [str(account.pk)])
    elif scenario == "subject_in_use":
        holder = people["member"]
        holder.microsoft_subject = "enrolment-subject"
        holder.save(update_fields=["microsoft_subject"])
    elif scenario == "already_consumed":
        with connection.cursor() as cursor:
            cursor.execute("UPDATE public.ctm_council_enrolment SET bound_at=now() WHERE account_id=%s", [str(account.pk)])
    elif scenario == "unknown_account":
        account = Account(pk="00000000-0000-4000-8000-000000000065")
        with pytest.raises(DatabaseError) as raised:
            bind(granted_roles, account, values)
        cause = raised.value.__cause__
        assert (cause.sqlstate, cause.diag.message_primary, cause.diag.message_detail) == ("42501", UNIFORM, None)
        return
    cause = refusal(granted_roles, account, values)
    assert (cause.sqlstate, cause.diag.message_primary, cause.diag.message_detail) == ("42501", UNIFORM, None)
