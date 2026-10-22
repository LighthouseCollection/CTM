"""QA-01 HTTP and database checks against the live assembled server (runtime role ctm_app).

Every request goes over real HTTP to 127.0.0.1:18870 with a test-issued session cookie.
Database reads used as evidence go through a separate owner connection (read-only queries).
Section 12 also runs raw SQL as ctm_app to show RLS/trigger enforcement below the API.

Writes evidence/api-results.json. Cookies, CSRF tokens and passwords are never written out.
"""

import http.client
import json
import secrets
import sys
import threading
import time
import uuid
from urllib.parse import urlparse

import psycopg

from qa_env import EVIDENCE, fixtures, load_env

F = fixtures()
ENV = load_env()
HOST, PORT = "127.0.0.1", 18870
CHECKS = []


def name(key):
    return F["people"][key]["name"] if key in F["people"] else key


class Session:
    def __init__(self, who):
        self.who = who
        self.cookie = F["cookies"][who]
        self.csrf = secrets.token_hex(16)  # double-submit token; Django accepts a client-set value

    def call(self, method, path, payload=None):
        conn = http.client.HTTPConnection(HOST, PORT, timeout=30)
        headers = {"Cookie": f"sessionid={self.cookie}; csrftoken={self.csrf}", "Accept": "application/json"}
        body = None
        if method != "GET":
            headers.update({"X-CSRFToken": self.csrf, "Content-Type": "application/json"})
            body = json.dumps(payload or {})
        conn.request(method, path, body=body, headers=headers)
        res = conn.getresponse()
        raw = res.read()
        conn.close()
        try:
            data = json.loads(raw or b"null")
        except json.JSONDecodeError:
            data = {"non_json": raw[:200].decode("utf-8", "replace")}
        return res.status, data


S = {k: Session(k) for k in F["cookies"]}
R = F["reports"]


def owner_db():
    u = urlparse(ENV["qa_owner"])
    return psycopg.connect(host=u.hostname, port=u.port, user=u.username, password=u.password, dbname=u.path[1:])


def runtime_db():
    u = urlparse(ENV["ctm_app"])
    return psycopg.connect(host=u.hostname, port=u.port, user=u.username, password=u.password, dbname=u.path[1:])


def revisions(report):
    with owner_db() as c:
        return c.execute(
            "SELECT number, answers, observations, actor_id::text FROM tribunal_reportrevision "
            "WHERE report_id=%s ORDER BY number", [report]).fetchall()


def audit_count(report_ids, kind="report_revised"):
    with owner_db() as c:
        return c.execute(
            "SELECT count(*) FROM tribunal_auditevent a JOIN tribunal_reportrevision v ON v.id=a.source_id "
            "WHERE a.action=%s AND v.report_id = ANY(%s::uuid[])", [kind, report_ids]).fetchone()[0]


DENY = "denied with no new version (contract: 403 forbidden / 422 read-only)"
DENIAL_STATUSES = []


def denied(status, role):
    DENIAL_STATUSES.append((role, status))
    return status in (403, 404, 422)


def check(scenario, label, expected, actual, ok, role):
    CHECKS.append({"scenario": scenario, "check": label, "role": role, "expected": expected,
                   "actual": actual, "result": "PASS" if ok else "FAIL"})
    print(("PASS " if ok else "FAIL ") + f"[{scenario}] {label} :: {actual}", flush=True)


def row(who, case, report):
    status, data = S[who].call("GET", f"/api/cases/{F['cases'][case]}/reports/")
    if status != 200:
        return status, None
    return status, next((x for x in data["items"] if x["id"] == R[report]), None)


def post_revision(who, report, answers, observations="", **extra):
    """Like a real client: send the newest version it read, unless a test overrides expected_version.

    On db6dfa3 (run 1) the field is ignored by the server; on bb3e48b (run 2) it is required.
    """
    if "expected_version" not in extra:
        extra["expected_version"] = revisions(R[report])[-1][0]
    return S[who].call("POST", f"/api/reports/{R[report]}/revisions/",
                       {"answers": answers, "observations": observations, **extra})


def latest(report):
    rows = revisions(R[report])
    return rows[-1]


# ---------------------------------------------------------------- S1 can_revise / newest content
st, a = row("thompson", "a", "a_main")
check("S1", "author sees literal can_revise true on own open report", "can_revise is True",
      f"status={st} can_revise={a and a.get('can_revise')!r}", st == 200 and a and a.get("can_revise") is True, "member (assigned author)")
