"""QA-01 browser checks: real assembled UI + real backend (runtime role ctm_app) + real Plenix 0.58.0 CDN.

Run after reset.sh on a fresh fixture set (the API script consumes some of the same reports).
Simulated conditions are labelled: 'simulated' means Playwright intercepted the browser request;
'real' means the server itself produced the condition.
Writes evidence/browser-results.json and screenshots under evidence/screens/.
"""

import json
import re
import traceback
from urllib.parse import urlparse

import psycopg

from browser_common import BASE_URL, F, context_for, open_case_reports, run
from qa_env import EVIDENCE, load_env

SHOTS = EVIDENCE / "screens"
SHOTS.mkdir(exist_ok=True)
R = F["reports"]
CHECKS = []
HIST = re.compile(r"^QA-HIST — \W*Describe how the marriage began\.\W*$")  # 65fa389 adds bidi isolates
OBS = "Council observations"


def db():
    u = urlparse(load_env()["qa_owner"])
    return psycopg.connect(host=u.hostname, port=u.port, user=u.username, password=u.password, dbname=u.path[1:])


def versions(report):
    with db() as c:
        return c.execute("SELECT number, answers, observations, actor_id::text FROM tribunal_reportrevision "
                         "WHERE report_id=%s ORDER BY number", [R[report]]).fetchall()


def check(scenario, label, expected, actual, ok, role, shot=None):
    CHECKS.append({"scenario": scenario, "check": label, "role": role, "expected": expected, "actual": actual,
                   "result": "PASS" if ok else "FAIL", "screenshot": shot})
    print(("PASS " if ok else "FAIL ") + f"[{scenario}] {label} :: {actual}", flush=True)


def shot(page, name):
    path = SHOTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return f"evidence/screens/{name}.png"


def page_for(browser, who, **kw):
    ctx = context_for(browser, who, **kw)
    page = ctx.new_page()
    page.qa_errors = []
    page.on("pageerror", lambda e: page.qa_errors.append(str(e)))
    return ctx, page


def report_item(page, title):
    """Report row: a card button up to 65fa389, a table grid cell from 0b10a61."""
    return page.get_by_role("gridcell", name=title, exact=True).or_(page.get_by_role("button", name=title, exact=True))


def open_report(page, case_key, title):
    for attempt in range(2):
        open_case_reports(page, case_key)
        try:
            page.get_by_role("gridcell", name=title, exact=True).or_(
                page.get_by_role("button", name=title, exact=True)).first.wait_for(timeout=10000)
            item = report_item(page, title).first
            break
        except Exception:
            if attempt:
                raise
    item.click()
    page.get_by_text("Report for", exact=True).first.wait_for()


def has_revise(page):
    page.wait_for_timeout(400)
    return page.get_by_role("button", name="Revise report", exact=True).count() > 0


def start_edit(page):
    page.get_by_role("button", name="Revise report", exact=True).click()
    page.get_by_role("textbox", name=HIST).wait_for()


def save(page):
    """Click Save; from 0b10a61 an unconfirmed save offers 'Try again' (same body) instead."""
    retry = page.get_by_role("button", name="Try again", exact=True)
    (retry if retry.count() else page.get_by_role("button", name="Save as new version", exact=True)).first.click()


UNCONFIRMED = re.compile(r"Your text is kept; try again\.|The server did not confirm this save")


def scenario(fn):
    def wrapped(browser):
        try:
            fn(browser)
        except Exception as exc:  # record, keep going with other scenarios
            CHECKS.append({"scenario": fn.__name__, "check": "scenario raised", "result": "ERROR",
                           "actual": f"{type(exc).__name__}: {exc}"[:500]})
            traceback.print_exc()
    return wrapped


