"""QA-01 synthetic fixtures. Runs as the migration owner (setup only, not under test).

All people are fictional. Reports are created through the backend's own services
(create_request / send_request / complete_request / revise_report / assign_case / close_case).
The reopened case reproduces the exact state written by the appeal-acceptance branch of
tribunal/services/decisions.py (new open 'appeal' proceeding, case reopened); the full
appeal hearing flow itself is outside QA-01 and is not exercised.

Writes record ids and test-issued session cookies to SECRETS_DIR/fixtures.json.
"""

import json
import os
import sys
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qa01_settings")
os.environ["QA01_DB_ROLE"] = "qa_owner"

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.db.models import Max  # noqa: E402
from django.test import Client  # noqa: E402

from qa_env import SECRETS_DIR  # noqa: E402
from tribunal.models import Account, Case, Party, Proceeding, ReportQuestion, Report  # noqa: E402
from tribunal.services.council import assign_case  # noqa: E402
from tribunal.services.decisions import close_case  # noqa: E402
from tribunal.services.reports import complete_request, create_request, revise_report, send_request  # noqa: E402


def person(email, first, last, role="applicant"):
    return Account.objects.create_user(email=email, first_name=first, last_name=last,
                                       role=role, email_verified=True)


people = {
    "thompson": person("m.thompson@qa01.test", "Michael", "Thompson", "member"),
    "wilson": person("d.wilson@qa01.test", "David", "Wilson", "member"),
    "collins": person("a.collins@qa01.test", "Andrew", "Collins", "member"),
    "miller": person("s.miller@qa01.test", "Susan", "Miller", "secretary"),
    "anderson": person("r.anderson@qa01.test", "Robert", "Anderson", "admin"),
    "wright": person("t.wright@qa01.test", "Thomas", "Wright", "president"),
    "emily": person("e.carter@qa01.test", "Emily", "Carter"),
    "laura": person("l.bennett@qa01.test", "Laura", "Bennett"),
}
P = people

for code, wording, foundational in [
    ("QA-NAME", "Please state your full name.", True),
    ("QA-HIST", "Describe how the marriage began.", False),
    ("QA-SEP", "When and why did the separation happen?", False),
    ("QA-PREF", "Is reconciliation being considered?", False),
]:
    ReportQuestion.objects.create(code=code, category="QA-01", wording_en=wording, foundational=foundational)


def new_case(number, manager, applicant):
    case = Case.objects.create(number=number, assigned_member=manager)
    proceeding = Proceeding.objects.create(case=case)
    party = Party.objects.create(case=case, account=applicant, slot="A",
                                 name=f"{applicant.first_name} {applicant.last_name}", participating=True)
    return case, proceeding, party


def interview(author, proceeding, party, title, answers, observations, parent=None):
    req = create_request(author, proceeding.pk, party.pk, "interview", title,
                         ["QA-HIST", "QA-SEP", "QA-PREF"], parent_id=parent.pk if parent else None)
    send_request(author, req.pk)
    return complete_request(author, req.pk, answers, observations)


def answers(tag):
    # Text answers plus non-text values the editor must carry over unchanged.
    return {
        "QA-NAME": f"Emily Carter ({tag})",
        "QA-HIST": f"Original history narrative ({tag}).",
        "QA-SEP": f"Original separation narrative ({tag}).",
        "QA-PREF": {"choice": "no", "noted_by": "council"},
        "QA-SCORE": 3,
    }


case_a, proc_a, party_a = new_case("20261021-41", P["thompson"], P["emily"])
r = {}
r["a_main"] = interview(P["thompson"], proc_a, party_a, "QA interview: main", answers("main"),
                        "Original observation (main).")
import inspect  # noqa: E402

# Backend bb3e48b made expected_version a required keyword; db6dfa3 had no such parameter.
_versioned = "expected_version" in inspect.signature(revise_report).parameters
revise_report(P["thompson"], r["a_main"].pk, {**answers("main"), "QA-HIST": "Second history narrative (main)."},
              "Second observation (main).", **({"expected_version": 1} if _versioned else {}))