check("S1", "row exposes author_id/author", f"author_id={F['people']['thompson']['id']} author=Michael Thompson",
      f"author_id={a.get('author_id')} author={a.get('author')}",
      a.get("author_id") == F["people"]["thompson"]["id"] and a.get("author") == "Michael Thompson", "member (assigned author)")
check("S1", "row carries newest version answers/observations", "version=2, QA-HIST second narrative, observation v2",
      f"version={a.get('version')} QA-HIST={a['answers'].get('QA-HIST')!r} obs={a.get('observations')!r}",
      a.get("version") == 2 and a["answers"].get("QA-HIST") == "Second history narrative (main)." and a.get("observations") == "Second observation (main).",
      "member (assigned author)")
for who, role in [("wilson", "member (unassigned)"), ("miller", "secretary (non-author)"), ("anderson", "admin (non-author)"), ("wright", "president")]:
    st, x = row(who, "a", "a_main")
    check("S1", f"{who} reads row but can_revise is false", "200, can_revise False", f"status={st} can_revise={x and x.get('can_revise')!r}",
          st == 200 and x is not None and x.get("can_revise") is False, role)
st, x = row("thompson", "a", "a_secretary")
check("S1", "assigned manager cannot revise secretary-authored report", "can_revise False", f"can_revise={x and x.get('can_revise')!r}",
      x is not None and x.get("can_revise") is False, "member (assigned, non-author)")
st, x = row("miller", "a", "a_secretary")
check("S1", "secretary author can revise own report", "can_revise True", f"can_revise={x and x.get('can_revise')!r}",
      x is not None and x.get("can_revise") is True, "secretary (author)")

# ---------------------------------------------------------------- S2 successful edit
before = revisions(R["a_main"])
v2 = before[-1][1]
new_answers = {**v2, "QA-SEP": "Revised separation narrative by author (QA-01 S2)."}
audit_before = audit_count([R["a_main"]])
st, data = post_revision("thompson", "a_main", new_answers, "Revised observation (QA-01 S2).")
after = revisions(R["a_main"])
check("S2", "author revision accepted over HTTP", "201", f"status={st}", st == 201, "member (assigned author)")
check("S2", "exactly one new version appended", f"{len(before)}+1 versions", f"{len(after)} versions",
      len(after) == len(before) + 1, "member (assigned author)")
check("S2", "new version attributed to author", F["people"]["thompson"]["id"], after[-1][3],
      after[-1][3] == F["people"]["thompson"]["id"], "member (assigned author)")
check("S2", "prior versions unchanged", "v1,v2 rows identical before/after", "identical" if after[:-1] == before else "CHANGED",
      after[:-1] == before, "member (assigned author)")
check("S2", "non-text answers preserved in new version when sent", "QA-PREF dict and QA-SCORE int unchanged",
      f"QA-PREF={after[-1][1].get('QA-PREF')} QA-SCORE={after[-1][1].get('QA-SCORE')}",
      after[-1][1].get("QA-PREF") == v2["QA-PREF"] and after[-1][1].get("QA-SCORE") == 3, "member (assigned author)")
check("S2", "audit report_revised written atomically", f"{audit_before}+1", str(audit_count([R['a_main']])),
      audit_count([R["a_main"]]) == audit_before + 1, "member (assigned author)")
st, x = row("thompson", "a", "a_main")
check("S2", "reload shows new newest version", "version=3 with revised QA-SEP",
      f"version={x.get('version')} QA-SEP={x['answers'].get('QA-SEP')!r}",
      x.get("version") == 3 and x["answers"].get("QA-SEP", "").startswith("Revised separation"), "member (assigned author)")
st, hist = S["wilson"].call("GET", f"/api/reports/{R['a_main']}/revisions/")
check("S2", "other council member reads full attributed history", "200 with versions 3,2,1 and actor names",
      f"status={st} versions={[h['version'] for h in hist.get('items', [])]} actors={sorted({h['actor'] for h in hist.get('items', [])})}",
      st == 200 and [h["version"] for h in hist["items"]] == [3, 2, 1], "member (unassigned)")
# The council editor's exact request body (council-media.js revisionPayload): answers + observations only.
before = revisions(R["a_main"])
st, data = S["thompson"].call("POST", f"/api/reports/{R['a_main']}/revisions/",
                              {"answers": {**before[-1][1], "QA-HIST": "Editor-shaped body (QA-01 S2)."},
                               "observations": before[-1][2]})