@scenario
def s1_visibility(browser):
    ctx, page = page_for(browser, "thompson")
    open_report(page, "a", "QA interview: main")
    ok_text = page.get_by_text("Second history narrative (main).", exact=True).count() > 0 and \
        page.get_by_text("Second observation (main).", exact=True).count() > 0
    s = shot(page, "s1-author-main-newest")
    check("S1", "author sees Revise on own open report", "Revise visible", f"visible={has_revise(page)}", has_revise(page), "member (assigned author)", s)
    check("S1", "newest answers and observations load (v2)", "v2 texts shown", f"shown={ok_text}", ok_text, "member (assigned author)", s)
    for title, label in [("QA interview: secretary-authored", "secretary-authored report"), ("QA applicant intake", "applicant intake")]:
        report_item(page, title).first.click()
        page.wait_for_timeout(600)
        s = shot(page, "s1-author-no-revise-" + label.split()[0])
        notice = page.get_by_text("Only the report's original council author can revise it", exact=False).count() > 0
        check("S1", f"no Revise on {label}", "hidden + explanation", f"revise={has_revise(page)} explanation={notice}",
              not has_revise(page) and notice, "member (assigned, non-author)", s)
    ctx.close()
    for who, role in [("wilson", "member (unassigned)"), ("anderson", "admin (non-author)")]:
        ctx, page = page_for(browser, who)
        open_report(page, "a", "QA interview: main")
        s = shot(page, f"s1-{who}-no-revise")
        check("S1", f"{who} sees report but no Revise", "hidden", f"revise={has_revise(page)}", not has_revise(page), role, s)
        ctx.close()
    ctx, page = page_for(browser, "miller")
    open_report(page, "a", "QA interview: secretary-authored")
    check("S1", "secretary author sees Revise on own report", "visible", f"revise={has_revise(page)}", has_revise(page), "secretary (author)")
    ctx.close()


@scenario
def s2_edit_persist(browser):
    before = versions("a_ui")
    ctx, page = page_for(browser, "thompson")
    open_report(page, "a", "QA interview: browser")
    start_edit(page)
    page.get_by_role("textbox", name=HIST).fill("Browser revision of the history (QA-01 S2).")
    page.get_by_role("textbox", name=OBS).fill("Browser revised observation (QA-01 S2).")
    s_edit = shot(page, "s2-editor-filled")
    save(page)
    page.get_by_text("Saved as version 2.", exact=True).wait_for(timeout=10000)
    s = shot(page, "s2-saved")
    after = versions("a_ui")
    check("S2", "UI save appends exactly one version", f"{len(before)}+1", f"{len(after)}", len(after) == len(before) + 1, "member (assigned author)", s)
    new = after[-1][1]
    check("S2", "non-text answers carried over by the editor", "QA-PREF dict and QA-SCORE=3 unchanged",
          f"QA-PREF={new.get('QA-PREF')} QA-SCORE={new.get('QA-SCORE')}",
          new.get("QA-PREF") == before[-1][1]["QA-PREF"] and new.get("QA-SCORE") == 3, "member (assigned author)", s_edit)
    check("S2", "untouched text answers preserved", "QA-SEP unchanged", f"QA-SEP={new.get('QA-SEP')!r}",
          new.get("QA-SEP") == before[-1][1]["QA-SEP"], "member (assigned author)")
    check("S2", "version attributed to author", F["people"]["thompson"]["id"], after[-1][3], after[-1][3] == F["people"]["thompson"]["id"], "member (assigned author)")
    page.reload(wait_until="domcontentloaded")
    open_report(page, "a", "QA interview: browser")
    shown = page.get_by_text("Browser revision of the history (QA-01 S2).", exact=True).count() > 0
    page.get_by_role("button", name="Show revision history", exact=True).click()
    combo = page.get_by_role("combobox", name="Revision history", exact=True)
    options = combo.evaluate("e => [...e.options].map(o => o.textContent)")
    combo.select_option("1")
    old_visible = page.get_by_text("Original history narrative (ui).", exact=True).count() > 0
    s = shot(page, "s2-reload-history-v1")
    check("S2", "after reload newest text shown; history lists both versions with author; v1 still readable",
          "v2 shown, 2 options with Michael Thompson, v1 text visible",
          f"v2_shown={shown} options={options} v1_visible={old_visible}",
          shown and len(options) == 2 and all("Michael Thompson" in o for o in options) and old_visible, "member (assigned author)", s)
    ctx.close()


