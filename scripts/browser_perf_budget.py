"""Speed measurement of the main pages on the synthetic browser fixture (#314).

Loads each page in scripts/perf_budgets.json at desktop width in a fresh browser
context (cold cache) against the real Plenix CDN and records, per page, the
median over the configured runs of:

- lcp_ms: Largest Contentful Paint.
- tbt_ms: Total Blocking Time after First Contentful Paint (the lab stand-in
  for INP: no real user clicks in CI).
- requests: every request the page made.
- js_bytes: decoded JavaScript bytes (CTM's own files and the Plenix CDN).

A metric the browser did not report is written as null (unknown, never a pass).
Budgets and the comparison with main live in scripts/check_perf_budget.py.

Run (from the checkout whose scripts you want to use):
  uv run --group browser python scripts/browser_perf_budget.py --out .tmp/perf-head.json
  uv run --group browser python scripts/browser_perf_budget.py --app-root ../base --out .tmp/perf-base.json
--app-root measures another checkout (for example main) with this script, using
that checkout's own fixture and application code. Data is synthetic only.
"""

import argparse
import io
import json
import logging
import os
import statistics
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--app-root", default=str(HERE.parent))
parser.add_argument("--budgets", default=str(HERE / "perf_budgets.json"))
parser.add_argument("--runs", type=int, default=None)
parser.add_argument("--port", type=int, default=18870)
parser.add_argument("--out", required=True)
args = parser.parse_args()

config = json.loads(Path(args.budgets).read_text(encoding="utf-8"))
runs = args.runs or int(config["runs"])
out_path = Path(args.out).resolve()
app_root = Path(args.app_root).resolve()

# A fresh database on the disposable cluster, with the measured checkout's own
# code and fictional dataset (seed_workflow_demo and friends, never real data).
admin_url = os.environ.get("CTM_PERF_DATABASE_URL") or os.environ.get("CTM_TEST_DATABASE_URL")
if not admin_url:
    raise SystemExit("Set CTM_PERF_DATABASE_URL to a disposable PostgreSQL cluster (never CTM live data).")
import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402

db_name = "ctm_perf_" + uuid.uuid4().hex[:12]
with psycopg.connect(admin_url, autocommit=True, connect_timeout=10) as conn:
    conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
parts = urlsplit(admin_url)
os.environ["CTM_TEST_DATABASE_URL"] = urlunsplit(parts._replace(path="/" + db_name))
os.environ["DJANGO_SETTINGS_MODULE"] = "ctm.settings_postgres_test"
os.chdir(app_root)
sys.path.insert(0, str(app_root))
run_dir = app_root / ".tmp" / ("browser-perf-" + uuid.uuid4().hex)
run_dir.mkdir(parents=True)


def drop_database():
    from django.db import connections

    connections.close_all()
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=10) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(db_name)))


import django  # noqa: E402
from django.conf import settings  # noqa: E402

try:
    settings.MEDIA_ROOT = run_dir / "media"
    settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
    settings.DEBUG = True
    django.setup()
    import ctm  # noqa: E402

    if not Path(ctm.__file__).resolve().is_relative_to(app_root):
        raise SystemExit(f"Measured code is {ctm.__file__}, not the checkout at {app_root}.")
    from django.core.management import call_command  # noqa: E402
    from django.db.models import Count, Q  # noqa: E402
    from tribunal import models as m  # noqa: E402

    seed = {"live_fictitious": True, "confirmation": "FICTITIOUS-DEMO-DATA-ONLY", "verbosity": 0}
    started = time.monotonic()
    call_command("migrate", verbosity=0, interactive=False)
    for command in ("seed_workflow_demo", "seed_new_applications_demo", "seed_seat_cases"):
        call_command(command, stdout=io.StringIO(), **seed)
    logging.getLogger("django.request").setLevel(logging.ERROR)  # expected 401/404 noise
    print(f"fictional dataset ready in {time.monotonic() - started:.0f} s", flush=True)
    member = (
        m.Account.objects.filter(role="member", is_active=True)
        .annotate(open_cases=Count("assigned_cases", filter=Q(assigned_cases__status="open")))
        .order_by("-open_cases", "email")
        .first()
    )
    case = m.Case.objects.filter(assigned_member=member, status="open").order_by("number").first()
    applicant = (
        m.Account.objects.filter(role="applicant", is_active=True, party__isnull=False)
        .annotate(n=Count("party"))
        .order_by("-n", "email")
        .first()
    )
    if not (member and case and applicant):
        raise SystemExit("The fictional dataset has no council member with an open case or no applicant.")
    from django.test import Client  # noqa: E402
    from django.contrib.staticfiles.handlers import StaticFilesHandler  # noqa: E402
    from django.core.wsgi import get_wsgi_application  # noqa: E402
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server  # noqa: E402
    from socketserver import ThreadingMixIn  # noqa: E402
except BaseException:
    drop_database()
    raise