check("S2", "contract: council editor request body (no expected_version) is accepted by this backend",
      "201 (backend and council agree on the write contract)", f"status={st} body={data}",
      st == 201, "member (assigned author)")
# Server-side contract observations (the editor is responsible for carrying values over).
before = revisions(R["a_followup"])
st, _ = post_revision("thompson", "a_followup", {"QA-HIST": "Only one key sent."}, "obs")
after = revisions(R["a_followup"])
check("S2", "OBSERVATION: server keeps prior versions when a partial answer object is posted",
      "prior versions intact; server does not merge, so the new version holds only the posted keys",
      f"status={st} new keys={sorted(after[-1][1].keys()) if len(after) > len(before) else None} prior intact={after[:len(before)] == before}",
      after[:len(before)] == before, "member (assigned author)")
fake_file = str(uuid.uuid4())
st, data = post_revision("thompson", "a_followup", {**after[-1][1], "files": [fake_file]}, "obs")
check("S2", "OBSERVATION: revision answers referencing an unknown file id", "rejected (file references validated like complete_request)",
      f"status={st}", st in (403, 404, 422), "member (assigned author)")

# ---------------------------------------------------------------- S3 unchanged save (API level)
before = revisions(R["a_unchanged"])
st, _ = post_revision("thompson", "a_unchanged", before[-1][1], before[-1][2])
after = revisions(R["a_unchanged"])
check("S3", "server: identical payload does not append a version", "no new version (or explicit no-op)",
      f"status={st} versions {len(before)}->{len(after)}", len(after) == len(before), "member (assigned author)")

# ---------------------------------------------------------------- S4 non-author denial + forged requests
base = revisions(R["a_main"])
for who, role in [("wilson", "member (unassigned)"), ("collins", "member (unassigned)"), ("miller", "secretary (non-author)"),
                  ("anderson", "admin (non-author)"), ("wright", "president (non-author)")]:
    st, data = post_revision(who, "a_main", {**base[-1][1], "QA-HIST": f"forged by {who}"}, "forged")
    check("S4", f"forged POST by {who} denied", DENY, f"status={st} error={data.get('error') if isinstance(data, dict) else data}",
          denied(st, role), role)
st, data = post_revision("thompson", "a_secretary", {"QA-HIST": "forged by manager"}, "forged")
check("S4", "assigned manager forging secretary-authored report denied", DENY, f"status={st}", denied(st, "member (assigned, non-author)"), "member (assigned, non-author)")
st, _ = S["miller"].call("GET", f"/api/reports/{R['a_main']}/revisions/")
check("S4", "read access does not imply write (secretary GET 200, POST 403 above)", "200", f"status={st}", st == 200, "secretary (non-author)")
check("S4", "no version created by any forged request", f"{len(base)} versions", f"{len(revisions(R['a_main']))} versions",
      len(revisions(R["a_main"])) == len(base), "all non-authors")
noauth = http.client.HTTPConnection(HOST, PORT, timeout=10)
noauth.request("POST", f"/api/reports/{R['a_main']}/revisions/", body="{}", headers={"Content-Type": "application/json"})
resp = noauth.getresponse(); resp.read()
check("S4", "unauthenticated POST rejected", "401 or 403 (CSRF)", f"status={resp.status}", resp.status in (401, 403), "anonymous")
nocsrf = http.client.HTTPConnection(HOST, PORT, timeout=10)
nocsrf.request("POST", f"/api/reports/{R['a_main']}/revisions/", body=json.dumps({"answers": {"x": "y"}}),
               headers={"Content-Type": "application/json", "Cookie": f"sessionid={F['cookies']['thompson']}"})
resp = nocsrf.getresponse(); resp.read()
check("S4", "author session without CSRF token rejected", "403", f"status={resp.status}", resp.status == 403, "member (assigned author, cross-site)")

# ---------------------------------------------------------------- S5 applicant / external sources
st, x = row("thompson", "a", "a_intake")
check("S5", "applicant-authored intake: can_revise false for manager", "can_revise False",
      f"can_revise={x and x.get('can_revise')!r} author={x and x.get('author')}", x is not None and x.get("can_revise") is False, "member (assigned)")
base = revisions(R["a_intake"])
for who, role in [("thompson", "member (assigned)"), ("miller", "secretary"), ("anderson", "admin")]:
    st, _ = post_revision(who, "a_intake", {"QA-NAME": "Emily Carter", "QA-HIST": "Council rewrite attempt."}, "council narrative")
    check("S5", f"{who} cannot rewrite applicant-authored intake", DENY, f"status={st}", denied(st, role), role)
