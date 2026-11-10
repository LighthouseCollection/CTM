"""Speed measurement of the main pages on the fictional dataset (#314).

For each checkout measured (this one and, with --base-root, main) a server
process creates a fresh database on a disposable PostgreSQL cluster, runs that
checkout's own migrations and fictional seeders (seed_workflow_demo,
seed_new_applications_demo, seed_seat_cases; never real data) and serves that
checkout's code. The driver then loads each page in scripts/perf_budgets.json
at desktop width in a fresh browser context (cold cache, real Plenix CDN),
alternating between the checkouts on every run so both see the same machine
load, and records the median over the runs of:

- lcp_ms: Largest Contentful Paint.
- tbt_ms: Total Blocking Time after First Contentful Paint (the lab stand-in
  for INP: no real user clicks in CI).
- requests: every request the page made.
- js_bytes: decoded JavaScript bytes (CTM's own files and the Plenix CDN).

A metric the browser did not report is written as null (unknown, never a pass).
Budgets and the verdict live in scripts/check_perf_budget.py.

Run:
  CTM_PERF_DATABASE_URL=postgres://... uv run --group browser python scripts/browser_perf_budget.py \\
      --out .tmp/perf-head.json [--base-root ../main --base-out .tmp/perf-base.json]
CTM_PERF_DATABASE_URL must point to a disposable cluster that has the ctm_app
and ctm_worker roles (deploy/postgres/init.sql); each server creates and drops
its own database. Optional: CTM_BROWSER_EXECUTABLE, CTM_CDN_LAN_IP.
"""

import argparse
import io
import json
import logging
import os
import statistics
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
METRICS = ("lcp_ms", "tbt_ms", "requests", "js_bytes")


# --------------------------------------------------------------------------
# Server mode: one checkout, its own fresh database and fictional dataset.
# --------------------------------------------------------------------------
def serve(app_root, port, ready_file):
    admin_url = os.environ.get("CTM_PERF_DATABASE_URL")
    if not admin_url:
        raise SystemExit("Set CTM_PERF_DATABASE_URL to a disposable PostgreSQL cluster (never CTM live data).")
    import psycopg
    from psycopg import sql

    db_name = "ctm_perf_" + uuid.uuid4().hex[:12]
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=10) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))

    def drop_database():
        try:
            from django.db import connections

            connections.close_all()
        except Exception:
            pass
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=10) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(db_name)))

    try:
        os.environ["CTM_TEST_DATABASE_URL"] = urlunsplit(urlsplit(admin_url)._replace(path="/" + db_name))
        os.environ["DJANGO_SETTINGS_MODULE"] = "ctm.settings_postgres_test"
        os.chdir(app_root)
        sys.path.insert(0, str(app_root))
        run_dir = app_root / ".tmp" / ("browser-perf-" + uuid.uuid4().hex)
        run_dir.mkdir(parents=True)
        import django
        from django.conf import settings

        settings.MEDIA_ROOT = run_dir / "media"
        settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
        settings.DEBUG = True
        django.setup()
        import ctm

        if not Path(ctm.__file__).resolve().is_relative_to(app_root):
            raise SystemExit(f"Measured code is {ctm.__file__}, not the checkout at {app_root}.")
        from django.contrib.staticfiles.handlers import StaticFilesHandler
        from django.core.management import call_command
        from django.core.wsgi import get_wsgi_application
        from django.db.models import Count, Q
        from django.test import Client
        from socketserver import ThreadingMixIn
        from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server
        from tribunal import models as m

        started = time.monotonic()
        call_command("migrate", verbosity=0, interactive=False)
        seed = {"live_fictitious": True, "confirmation": "FICTITIOUS-DEMO-DATA-ONLY", "verbosity": 0}
        for command in ("seed_workflow_demo", "seed_new_applications_demo", "seed_seat_cases"):
            call_command(command, stdout=io.StringIO(), **seed)
        logging.getLogger("django.request").setLevel(logging.ERROR)  # expected 401/404 noise
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

        def session_cookie(account):
            client = Client()
            client.force_login(account, backend="allauth.account.auth_backends.AuthenticationBackend")
            return client.cookies[settings.SESSION_COOKIE_NAME].value

        class Quiet(WSGIRequestHandler):
            def log_message(self, *a):
                pass

        class Threaded(ThreadingMixIn, WSGIServer):
            daemon_threads = True

        server = make_server(
            "127.0.0.1", port, StaticFilesHandler(get_wsgi_application()), server_class=Threaded, handler_class=Quiet
        )
        threading.Thread(target=server.serve_forever, daemon=True).start()
        info = {
            "base_url": f"http://127.0.0.1:{port}",
            "cookie_name": settings.SESSION_COOKIE_NAME,
            # Synthetic sessions on a throwaway database; never printed.
            "cookies": {"manager": session_cookie(member), "applicant": session_cookie(applicant)},
            "values": {"case_id": str(case.pk)},
            "commit": subprocess.run(
                ["git", "-C", str(app_root), "rev-parse", "HEAD"], capture_output=True, text=True
            ).stdout.strip() or None,
            "plenix_base": getattr(settings, "PLENIX_BASE", None),
            "dataset": {
                "cases": m.Case.objects.count(),
                "member_open_cases": member.open_cases,
                "applicant_parties": applicant.n,
                "seconds_to_seed": round(time.monotonic() - started),
            },
        }
        tmp = Path(str(ready_file) + ".part")
        tmp.touch(mode=0o600)
        tmp.write_text(json.dumps(info), encoding="utf-8")
        tmp.rename(ready_file)
        sys.stdin.read()  # serve until the driver closes our stdin (or exits)
        server.shutdown()
    finally:
        drop_database()