def session_cookie(account):
    client = Client()
    client.force_login(
        account, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    return client.cookies[settings.SESSION_COOKIE_NAME].value


cookies = {"manager": session_cookie(member), "applicant": session_cookie(applicant)}
values = {"case_id": str(case.pk)}
dataset = {
    "cases": m.Case.objects.count(),
    "member_open_cases": member.open_cases,
    "applicant_parties": applicant.n,
}


class Quiet(WSGIRequestHandler):
    def log_message(self, *a):
        pass


class Threaded(ThreadingMixIn, WSGIServer):
    daemon_threads = True


server = make_server(
    "127.0.0.1",
    args.port,
    StaticFilesHandler(get_wsgi_application()),
    server_class=Threaded,
    handler_class=Quiet,
)
threading.Thread(target=server.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{args.port}"

OBSERVE = """
(() => {
  const p = (window.__ctmPerf = { lcp: null, longtasks: [] });
  try {
    new PerformanceObserver((l) => { for (const e of l.getEntries()) p.lcp = e.renderTime || e.loadTime || e.startTime; })
      .observe({ type: "largest-contentful-paint", buffered: true });
    new PerformanceObserver((l) => { for (const e of l.getEntries()) p.longtasks.push([e.startTime, e.duration]); })
      .observe({ type: "longtask", buffered: true });
  } catch (e) { p.error = String(e); }
})();
"""
READ = """
() => {
  const p = window.__ctmPerf || {};
  const fcpEntry = performance.getEntriesByName("first-contentful-paint")[0];
  const fcp = fcpEntry ? fcpEntry.startTime : null;
  const tbt = fcp === null ? null : (p.longtasks || [])
    .filter(([start]) => start >= fcp)
    .reduce((sum, [, d]) => sum + Math.max(0, d - 50), 0);
  return { lcp: p.lcp, fcp, tbt, error: p.error || null };
}
"""
READY = "() => !!document.querySelector('h1, [role=heading][aria-level=\"1\"]')"


def measure(browser, page_cfg):
    context = browser.new_context(
        viewport={
            "width": config["viewport"]["width"],
            "height": config["viewport"]["height"],
        }
    )
    if page_cfg["account"]:
        context.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": cookies[page_cfg["account"]],
                    "url": BASE + "/",
                    "httpOnly": True,
                    "sameSite": "Lax",
                }
            ]
        )
    context.add_init_script(OBSERVE)
    page = context.new_page()
    requests, scripts, problems, open_requests = [], [], [], set()
    page.on("request", lambda r: (requests.append(r.url), open_requests.add(r.url)))
    page.on("requestfinished", lambda r: open_requests.discard(r.url))
    page.on("response", lambda r: r.request.resource_type == "script" and scripts.append(r))
    page.on("pageerror", lambda e: problems.append(f"browser error: {e}"))
    page.on("requestfailed", lambda r: problems.append(f"request failed: {r.url}"))
    try:
        page.goto(BASE + page_cfg["path"].format(**values), wait_until="load", timeout=60000)
        page.wait_for_function(READY, timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            problems.append("never network-idle; still open: " + ", ".join(sorted(open_requests)))
        time.sleep(0.5)  # let the last paint and long-task entries arrive
        metrics = page.evaluate(READ)
        js_bytes = 0
        for response in scripts:
            try:
                js_bytes += len(response.body())
            except Exception as error:  # body unavailable: unknown, never zero
                problems.append(f"script body unavailable: {response.url} ({error})")
                js_bytes = None
                break
    except Exception as error:
        problems.append(f"page did not load: {error}")
        metrics, js_bytes = {"lcp": None, "tbt": None, "error": None}, None
    finally:
        context.close()
    if metrics.get("error"):
        problems.append(f"performance observer: {metrics['error']}")
    return {
        "lcp_ms": round(metrics["lcp"]) if metrics.get("lcp") else None,
        "tbt_ms": round(metrics["tbt"]) if metrics.get("tbt") is not None else None,
        "requests": len(requests),
        "js_bytes": js_bytes,
        "problems": problems,
    }


def median(samples, key):
    vals = [s[key] for s in samples]
    if any(v is None for v in vals):
        return None
    return round(statistics.median(vals))


from playwright.sync_api import sync_playwright  # noqa: E402

result = {
    "app_root": str(app_root),
    "commit": os.popen(f"git -C '{app_root}' rev-parse HEAD").read().strip() or None,
    "plenix_base": getattr(settings, "PLENIX_BASE", None),
    "runs": runs,
    "viewport": config["viewport"],
    "dataset": dataset,
    "pages": {},
}
try:
    with sync_playwright() as p:
        cdn_args = (
            [f"--host-resolver-rules=MAP design-system.lighthouseway.org {os.environ['CTM_CDN_LAN_IP']}"]
            if os.environ.get("CTM_CDN_LAN_IP")
            else []
        )
        browser = p.chromium.launch(
            executable_path=os.environ.get("CTM_BROWSER_EXECUTABLE", p.chromium.executable_path),
            headless=True,
            args=cdn_args,
        )
        # One warm-up load so DNS/TLS to the CDN is not charged to the first page.
        measure(browser, {"account": None, "path": "/"})
        for page_cfg in config["pages"]:
            samples = [measure(browser, page_cfg) for _ in range(runs)]
            result["pages"][page_cfg["id"]] = {
                "label": page_cfg["label"],
                **{k: median(samples, k) for k in ("lcp_ms", "tbt_ms", "requests", "js_bytes")},
                "samples": samples,
                "problems": sorted({p for s in samples for p in s["problems"]}),
            }
            row = result["pages"][page_cfg["id"]]
            print(
                f"{row['label']:<16} LCP {row['lcp_ms']} ms  TBT {row['tbt_ms']} ms  "
                f"requests {row['requests']}  JS {row['js_bytes']} B"
                + (f"  problems: {row['problems']}" if row["problems"] else ""),
                flush=True,
            )
        browser.close()
finally:
    server.shutdown()
    drop_database()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
