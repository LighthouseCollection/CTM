"""Run 4: returned-correction resubmission (backend fix 48b80c4 / migration 0041) over real HTTP as ctm_app.

Journey per fictional applicant (one without the optional spouse DOB, one with it):
save -> submit -> identical replay -> admin return with instructions -> correction save ->
resubmit (no new signature, no fee) -> identical replay. Then owner-read checks that the first
formal submission, its attestation/actor, the party reference and the case identity are unchanged,
plus cross-applicant and council-write denials. Writes evidence/<run>/returned-results.json.
"""

import copy
import http.client
import json
import secrets
from urllib.parse import urlparse

import psycopg

from qa_env import EVIDENCE, SECRETS_DIR, fixtures, load_env

F = fixtures()
A = json.loads((SECRETS_DIR / "returned.json").read_text())["applicants"]
ENV = load_env()
CHECKS = []


def call(cookie, method, path, payload=None):
    token = secrets.token_hex(16)
    conn = http.client.HTTPConnection("127.0.0.1", 18870, timeout=30)
    headers = {"Cookie": f"sessionid={cookie}; csrftoken={token}", "Accept": "application/json"}
    body = None
    if method != "GET":
        headers.update({"X-CSRFToken": token, "Content-Type": "application/json"})
        body = json.dumps(payload or {})
    conn.request(method, path, body=body, headers=headers)
    res = conn.getresponse()
    raw = res.read()
    conn.close()
    try:
        return res.status, json.loads(raw or b"null")
    except json.JSONDecodeError:
        return res.status, {"non_json": raw[:200].decode("utf-8", "replace")}


def db():
    u = urlparse(ENV["qa_owner"])
    return psycopg.connect(host=u.hostname, port=u.port, user=u.username, password=u.password, dbname=u.path[1:])


def check(label, expected, actual, ok, role):
    CHECKS.append({"scenario": "RC", "check": label, "role": role, "expected": expected, "actual": actual,
                   "result": "PASS" if ok else "FAIL"})
    print(("PASS " if ok else "FAIL ") + f"[RC] {label} :: {actual}", flush=True)


def state(app_id):
    with db() as c:
        app = c.execute("SELECT status, current_version, case_id::text, party_id::text FROM tribunal_application WHERE id=%s",
                        [app_id]).fetchone()
        subs = c.execute("SELECT s.id::text, r.answers, s.manifest, s.attestation, s.actor_id::text FROM tribunal_submission s "
                         "JOIN tribunal_answerrevision r ON r.id=s.revision_id WHERE s.application_id=%s ORDER BY s.created_at",
                         [app_id]).fetchall()
        party = c.execute("SELECT reference FROM tribunal_party WHERE id=%s", [app[3]]).fetchone() if app[3] else None
        case = c.execute("SELECT marriage_date::text, spouse_dob_low::text, spouse_dob_high::text, status FROM tribunal_case WHERE id=%s",
                         [app[2]]).fetchone() if app[2] else None
        answers = c.execute("SELECT answers FROM tribunal_answerrevision WHERE application_id=%s AND number=%s",
                            [app_id, app[1]]).fetchone()[0]
    return {"status": app[0], "version": app[1], "case": app[2], "submissions": subs,
            "party_reference": party[0] if party else None, "case_identity": case, "answers": answers}


