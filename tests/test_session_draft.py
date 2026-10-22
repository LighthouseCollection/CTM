from datetime import date

import pytest

from tribunal.services.council import activate_session, create_session, return_session_to_planned


pytestmark = pytest.mark.django_db


def test_draft_session_becomes_an_official_in_session_record(people):
    session = create_session(people["admin"], date(2031, 1, 7), state="draft")

    assert session.state == "draft"

    activated = activate_session(people["admin"], session.pk)

    assert activated.state == "planned"


def test_in_progress_session_can_return_to_planned_before_adjournment(people):
    session = create_session(people["admin"], date(2031, 1, 7), state="draft")
    activate_session(people["admin"], session.pk)

    planned = return_session_to_planned(people["admin"], session.pk)

    assert planned.state == "draft"