# --------------------------------------------------------------------------
# Driver mode: start the servers, alternate page loads, write the results.
# --------------------------------------------------------------------------
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


def measure(browser, viewport, target, page_cfg):
    context = browser.new_context(viewport=viewport)
    base = target["base_url"]
    if page_cfg["account"]:
        context.add_cookies(
            [
                {
                    "name": target["cookie_name"],
                    "value": target["cookies"][page_cfg["account"]],
                    "url": base + "/",
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
    metrics, js_bytes = {"lcp": None, "tbt": None, "error": None}, None
    try:
        page.goto(base + page_cfg["path"].format(**target["values"]), wait_until="load", timeout=60000)
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
        problems.append(f"page did not load: {str(error).splitlines()[0]}")
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
    if not vals or any(v is None for v in vals):
        return None
    return round(statistics.median(vals))


def start_server(name, app_root, port, run_dir):
    ready = run_dir / f"{name}.ready.json"
    log = open(run_dir / f"{name}.server.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--serve", "--app-root", str(app_root),
         "--port", str(port), "--ready-file", str(ready)],
        stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True,
    )
    return {"name": name, "proc": proc, "ready": ready, "log": log, "log_path": run_dir / f"{name}.server.log"}


def wait_ready(server, deadline):
    while time.monotonic() < deadline:
        if server["ready"].exists():
            target = json.loads(server["ready"].read_text(encoding="utf-8"))
            server["ready"].unlink()
            return target
        if server["proc"].poll() is not None:
            break
        time.sleep(0.5)
    server["log"].flush()
    tail = server["log_path"].read_text(encoding="utf-8", errors="replace").splitlines()[-15:]
    print(f"{server['name']} server did not start:\n  " + "\n  ".join(tail), flush=True)
    return None


def stop_server(server):
    try:
        server["proc"].stdin.close()
        server["proc"].wait(timeout=60)
    except Exception:
        server["proc"].kill()
    server["log"].close()


def drive(args):
    config = json.loads(Path(args.budgets).read_text(encoding="utf-8"))
    runs = args.runs or int(config["runs"])
    viewport = {"width": config["viewport"]["width"], "height": config["viewport"]["height"]}
    run_dir = HERE.parent / ".tmp" / ("perf-run-" + uuid.uuid4().hex[:12])
    run_dir.mkdir(parents=True)
    sides = [("head", Path(args.app_root).resolve(), Path(args.out).resolve(), args.port)]
    if args.base_root:
        if not args.base_out:
            raise SystemExit("--base-root needs --base-out.")
        sides.append(("base", Path(args.base_root).resolve(), Path(args.base_out).resolve(), args.port + 1))
    servers = {name: start_server(name, root, port, run_dir) for name, root, _, port in sides}
    results = {}
    try:
        deadline = time.monotonic() + 900
        targets = {name: wait_ready(server, deadline) for name, server in servers.items()}
        live = [name for name, target in targets.items() if target]
        for name in live:
            t = targets[name]
            results[name] = {
                "app_root": str(dict((n, r) for n, r, _, _ in sides)[name]),
                "commit": t["commit"], "plenix_base": t["plenix_base"], "dataset": t["dataset"],
                "runs": runs, "viewport": viewport, "pages": {},
            }
            print(f"{name}: {t['commit'] and t['commit'][:10]} ready, dataset {t['dataset']}", flush=True)
        if not live:
            return
        from playwright.sync_api import sync_playwright

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
            for name in live:  # warm-up: DNS/TLS to the CDN is not charged to the first page
                measure(browser, viewport, targets[name], {"account": None, "path": "/"})
            for page_cfg in config["pages"]:
                samples = {name: [] for name in live}
                for run in range(runs):
                    order = live if run % 2 == 0 else list(reversed(live))
                    for name in order:
                        samples[name].append(measure(browser, viewport, targets[name], page_cfg))
                for name in live:
                    row = {
                        "label": page_cfg["label"],
                        **{k: median(samples[name], k) for k in METRICS},
                        "samples": samples[name],
                        "problems": sorted({q for s in samples[name] for q in s["problems"]}),
                    }
                    results[name]["pages"][page_cfg["id"]] = row
                    print(
                        f"{name:<5} {row['label']:<16} LCP {row['lcp_ms']} ms  TBT {row['tbt_ms']} ms  "
                        f"requests {row['requests']}  JS {row['js_bytes']} B"
                        + (f"  problems: {row['problems']}" if row["problems"] else ""),
                        flush=True,
                    )
            browser.close()
    finally:
        for server in servers.values():
            stop_server(server)
        for name, _, out, _ in sides:
            if name in results:  # a side that never started writes nothing: unknown
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(results[name], indent=2) + "\n", encoding="utf-8")
                print(f"wrote {out}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app-root", default=str(HERE.parent), help="checkout to measure (default: this one)")
    parser.add_argument("--base-root", help="second checkout to compare with (main)")
    parser.add_argument("--out", help="results for --app-root")
    parser.add_argument("--base-out", help="results for --base-root")
    parser.add_argument("--budgets", default=str(HERE / "perf_budgets.json"))
    parser.add_argument("--runs", type=int, default=None)
    parser.add_argument("--port", type=int, default=18870)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ready-file", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(Path(args.app_root).resolve(), args.port, Path(args.ready_file))
        return
    if not args.out:
        parser.error("--out is required")
    if not os.environ.get("CTM_PERF_DATABASE_URL"):
        raise SystemExit("Set CTM_PERF_DATABASE_URL to a disposable PostgreSQL cluster (never CTM live data).")
    drive(args)


if __name__ == "__main__":
    main()
