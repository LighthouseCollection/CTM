"""Build the pinned GitHub issues that are CTM's dashboard and daily summary.

Generated from GitHub only (decision D-0002): decisions.yaml, the latest check
results on main, the ci-screenshots branch, and the last 24 hours of PRs and
issues. Read-only output; never hand-edit the issues.

Run (CI):  uv run --no-project --with pyyaml==6.0.3 python scripts/build_dashboard.py [--write]
Needs GH_TOKEN and GITHUB_REPOSITORY. Without --write it prints both bodies.
"""

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = os.environ.get("GITHUB_REPOSITORY", "LighthouseCollection/CTM")
SERVER = "https://github.com"
SHOT_BRANCH = "ci-screenshots"


def gh(*args, default=None):
    try:
        out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout
        return json.loads(out) if out.strip().startswith(("[", "{")) else out
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return default


def latest_main_runs():
    """workflow file name -> latest completed run on main (with its jobs)."""
    runs = gh("api", f"repos/{REPO}/actions/runs?branch=main&status=completed&per_page=60", default={}) or {}
    latest = {}
    for run in runs.get("workflow_runs", []):
        wf = Path(run.get("path", "")).name
        if wf and wf not in latest:
            latest[wf] = run
    return latest


def job_result(runs, wf_file, job_id):
    run = runs.get(Path(wf_file).name)
    if not run:
        return "no run yet", None
    jobs = gh("api", f"repos/{REPO}/actions/runs/{run['id']}/jobs", default={}) or {}
    wf_def = yaml.safe_load((ROOT / wf_file).read_text(encoding="utf-8")) or {}
    name = ((wf_def.get("jobs") or {}).get(job_id) or {}).get("name", job_id)
    for job in jobs.get("jobs", []):
        if job.get("name") in (name, job_id):
            return job.get("conclusion") or job.get("status"), job.get("html_url")
    return run.get("conclusion") or "unknown", run.get("html_url")


ICON = {"success": "✅ pass", "failure": "❌ fail", "cancelled": "⚪ cancelled", "skipped": "⚪ skipped"}


def check_cell(d, runs):
    c = d.get("check")
    if not c:
        return f"review only: {d.get('review_only', '')}"
    kind, ref = c.get("kind"), c.get("ref", "")
    if kind == "ci-job":
        wf, job = ref.split("#", 1)
        result, url = job_result(runs, wf, job)
        label = ICON.get(result, result)
        return f"`{job}` ({Path(wf).name}): " + (f"[{label}]({url})" if url else label)
    if kind == "workflow":
        run = runs.get(Path(ref).name)
        if not run:
            return f"`{Path(ref).name}`: no run yet"
        return f"`{Path(ref).name}`: [{ICON.get(run.get('conclusion'), run.get('conclusion'))}]({run['html_url']})"
    if kind == "test":
        result, url = job_result(runs, ".github/workflows/backend.yml", "postgres")
        return f"`{ref}` in PostgreSQL suite: " + (f"[{ICON.get(result, result)}]({url})" if url else result)
    return f"`{ref}` ({kind})"


def screenshots(limit_runs=3):
    tree = gh("api", f"repos/{REPO}/git/trees/{SHOT_BRANCH}?recursive=1", default={}) or {}
    pngs = [t["path"] for t in tree.get("tree", []) if t.get("path", "").endswith(".png")]
    groups = {}
    for p in pngs:
        groups.setdefault(str(Path(p).parent).replace("\\", "/"), []).append(p)

    def run_key(folder):
        tail = folder.rsplit("/", 1)[-1]
        return int(tail) if tail.isdigit() else 0

    out = []
    for folder in sorted(groups, key=run_key, reverse=True)[:limit_runs]:
        out.append(f"#### `{folder}`")
        for p in sorted(groups[folder]):
            url = f"{SERVER}/{REPO}/blob/{SHOT_BRANCH}/{p}?raw=true"
            out.append(f"**{Path(p).stem}**\n\n![{Path(p).name}]({url})\n")
    return "\n".join(out) or "_No screenshots yet._"