@scenario
def s3_unchanged(browser):
    before = versions("a_unchanged")
    ctx, page = page_for(browser, "thompson")
    posts = []
    page.on("request", lambda r: r.method == "POST" and "/revisions/" in r.url and posts.append(r.url))
    open_report(page, "a", "QA interview: unchanged")
    start_edit(page)
    save(page)
    page.get_by_text("Nothing has changed from the current version.", exact=True).wait_for(timeout=5000)
    s = shot(page, "s3-unchanged")
    after = versions("a_unchanged")
    check("S3", "UI: unchanged save sends no POST and creates no version", "0 POSTs, versions unchanged",
          f"posts={len(posts)} versions {len(before)}->{len(after)}", not posts and len(after) == len(before), "member (assigned author)", s)
    ctx.close()


@scenario
def s8_failures(browser):
    ctx, page = page_for(browser, "thompson")
    open_report(page, "a", "QA interview: lost ack")
    start_edit(page)
    text = "Text that must survive failures (QA-01 S8)."
    page.get_by_role("textbox", name=HIST).fill(text)
    base = versions("a_lost")
    # (a) simulated server error
    page.route("**/api/reports/*/revisions/", lambda route: route.fulfill(status=500, content_type="application/json", body='{"error":"server"}')
               if route.request.method == "POST" else route.continue_())
    save(page)
    page.get_by_text(UNCONFIRMED).first.wait_for(timeout=8000)
    kept = page.get_by_role("textbox", name=HIST).input_value() == text
    success = page.get_by_text("Saved as version", exact=False).count() > 0
    s = shot(page, "s8-simulated-500")
    check("S8", "simulated 500: text kept, no false success, no version", "text kept, no success, versions unchanged",
          f"kept={kept} success_shown={success} versions {len(base)}->{len(versions('a_lost'))}",
          kept and not success and len(versions("a_lost")) == len(base), "member (assigned author)", s)
    page.unroute("**/api/reports/*/revisions/")
    # (b) simulated lost acknowledgement: request reaches the real server, response is dropped
    def drop_ack(route):
        if route.request.method != "POST":
            return route.continue_()
        route.fetch()  # server commits
        route.abort("connectionreset")
    page.route("**/api/reports/*/revisions/", drop_ack)
    save(page)
    page.wait_for_timeout(2500)
    after_drop = versions("a_lost")
    kept = page.get_by_role("textbox", name=HIST).input_value() == text
    success = page.get_by_text("Saved as version", exact=False).count() > 0
    s = shot(page, "s8-lost-ack")
    check("S8", "lost acknowledgement: server committed once, UI shows no false success and keeps text",
          "1 new version, no success notice, text kept",
          f"versions {len(base)}->{len(after_drop)} success_shown={success} kept={kept}",
          len(after_drop) == len(base) + 1 and not success and kept, "member (assigned author)", s)
    page.unroute("**/api/reports/*/revisions/")
    save(page)  # user retries
    page.wait_for_timeout(2500)
    after_retry = versions("a_lost")
    stale_notice = page.get_by_text("Save my text as a new version", exact=True).count() > 0
    s = shot(page, "s8-retry-after-lost-ack")
    check("S8", "retry after lost acknowledgement does not silently duplicate", "no second version without an explicit choice",
          f"versions {len(after_drop)}->{len(after_retry)} stale_choice_shown={stale_notice}",
          len(after_retry) == len(after_drop), "member (assigned author)", s)
    check("S8", "OBSERVATION: retry after lost ack presents the user's own saved version as a conflicting newer version",
          "UI recognises its own committed write (idempotent receipt) instead of a conflict",
          f"stale_choice_shown={stale_notice} (a 'Save anyway' click would append a duplicate)", not stale_notice, "member (assigned author)", s)
    confirmed = page.get_by_text("Saved as version", exact=False).count() > 0
    check("S8", "retry after lost acknowledgement is confirmed as the already-saved version",
          "success notice for the existing version, no new version", f"success_shown={confirmed} versions={len(after_retry)}",
          confirmed and len(after_retry) == len(after_drop), "member (assigned author)", s)
    ctx.close()
    # (c) simulated 403 response
    ctx, page = page_for(browser, "thompson")
    open_report(page, "a", "QA interview: main")
    start_edit(page)
    page.get_by_role("textbox", name=HIST).fill("Edit before a simulated 403.")
    page.route("**/api/reports/*/revisions/", lambda route: route.fulfill(status=403, content_type="application/json",
               body='{"error":"forbidden","detail":"Only the original authorized council author can revise this report."}')
               if route.request.method == "POST" else route.continue_())
    save(page)
    page.get_by_text("This revision was not allowed.", exact=False).wait_for(timeout=8000)
    kept = page.get_by_role("textbox", name=HIST).input_value() == "Edit before a simulated 403."
    save_gone = page.get_by_role("button", name="Save as new version", exact=True).count() == 0
    s = shot(page, "s8-simulated-403")
    check("S8", "simulated 403: text kept, Save hidden, denial explained", "kept, Save hidden",
          f"kept={kept} save_hidden={save_gone}", kept and save_gone, "member (assigned author)", s)
    ctx.close()
    # (d) real server denial: case reassigned while the author is editing
    ctx, page = page_for(browser, "thompson")
    open_report(page, "e", "QA interview: mid-edit reassignment")
    start_edit(page)
    page.get_by_role("textbox", name=HIST).fill("Edit while the case is being reassigned.")
    admin = browser.new_context()
    admin.add_cookies([{"name": "sessionid", "value": F["cookies"]["miller"], "url": BASE_URL},
                       {"name": "csrftoken", "value": "qa01" + "0" * 28, "url": BASE_URL}])
    res = admin.request.post(f"{BASE_URL}/api/cases/{F['cases']['e']}/assignment/",
                             data=json.dumps({"member_id": F["people"]["collins"]["id"], "president_id": F["people"]["wright"]["id"]}),
                             headers={"Content-Type": "application/json", "X-CSRFToken": "qa01" + "0" * 28})
    admin.close()
    base = versions("e_main")
    statuses = []
    page.on("response", lambda r: r.request.method == "POST" and "/revisions/" in r.url and statuses.append(r.status))
    save(page)
    page.wait_for_timeout(2500)
    kept = page.get_by_role("textbox", name=HIST).input_value() == "Edit while the case is being reassigned."
    denied_msg = page.get_by_text("This revision was not allowed.", exact=False).count() > 0
    save_gone = page.get_by_role("button", name="Save as new version", exact=True).count() == 0
    s = shot(page, "s8-real-denial-after-reassignment")
    check("S8", "real server denial mid-edit (reassigned): no write, text kept, no false success",
          "no new version, text kept", f"reassign={res.status} POST statuses={statuses} kept={kept} versions {len(base)}->{len(versions('e_main'))}",
          res.status == 201 and kept and len(versions("e_main")) == len(base) and page.get_by_text("Saved as version", exact=False).count() == 0,
          "member (author, reassigned away)", s)
    check("S8", "real server denial is presented as a denial (Save hidden, 'not allowed')",
          "denial notice, Save hidden (needs 403 from server)", f"POST statuses={statuses} denial_notice={denied_msg} save_hidden={save_gone}",
          denied_msg and save_gone, "member (author, reassigned away)", s)
    ctx.close()