st, _ = post_revision("emily", "a_intake", {"QA-NAME": "Emily Carter", "QA-HIST": "Applicant edit via council route."})
check("S5", "applicant cannot call revision endpoint on own intake", DENY, f"status={st}", denied(st, "applicant (author)"), "applicant (author)")
st, _ = post_revision("emily", "a_main", {"QA-HIST": "Applicant edit of council report."})
check("S5", "applicant cannot call revision endpoint on council report", DENY, f"status={st}", denied(st, "applicant"), "applicant")
st, _ = S["emily"].call("GET", f"/api/reports/{R['a_main']}/revisions/")
check("S5", "applicant cannot read council revision history", "403", f"status={st}", st == 403, "applicant")
st, data = S["emily"].call("GET", f"/api/cases/{F['cases']['a']}/reports/")
items = data.get("items", []) if isinstance(data, dict) else []
leak = [i for i in items if "can_revise" in i or i.get("observations") or i["id"] != R["a_intake"]]
check("S5", "applicant list: only own intake, no capability/observations", "1 own item, no can_revise/observations",
      f"status={st} items={len(items)} leaked_fields_or_rows={len(leak)}", st == 200 and len(items) == 1 and not leak, "applicant")
check("S5", "intake history untouched", f"{len(base)} versions", f"{len(revisions(R['a_intake']))}",
      len(revisions(R["a_intake"])) == len(base), "all")

# ---------------------------------------------------------------- S6 closed / reopened
st, x = row("wilson", "d", "d_main")
check("S6", "closed case: author can_revise false", "False", f"can_revise={x and x.get('can_revise')!r}", x is not None and x.get("can_revise") is False, "member (author, closed case)")
base = revisions(R["d_main"])
st, data = post_revision("wilson", "d_main", {**base[-1][1], "QA-HIST": "edit after closure"}, "x")
check("S6", "closed case: author write denied", DENY, f"status={st} {data}", denied(st, "member (author, closed case)"), "member (author, closed case)")
st, data = post_revision("anderson", "d_main", {**base[-1][1], "QA-HIST": "admin edit after closure"}, "x")
check("S6", "closed case: admin write denied", DENY, f"status={st}", denied(st, "admin"), "admin")
st, x = row("wilson", "b", "b_old")
check("S6", "reopened case: original-proceeding report can_revise false", "False", f"can_revise={x and x.get('can_revise')!r}",
      x is not None and x.get("can_revise") is False, "member (author, assigned, reopened case)")
base_b = revisions(R["b_old"])
st, data = post_revision("wilson", "b_old", {**base_b[-1][1], "QA-HIST": "edit after reopening"}, "x")
check("S6", "reopened case: original-proceeding report write denied", DENY, f"status={st} {data}", denied(st, "reopened"),
      "member (author, assigned, reopened case)")
check("S6", "no versions added to closed/old-proceeding reports", "unchanged",
      f"d={len(revisions(R['d_main']))} b={len(revisions(R['b_old']))}",
      len(revisions(R["d_main"])) == len(base) and len(revisions(R["b_old"])) == len(base_b), "all")

# ---------------------------------------------------------------- S7 reassignment + follow-up
for who, role in [("thompson", "member (original author, no longer assigned)"), ("collins", "member (new manager, non-author)")]:
    st, x = row(who, "c", "c_main")
    check("S7", f"{who}: can_revise false after reassignment", "False", f"can_revise={x and x.get('can_revise')!r}",
          x is not None and x.get("can_revise") is False, role)
    base = revisions(R["c_main"])
    st, _ = post_revision(who, "c_main", {**base[-1][1], "QA-HIST": f"{who} after reassignment"}, "x")
    check("S7", f"{who}: revision denied after reassignment", DENY, f"status={st}", denied(st, role), role)
st, created = S["collins"].call("POST", f"/api/cases/{F['cases']['c']}/requests/", {
    "proceeding_id": F["proceedings"]["c"], "party_id": F["parties"]["c"], "kind": "interview",
    "title": "QA follow-up by new manager", "questions": ["QA-HIST"], "parent_id": R["c_main"]})
ok = st == 201
if ok:
    st2, _ = S["collins"].call("POST", f"/api/requests/{created['id']}/send/", {})
    st3, rep = S["collins"].call("POST", f"/api/requests/{created['id']}/complete/",
                                 {"answers": {"QA-NAME": "Laura Bennett", "QA-HIST": "New manager's follow-up."}, "observations": "Follow-up obs."})
    ok = st2 in (200, 201) and st3 in (200, 201)
