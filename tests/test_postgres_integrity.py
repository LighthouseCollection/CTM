from concurrent.futures import ThreadPoolExecutor
from datetime import date
import pytest
from django.db import connection, connections, IntegrityError, transaction
from tribunal.models import Account, Application, AnswerRevision, OpenCaseClaim, Case


@pytest.mark.django_db(transaction=True)
def test_concurrent_case_allocation_postgres():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL transaction test")
    from tribunal.services.applications import allocate_case_number

    def allocate(_):
        try:
            return allocate_case_number()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=4) as pool:
        numbers = list(pool.map(allocate, range(8)))
    assert len(set(numbers)) == 8


@pytest.mark.django_db
def test_database_blocks_queryset_overwrite():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL immutable-row trigger")
    user = Account.objects.create_user(email="history@example.test")
    app = Application.objects.create(owner=user)
    revision = AnswerRevision.objects.create(
        application=app, actor=user, number=1, answers={"original": True}
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AnswerRevision.objects.filter(pk=revision.pk).update(
                answers={"overwritten": True}
            )
    revision.refresh_from_db()
    assert revision.answers == {"original": True}


@pytest.mark.django_db
def test_database_rejects_second_open_case_claim():
    user = Account.objects.create_user(email="claim@example.test")
    first = Case.objects.create(number="first")
    second = Case.objects.create(number="second")
    OpenCaseClaim.objects.create(person=user.person, case=first)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            OpenCaseClaim.objects.create(person=user.person, case=second)


@pytest.mark.django_db
def test_database_blocks_new_finding_after_closure(ready_application, people):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL closed-proceeding trigger")
    from tribunal.services.applications import submit_application
    from tribunal.services.decisions import record_decision, approve_decision
    from tribunal.models import FindingRevision

    app = ready_application
    submit_application(
        app.owner, app.pk, "db-closed", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    decision = record_decision(
        people["admin"], app.proceeding_id, "denied", "Reason", {}
    )
    approve_decision(people["president"], decision.pk)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            FindingRevision.objects.create(
                proceeding_id=app.proceeding_id,
                fact_code="closed",
                number=1,
                value={},
                actor=people["admin"],
            )


@pytest.mark.django_db
def test_database_blocks_submitted_answer_deletion(ready_application):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL submitted-history delete trigger")
    from tribunal.services.applications import submit_application

    app = ready_application
    submit_application(
        app.owner, app.pk, "db-delete", {"accepted": True, "name": "John Smith"}
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AnswerRevision.objects.filter(application=app).delete()
