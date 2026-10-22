from datetime import date

import pytest

from tribunal.services.council import activate_session, create_session


pytestmark = pytest.mark.django_db


def test_draft_session_becomes_an_official_in_session_record(people):
    session = create_session(people["admin"], date(2031, 1, 7), state="draft")

    assert session.state == "draft"

    activated = activate_session(people["admin"], session.pk)

    assert activated.state == "planned"