st, data = S["collins"].call("GET", f"/api/cases/{F['cases']['c']}/reports/")
follow = [i for i in data.get("items", []) if i.get("parent_report_id") == R["c_main"]]
check("S7", "new manager adds follow-up as separate linked report", "new report, parent_report_id=original, own version 1, can_revise True",
      f"created={ok} follow_ups={len(follow)} version={follow and follow[0].get('version')} can_revise={follow and follow[0].get('can_revise')}",
      ok and len(follow) == 1 and follow[0]["id"] != R["c_main"] and follow[0].get("version") == 1 and follow[0].get("can_revise") is True,
      "member (new manager)")
check("S7", "original report untouched by follow-up", "1 version", f"{len(revisions(R['c_main']))}", len(revisions(R["c_main"])) == 1, "all")

# ---------------------------------------------------------------- S8 retry semantics (API level)
base = revisions(R["a_lost"])
payload = {**base[-1][1], "QA-HIST": "Lost-acknowledgement edit (QA-01 S8)."}
st1, r1 = post_revision("thompson", "a_lost", payload, "obs S8", expected_version=base[-1][0])
# Identical resend after an unknown outcome: same body, same expected_version the client started from.
st2, r2 = post_revision("thompson", "a_lost", payload, "obs S8", expected_version=base[-1][0])
after = revisions(R["a_lost"])
check("S8", "server: identical retry after unknown outcome is replay-safe", "second identical POST returns original receipt, no extra version",
      f"statuses={st1},{st2} receipts={r1.get('version') if isinstance(r1, dict) else r1},{r2.get('version') if isinstance(r2, dict) else r2} versions {len(base)}->{len(after)}",
      len(after) == len(base) + 1 and isinstance(r2, dict) and r2.get("id") == r1.get("id"), "member (assigned author)")
st3, r3 = post_revision("thompson", "a_lost", {**payload, "QA-HIST": "Different text replayed on the old base."}, "obs S8",
                        expected_version=base[-1][0])
check("S8", "a different body replayed on the old base is not accepted as a retry", "409 conflict, no extra version",
      f"status={st3} body={r3} versions={len(revisions(R['a_lost']))}", st3 == 409 and len(revisions(R["a_lost"])) == len(base) + 1,
      "member (assigned author)")

# ---------------------------------------------------------------- S9 real concurrent writers
base = revisions(R["a_conflict"])
v1 = base[-1]
barrier = threading.Barrier(2)
results = {}


def writer(key, text):
    barrier.wait()
    results[key] = post_revision(key, "a_conflict", {**v1[1], "QA-HIST": text}, f"obs {key}", expected_version=v1[0])


threads = [threading.Thread(target=writer, args=("thompson", "Session 1 change (QA-01 S9).")),
           threading.Thread(target=writer, args=("thompson_2", "Session 2 change (QA-01 S9)."))]
t0 = time.time()
[t.start() for t in threads]
[t.join() for t in threads]
after = revisions(R["a_conflict"])
statuses = sorted(r[0] for r in results.values())
check("S9", "two sessions save from the same version in parallel: server rejects the stale writer",
      "one 201 and one 409 (stale expected_version), 1 new version",
      f"statuses={statuses} versions {len(base)}->{len(after)} newest QA-HIST={after[-1][1].get('QA-HIST')!r} elapsed={time.time()-t0:.2f}s",
      statuses == [201, 409] and len(after) == len(base) + 1, "member (author, 2 sessions)")
check("S9", "both concurrent writes serialized without corrupting history", "distinct sequential version numbers",
      f"numbers={[r[0] for r in after]}", [r[0] for r in after] == list(range(1, len(after) + 1)), "member (author, 2 sessions)")
st, _ = post_revision("thompson", "a_conflict", {**v1[1], "QA-HIST": "Third write with stale expected_version=1"}, "obs", expected_version=1)
check("S9", "sequential POST with stale expected_version=1 rejected", "409", f"status={st}", st == 409, "member (assigned author)")