@scenario
def s9_two_sessions(browser):
    base = versions("a_conflict")
    c1, p1 = page_for(browser, "thompson")
    c2, p2 = page_for(browser, "thompson_2")
    for p in (p1, p2):
        open_report(p, "a", "QA interview: conflict")
        start_edit(p)
    p1.get_by_role("textbox", name=HIST).fill("Session one wrote this (QA-01 S9).")
    p2.get_by_role("textbox", name=HIST).fill("Session two wrote this (QA-01 S9).")
    # Sequential: one session saves, the other then saves from the same base version.
    save(p1)
    p1.get_by_text("Saved as version", exact=False).wait_for(timeout=8000)
    save(p2)
    p2.wait_for_timeout(2000)
    warned = p2.get_by_text("Save my text as a new version", exact=True).count() > 0
    s = shot(p2, "s9-ui-sequential-stale")
    check("S9", "UI preflight: second session warned before overwriting a newer version", "stale warning, no extra version",
          f"warned={warned} versions {len(base)}->{len(versions('a_conflict'))}", warned and len(versions("a_conflict")) == len(base) + 1,
          "member (author, 2 sessions)", s)
    for c in (c1, c2):
        c.close()
    # Near-simultaneous: both sessions edit from the same version and click Save together.
    base = versions("a_conflict")
    c1, p1 = page_for(browser, "thompson")
    c2, p2 = page_for(browser, "thompson_2")
    for p, t in ((p1, "Race one (QA-01 S9)."), (p2, "Race two (QA-01 S9).")):
        open_report(p, "a", "QA interview: conflict")
        start_edit(p)
        p.get_by_role("textbox", name=HIST).fill(t)
    for p in (p1, p2):
        p.evaluate("""() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent==='Save as new version'); window.__qaSave=b; }""")
    p1.evaluate("() => window.__qaSave.click()")
    p2.evaluate("() => window.__qaSave.click()")
    p1.wait_for_timeout(3000)
    after = versions("a_conflict")
    s1 = shot(p1, "s9-ui-race-session1")
    s2 = shot(p2, "s9-ui-race-session2")
    both_saved = p1.get_by_text("Saved as version", exact=False).count() > 0 and p2.get_by_text("Saved as version", exact=False).count() > 0
    check("S9", "near-simultaneous saves from two sessions: only one may win without a conflict",
          "1 new version + 1 conflict/stale warning", f"versions {len(base)}->{len(after)} both_reported_saved={both_saved}",
          len(after) == len(base) + 1, "member (author, 2 sessions)", s1)
    for c in (c1, c2):
        c.close()