r["a_unchanged"] = interview(P["thompson"], proc_a, party_a, "QA interview: unchanged", answers("unchanged"), "Obs (unchanged).")
r["a_conflict"] = interview(P["thompson"], proc_a, party_a, "QA interview: conflict", answers("conflict"), "Obs (conflict).")
r["a_lost"] = interview(P["thompson"], proc_a, party_a, "QA interview: lost ack", answers("lost"), "Obs (lost).")
r["a_ui"] = interview(P["thompson"], proc_a, party_a, "QA interview: browser", answers("ui"), "Obs (ui).")
r["a_secretary"] = interview(P["miller"], proc_a, party_a, "QA interview: secretary-authored", answers("secretary"), "Obs (secretary).")
r["a_followup"] = interview(P["thompson"], proc_a, party_a, "QA follow-up of main", answers("follow-up"), "Obs (follow-up).",
                            parent=r["a_main"])
intake = create_request(P["thompson"], proc_a.pk, party_a.pk, "intake", "QA applicant intake", ["QA-HIST"])
send_request(P["thompson"], intake.pk)
# Applicant completion uses the request version contract; resolve it the same way the API does.
from tribunal.services.request_contracts import request_version  # noqa: E402

intake.refresh_from_db()
r["a_intake"] = complete_request(P["emily"], intake.pk, {"QA-NAME": "Emily Carter", "QA-HIST": "Applicant's own words."},
                                 expected_version=request_version(intake))

# Reassignment: Thompson authored, then the case moves to Collins.
case_c, proc_c, party_c = new_case("20261021-42", P["thompson"], P["laura"])
r["c_main"] = interview(P["thompson"], proc_c, party_c, "QA interview before reassignment", answers("reassign"), "Obs (reassign).")
assign_case(P["miller"], case_c.pk, P["collins"].pk, P["wright"].pk)

# Browser 403: Thompson authored; reassigned during the browser session by the harness.
case_e, proc_e, party_e = new_case("20261021-43", P["thompson"], P["laura"])
r["e_main"] = interview(P["thompson"], proc_e, party_e, "QA interview: mid-edit reassignment", answers("forbidden"), "Obs (forbidden).")

# Closed case (stays closed).
case_d, proc_d, party_d = new_case("20261021-44", P["wilson"], P["laura"])
r["d_main"] = interview(P["wilson"], proc_d, party_d, "QA interview on closed case", answers("closed"), "Obs (closed).")
close_case(P["anderson"], case_d, "case_closed", notify_parties=False)

# Closed then reopened (appeal-acceptance state): old proceeding stays closed.
case_b, proc_b, party_b = new_case("20261021-45", P["wilson"], P["laura"])
r["b_old"] = interview(P["wilson"], proc_b, party_b, "QA interview on original proceeding", answers("reopen"), "Obs (reopen).")
close_case(P["anderson"], case_b, "case_closed", notify_parties=False)
case_b.refresh_from_db()
seq = (case_b.proceedings.aggregate(n=Max("sequence"))["n"] or 0) + 1
proc_b2 = Proceeding.objects.create(case=case_b, kind="appeal", sequence=seq)
case_b.status, case_b.closed_at = "open", None
case_b.save(update_fields=["status", "closed_at"])


def cookie(account):
    client = Client()
    client.force_login(account, backend="allauth.account.auth_backends.AuthenticationBackend")
    return client.cookies[settings.SESSION_COOKIE_NAME].value


out = {
    "people": {k: {"id": str(v.pk), "role": v.role, "name": f"{v.first_name} {v.last_name}"} for k, v in P.items()},
    "cookies": {**{k: cookie(v) for k, v in P.items()}, "thompson_2": cookie(P["thompson"])},
    "cases": {"a": str(case_a.pk), "b": str(case_b.pk), "c": str(case_c.pk), "d": str(case_d.pk), "e": str(case_e.pk)},
    "proceedings": {"a": str(proc_a.pk), "b_old": str(proc_b.pk), "b_new": str(proc_b2.pk), "c": str(proc_c.pk),
                    "d": str(proc_d.pk), "e": str(proc_e.pk)},
    "parties": {"a": str(party_a.pk), "b": str(party_b.pk), "c": str(party_c.pk)},
    "reports": {k: str(v.pk) for k, v in r.items()},
    "case_numbers": {"a": case_a.number, "b": case_b.number, "c": case_c.number, "d": case_d.number, "e": case_e.number},
}
(SECRETS_DIR / "fixtures.json").write_text(json.dumps(out, indent=2))
print("Seeded", len(r), "reports across", len(out["cases"]), "cases;",
      Report.objects.count(), "reports total. Fixture ids/cookies stored outside the repository.")