# ---------------------------------------------------------------- S12 non-owner runtime role, raw SQL
with runtime_db() as c:
    who = c.execute("SELECT current_user, (SELECT rolsuper FROM pg_roles WHERE rolname=current_user), "
                    "(SELECT rolbypassrls FROM pg_roles WHERE rolname=current_user)").fetchone()
    check("S12", "HTTP/runtime role is non-owner, non-superuser, no BYPASSRLS", "ctm_app False False", str(who),
          who == ("ctm_app", False, False), "database runtime")
    c.execute("BEGIN")
    n = c.execute("SELECT count(*) FROM tribunal_reportrevision").fetchone()[0]
    c.execute("ROLLBACK")
    check("S12", "no actor context: report revisions invisible", "0 rows", f"{n} rows", n == 0, "database runtime, no actor")
    for actor, label, report, expect_ok in [("wilson", "unassigned member", "a_main", False),
                                            ("emily", "applicant", "a_main", False),
                                            ("wilson", "author on closed case", "d_main", False),
                                            ("wilson", "author on reopened case's old proceeding", "b_old", False)]:
        c.execute("BEGIN")
        c.execute("SELECT set_config('ctm.actor_id',%s,true)", [F["people"][actor]["id"]])
        visible = c.execute("SELECT count(*) FROM tribunal_reportrevision WHERE report_id=%s", [R[report]]).fetchone()[0]
        try:
            c.execute("INSERT INTO tribunal_reportrevision (id, created_at, report_id, number, answers, observations, actor_id) "
                      "VALUES (gen_random_uuid(), now(), %s, 99, '{}'::jsonb, 'raw sql', %s)", [R[report], F["people"][actor]["id"]])
            outcome = "INSERTED"
        except psycopg.Error as exc:
            outcome = f"denied: {type(exc).__name__}: {str(exc).splitlines()[0][:140]}"
        c.execute("ROLLBACK")
        check("S12", f"raw INSERT as ctm_app, actor={label}, report={report}", "denied by RLS/trigger",
              f"visible_rows={visible} {outcome}", outcome != "INSERTED", f"database runtime ({label})")
    c.execute("BEGIN")
    c.execute("SELECT set_config('ctm.actor_id',%s,true)", [F["people"]["thompson"]["id"]])
    try:
        cur = c.execute("UPDATE tribunal_reportrevision SET observations='tampered' WHERE report_id=%s", [R["a_main"]])
        touched = cur.rowcount
        outcome = f"UPDATE ran, rows changed={touched}"
    except psycopg.Error as exc:
        touched = 0
        outcome = f"denied: {type(exc).__name__}: {str(exc).splitlines()[0][:140]}"
    c.execute("ROLLBACK")
    check("S12", "author cannot UPDATE a retained revision in place (immutable history)",
          "denied or 0 rows changed", outcome, touched == 0, "database runtime (author)")
    c.execute("BEGIN")
    c.execute("SELECT set_config('ctm.actor_id',%s,true)", [F["people"]["thompson"]["id"]])
    try:
        c.execute("INSERT INTO tribunal_reportrevision (id, created_at, report_id, number, answers, observations, actor_id) "
                  "VALUES (gen_random_uuid(), now(), %s, 98, '{}'::jsonb, 'raw sql positive control', %s)",
                  [R["a_main"], F["people"]["thompson"]["id"]])
        outcome = "INSERTED (rolled back)"
    except psycopg.Error as exc:
        outcome = f"denied: {type(exc).__name__}: {str(exc).splitlines()[0][:140]}"
    c.execute("ROLLBACK")
    check("S12", "positive control: author raw INSERT on open own report is allowed by RLS", "INSERTED (rolled back)",
          outcome, outcome.startswith("INSERTED"), "database runtime (author)")
with owner_db() as c:
    audit = c.execute("SELECT count(*) FROM tribunal_auditevent WHERE action='report_revised'").fetchone()[0]
    versions = c.execute("SELECT count(*) FROM tribunal_reportrevision WHERE number>1").fetchone()[0]
check("S12", "every appended version (v>1) has a report_revised audit event", f"{versions}", f"{audit}", audit == versions,
      "database (owner read)")

codes = sorted({s for _, s in DENIAL_STATUSES})
check("S4", "denial status semantics under non-owner runtime role", "403 for non-author/applicant, 422 for closed proceeding",
      f"statuses seen={codes} ({sum(s == 404 for _, s in DENIAL_STATUSES)}/{len(DENIAL_STATUSES)} denials returned 404 resource_or_input_invalid)",
      all(s in (403, 422) for _, s in DENIAL_STATUSES), "all denied writers")

summary = {"pass": sum(c["result"] == "PASS" for c in CHECKS), "fail": sum(c["result"] == "FAIL" for c in CHECKS)}
(EVIDENCE / "api-results.json").write_text(json.dumps({"summary": summary, "checks": CHECKS}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(summary))