def dashboard_body():
    data = yaml.safe_load((ROOT / "decisions.yaml").read_text(encoding="utf-8")) or {}
    items = data.get("decisions") or []
    runs = latest_main_runs()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = ["| Id | Date | Area | Decision | Decided by | Status | Enforced by |", "|---|---|---|---|---|---|---|"]
    for d in sorted(items, key=lambda x: x.get("id", "")):
        status = d.get("status", "")
        if status == "superseded":
            status = f"superseded by {d.get('superseded_by')}"
        text = str(d.get("decision", "")).replace("|", "\\|")
        rows.append(f"| {d.get('id')} | {d.get('date')} | {d.get('area')} | {text} | {d.get('decided_by')} | {status} | {check_cell(d, runs).replace('|', '/')} |")
    gaps = [d for d in items if d.get("status") == "active" and not d.get("check")]
    gap_lines = "\n".join(f"- **{d['id']}** {d.get('review_only', '')}" for d in gaps) or "_None._"
    open_decisions = gh("issue", "list", "--repo", REPO, "--label", "decision", "--state", "open", "--json", "number,title,url", default=[]) or []
    open_lines = "\n".join(f"- [#{i['number']} {i['title']}]({i['url']})" for i in open_decisions) or "_None._"
    return f"""Generated {now} by `scripts/build_dashboard.py` from GitHub. Read-only: to change a decision, comment on its issue.

## Decisions ({len(items)})

{chr(10).join(rows)}

### Active decisions with no enforcing check ({len(gaps)})

{gap_lines}

### Open decision issues

{open_lines}

## Visual checks (latest runs)

Every screenshot CI takes is kept on the `{SHOT_BRANCH}` branch.

{screenshots()}
"""


def daily_body():
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    def search(kind, query):
        res = gh("search", kind, "--repo", REPO, *query, "--json", "number,title,url", "--limit", "50", default=[]) or []
        return "\n".join(f"- [#{x['number']} {x['title']}]({x['url']})" for x in res) or "_None._"

    merged = search("prs", ["--merged-at", f">={since}"])
    closed = search("issues", ["--closed", f">={since}"])
    opened = search("issues", ["--created", f">={since}"])
    urgent = search("issues", ["--state", "open", "--label", "sev:S1"]) + "\n" + search("issues", ["--state", "open", "--label", "sev:S2"])
    decisions = search("issues", ["--label", "decision", "--updated", f">={since}"])
    return f"""Daily summary for **{today}** (last 24 hours), generated from GitHub by `scripts/build_dashboard.py`.

### Merged pull requests
{merged}

### Issues closed
{closed}

### New issues
{opened}

### Decisions made or changed
{decisions}

### Open S1 / S2 bugs
{urgent}

Screenshots and decision checks: see the pinned **CTM dashboard** issue.
"""


def upsert(label, title, body):
    gh("label", "create", label, "--repo", REPO, "--force", "--color", "5319e7")
    found = gh("issue", "list", "--repo", REPO, "--label", label, "--state", "open", "--json", "number", default=[]) or []
    tmp = ROOT / f".{label}.md"
    tmp.write_text(body, encoding="utf-8")
    try:
        if found:
            number = str(found[0]["number"])
            gh("issue", "edit", number, "--repo", REPO, "--body-file", str(tmp))
        else:
            url = gh("issue", "create", "--repo", REPO, "--title", title, "--label", label, "--body-file", str(tmp), default="")
            number = str(url).strip().rsplit("/", 1)[-1]
            gh("issue", "pin", number, "--repo", REPO)
        print(f"{title}: #{number}")
    finally:
        tmp.unlink(missing_ok=True)


def main():
    write = "--write" in sys.argv
    dash, daily = dashboard_body(), daily_body()
    if not write:
        print(dash)
        print("\n---\n")
        print(daily)
        return 0
    upsert("dashboard", "CTM dashboard", dash)
    upsert("daily-summary", "Daily summary", daily)
    return 0


if __name__ == "__main__":
    sys.exit(main())