@scenario
def s10_unsaved(browser):
    ctx, page = page_for(browser, "thompson")
    open_report(page, "a", "QA interview: main")
    start_edit(page)
    page.get_by_role("textbox", name=HIST).fill("Unsaved narrative (QA-01 S10).")
    dialogs = []

    def on_dialog(d):
        dialogs.append(d.type)
        d.dismiss()
    page.on("dialog", on_dialog)
    try:
        page.reload(timeout=4000)
    except Exception:
        pass
    still = page.get_by_role("textbox", name=HIST).count() > 0 and page.get_by_role("textbox", name=HIST).input_value() == "Unsaved narrative (QA-01 S10)."
    s = shot(page, "s10-reload-guard")
    check("S10", "refresh with unsaved narrative triggers the leave-page warning; dismiss keeps text",
          "beforeunload dialog, text kept", f"dialogs={dialogs} kept={still}", "beforeunload" in dialogs and still, "member (assigned author)", s)
    # In-app navigation (sidebar) does not unload the page.
    page.get_by_role("button", name="Documents", exact=True).first.click()
    page.wait_for_timeout(800)
    page.get_by_role("button", name="Reports", exact=True).first.click()
    report_item(page, "QA interview: main").first.click()
    page.wait_for_timeout(800)
    editor_back = page.get_by_role("textbox", name=HIST).count() > 0
    s = shot(page, "s10-sidebar-navigation")
    check("S10", "in-app navigation away from the editor warns or preserves the unsaved narrative",
          "warning before leaving, or text restored", f"in_app_dialogs={dialogs[1:]} editor_restored={editor_back}",
          editor_back or len(dialogs) > 1, "member (assigned author)", s)
    ctx.close()


