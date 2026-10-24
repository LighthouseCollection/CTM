import importlib


def test_current_session_demo_agenda_has_ten_rows_in_each_tab():
    fixture = importlib.import_module(
        "tribunal.migrations.0058_populate_current_session_dummy_agenda"
    )

    assert len(fixture.CURRENT_SESSION_CASES_TO_ASSIGN) == 9
    assert len(fixture.CURRENT_SESSION_HEARINGS) == 9