admin = F["cookies"]["anderson"]
for key, info in A.items():
    role = f"applicant ({'spouse DOB absent' if not info['spouse_birth_date_known'] else 'spouse DOB known'})"
    me, app = info["cookie"], info["application_id"]
    base = state(app)
    original = copy.deepcopy(base["answers"])
    check(f"{key}: precondition spouse_birth_date present={info['spouse_birth_date_known']}",
          "matches setup", f"has_spouse_dob={'spouse_birth_date' in original}",
          ("spouse_birth_date" in original) == info["spouse_birth_date_known"], role)
    st, saved = call(me, "POST", f"/api/applications/{app}/", {"answers": original, "expected_version": base["version"]})
    check(f"{key}: save draft", "201", f"status={st}", st == 201, role)
    version = saved.get("version") if isinstance(saved, dict) else None
    first = {"expected_version": version, "idempotency_key": f"qa01-{key}-first",
             "attestation": {"accepted": True, "name": info["name"]}}
    st, receipt = call(me, "POST", f"/api/applications/{app}/submit/", first)
    check(f"{key}: initial submission", "201", f"status={st} body={str(receipt)[:160]}", st == 201, role)
    st2, replay = call(me, "POST", f"/api/applications/{app}/submit/", first)
    check(f"{key}: identical submission replay returns the same receipt", "same JSON, no second submission",
          f"status={st2} same={replay == receipt} submissions={len(state(app)['submissions'])}",
          replay == receipt and len(state(app)["submissions"]) == 1, role)
    frozen = state(app)
    # Council member (not admin/secretary) cannot return the application.
    st, _ = call(F["cookies"]["wilson"], "POST", f"/api/applications/{app}/review/",
                 {"result": "reject", "instructions": "Member attempt"})
    check(f"{key}: council member cannot return a filing", "403/404", f"status={st}", st in (403, 404), "member")
    st, ret = call(admin, "POST", f"/api/applications/{app}/review/",
                   {"result": "reject", "instructions": "QA-01 run 4: please correct your first name."})
    check(f"{key}: admin returns the filing with instructions", "201", f"status={st} status_now={state(app)['status']}",
          st == 201 and state(app)["status"] == "returned", "admin")
    corrected = {**original, "first_name": info["name"].split()[0] + " (corrected)"}
    st, save2 = call(me, "POST", f"/api/applications/{app}/", {"answers": corrected, "expected_version": version})
    check(f"{key}: returned correction saved", "201", f"status={st} body={str(save2)[:160]}", st == 201, role)
    other = [v for k, v in A.items() if k != key][0]
    st, _ = call(other["cookie"], "POST", f"/api/applications/{app}/",
                 {"answers": {**corrected, "statement": "foreign edit"}, "expected_version": save2.get("version") if isinstance(save2, dict) else 0})
    check(f"{key}: another applicant cannot edit this returned filing", "403/404", f"status={st}", st in (403, 404), "other applicant")
    st, peek = call(other["cookie"], "GET", f"/api/applications/{app}/")
    check(f"{key}: another applicant cannot read this filing", "403/404", f"status={st}", st in (403, 404), "other applicant")
    resubmit = {"expected_version": save2.get("version") if isinstance(save2, dict) else None, "idempotency_key": f"qa01-{key}-resubmit"}
    st, receipt2 = call(me, "POST", f"/api/applications/{app}/submit/", resubmit)
    check(f"{key}: corrected resubmission accepted without new signature or fee", "201",
          f"status={st} body={str(receipt2)[:200]}", st == 201, role)
    st2, replay2 = call(me, "POST", f"/api/applications/{app}/submit/", resubmit)
    check(f"{key}: resubmission replay returns the same receipt", "same JSON", f"status={st2} same={replay2 == receipt2}",
          replay2 == receipt2, role)
    after = state(app)
    check(f"{key}: application is submitted with exactly two formal submissions", "submitted, 2",
          f"status={after['status']} submissions={len(after['submissions'])}",
          after["status"] == "submitted" and len(after["submissions"]) == 2, role)
    if after["submissions"] and frozen["submissions"]:
        same_first = after["submissions"][0][1:] == frozen["submissions"][0][1:]
        check(f"{key}: first formal submission (answers, manifest, attestation, actor) unchanged", "identical",
              f"identical={same_first}", same_first, "database (owner read)")
        check(f"{key}: second submission holds the corrected answers", "first_name corrected",
              f"first_name={after['submissions'][-1][1].get('first_name')!r}",
              after["submissions"][-1][1] == corrected, "database (owner read)")
    check(f"{key}: party reference and case identity preserved", "unchanged",
          f"reference_same={after['party_reference'] == frozen['party_reference']} case={after['case_identity']}",
          after["party_reference"] == frozen["party_reference"] and after["case_identity"] == frozen["case_identity"],
          "database (owner read)")
    st, mine = call(me, "GET", f"/api/applications/{app}/")
    check(f"{key}: applicant reads own resubmitted filing", "200", f"status={st}", st == 200, role)

summary = {"pass": sum(c["result"] == "PASS" for c in CHECKS), "fail": sum(c["result"] == "FAIL" for c in CHECKS)}
(EVIDENCE / "returned-results.json").write_text(
    json.dumps({"summary": summary, "checks": CHECKS}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(summary))