@scenario
def s11_language_layout(browser):
    for lang, width in [("en", 390), ("ar", 1280), ("ar", 390)]:
        ctx, page = page_for(browser, "thompson", width=width, height=900)
        open_report(page, "a", "QA interview: main")
        if lang == "ar":
            page.get_by_role("button", name="العربية", exact=True).first.click()
            page.wait_for_timeout(1500)
        metrics = page.evaluate("""() => ({dir: document.documentElement.dir || document.body.dir,
            lang: document.documentElement.lang,
            overflow: document.scrollingElement.scrollWidth - window.innerWidth,
            styles: document.querySelectorAll('#ctm-root [style], #root [style], main [style]').length,
            text: document.body.innerText})""")
        author_label = ("الكاتب" if lang == "ar" else "Author") in metrics["text"]
        revise_label = ("تعديل التقرير" if lang == "ar" else "Revise report") in metrics["text"]
        s = shot(page, f"s11-{lang}-{width}-reader")
        check("S11", f"{lang.upper()} {width}px reader: direction, author label, Revise label, no overflow",
              f"dir={'rtl' if lang == 'ar' else 'ltr/empty'}, labels present, overflow<=0",
              f"dir={metrics['dir']!r} lang={metrics['lang']!r} author_label={author_label} revise_label={revise_label} overflow={metrics['overflow']} inline_styles={metrics['styles']}",
              (metrics["dir"] == "rtl") == (lang == "ar") and author_label and revise_label and metrics["overflow"] <= 0,
              "member (assigned author)", s)
        page.get_by_role("button", name="تعديل التقرير" if lang == "ar" else "Revise report", exact=True).click()
        page.wait_for_timeout(1200)
        fields = page.evaluate("""() => [...document.querySelectorAll('textarea')].map(t => ({w: t.getBoundingClientRect().width,
            r: t.getBoundingClientRect().right, l: t.getBoundingClientRect().left}))""")
        clipped = [f for f in fields if f["r"] > page.viewport_size["width"] + 1 or f["l"] < -1 or f["w"] < 120]
        overflow = page.evaluate("() => document.scrollingElement.scrollWidth - window.innerWidth")
        s = shot(page, f"s11-{lang}-{width}-editor")
        check("S11", f"{lang.upper()} {width}px editor: fields not clipped, no horizontal overflow",
              "all textareas within viewport and >=120px wide", f"textareas={len(fields)} clipped={len(clipped)} overflow={overflow}",
              fields and not clipped and overflow <= 0, "member (assigned author)", s)
        check("S11", f"{lang.upper()} {width}px: no page errors", "none", str(page.qa_errors[:3]), not page.qa_errors, "member (assigned author)")
        if lang == "ar":  # the language choice is saved on the account; restore English for later checks
            page.get_by_role("button", name="English", exact=True).first.click()
            page.wait_for_timeout(1200)
        ctx.close()
    ctx, page = page_for(browser, "wilson", width=390)
    open_report(page, "a", "QA interview: main")
    page.get_by_role("button", name="العربية", exact=True).first.click()
    page.wait_for_timeout(1200)
    text = page.evaluate("() => document.body.innerText")
    s = shot(page, "s11-ar-390-non-author")
    check("S11", "AR 390px non-author: no Revise control, explanation in Arabic", "no تعديل التقرير button",
          f"revise_button={page.get_by_role('button', name='تعديل التقرير', exact=True).count()}",
          page.get_by_role("button", name="تعديل التقرير", exact=True).count() == 0, "member (unassigned)", s)
    page.get_by_role("button", name="English", exact=True).first.click()
    page.wait_for_timeout(1200)
    ctx.close()


def main(browser):
    for fn in (s1_visibility, s2_edit_persist, s3_unchanged, s8_failures, s9_two_sessions, s10_unsaved, s11_language_layout):
        fn(browser)


run(main)
summary = {k: sum(c["result"] == k for c in CHECKS) for k in ("PASS", "FAIL", "ERROR")}
(EVIDENCE / "browser-results.json").write_text(json.dumps({"summary": summary, "checks": CHECKS}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(summary))
