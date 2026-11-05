"""Build the CTM 3.0 dashboard web page (GitHub Pages) from GitHub only (D-0031).

Writes a static site: index.html (Plenix from the CDN at the version pinned in
ctm/settings.py), app.js, data.js (window.CTM_DATA), data.json (the same, fetched by the open page)
and the latest CI screenshots.
The owner's answers come back as "**Answer to <id>: <choice>**" comments in the
decision's own issue; this script reads them so answered decisions leave "To decide".

Run (CI):  uv run --no-project --with pyyaml==6.0.3 python scripts/build_dashboard_page.py --out _site
Needs GH_TOKEN and GITHUB_REPOSITORY. Reads public repository data only; writes no secrets.
Set CTM_LOCAL_URL (e.g. http://localhost:8004) to also probe a local CTM.
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dashboard" / "page"
REPO = os.environ.get("GITHUB_REPOSITORY", "LighthouseCollection/CTM")
LIVE = "https://ctm.lighthouseway.org"
PAGES = "https://lighthousecollection.github.io/CTM/"

CARD_HEAD = re.compile(r"^\*\*(D-\d{4}) · (.+?)\*\*\s*$", re.M)
CARD_OPT = re.compile(r"^\*\*([A-Z])( \(Recommended\))?\*\* — (.+)$", re.M)
CARD_APPLIED = re.compile(r"\*\*Applied: ([A-Z])\.\*\*")
CARD_CONTEXT = re.compile(r"^Context: (.+)$", re.M)
ANSWER = re.compile(r"\*\*Answer to (\S+): ([^*]+)\*\*")


def gh(*args):
    out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True, encoding="utf-8", cwd=ROOT).stdout
    return json.loads(out) if out.strip() else None


def probe(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ctm3-dashboard"}), timeout=10) as r:
            return {"code": r.status, "body": r.read(2000).decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"code": e.code, "body": ""}
    except Exception as e:  # noqa: BLE001 - an unreachable site is a status, not a failure
        return {"code": 0, "body": type(e).__name__}


def version(p):
    try:
        return json.loads(p["body"]) if p["code"] == 200 else None
    except ValueError:
        return None


def label(labels, prefix):
    return [n[len(prefix):] for n in labels if n.startswith(prefix)]


def plenix_base():
    m = re.search(r'^PLENIX_BASE\s*=\s*"([^"]+)"', (ROOT / "ctm" / "settings.py").read_text(encoding="utf-8"), re.M)
    if not m:
        sys.exit("ctm/settings.py: PLENIX_BASE not found")
    return m.group(1)


def owner_decisions(open_numbers, owner_input):
    """Decision cards on open issues plus owner input still needed; newest card per decision id."""
    found, answers = {}, {}
    for n in open_numbers:
        issue = gh("issue", "view", str(n), "--json", "number,title,url,body,comments")
        posts = [{"body": issue["body"] or "", "at": "", "url": issue["url"]}] + [
            {"body": c["body"] or "", "at": c["createdAt"], "url": c.get("url") or issue["url"]} for c in issue["comments"]]
        for post in posts:
            m = ANSWER.search(post["body"])
            if m:
                rest = post["body"][m.end():].replace("_Sent from the CTM 3.0 dashboard._", "").strip()
                answers[m.group(1)] = {"choice": m.group(2).strip(), "text": rest[:500], "at": post["at"], "url": post["url"]}
        for post in posts:
            head = CARD_HEAD.search(post["body"])
            if not head or "(Recommended)" not in post["body"]:
                continue
            applied, ctx = CARD_APPLIED.search(post["body"]), CARD_CONTEXT.search(post["body"])
            found[head.group(1)] = {
                "id": head.group(1), "title": head.group(2), "issue": n, "url": issue["url"],
                "context": ctx.group(1) if ctx else "",
                "options": [{"key": m.group(1), "recommended": bool(m.group(2)), "text": m.group(3).strip()}
                            for m in CARD_OPT.finditer(post["body"])],
                "applied": applied.group(1) if applied else "", "at": post["at"],
            }
    for card in owner_input:
        if card["issue"] in open_numbers:
            found.setdefault(card["id"], {**card, "url": f"https://github.com/{REPO}/issues/{card['issue']}", "applied": "", "at": ""})
    for d in found.values():
        a = answers.get(d["id"])
        d["answer"] = a if a and a["at"] >= (d["at"] or "") else None  # counts only after the card
    return sorted(found.values(), key=lambda d: d["id"])


def decision_rows(runs, bd):
    rows = []
    for d in yaml.safe_load((ROOT / "decisions.yaml").read_text(encoding="utf-8"))["decisions"]:
        c = d.get("check")
        state, url, check = "review", None, d.get("review_only", "")
        if c:
            kind, ref = c.get("kind"), c.get("ref", "")
            check = ref
            if kind == "ci-job":
                wf, job = ref.split("#", 1)
                state, url = bd.job_result(runs, wf, job)
            elif kind == "workflow":
                r = runs.get(Path(ref).name)
                state, url = (r.get("conclusion"), r.get("html_url")) if r else ("no run yet", None)
            elif kind == "test":
                state, url = bd.job_result(runs, ".github/workflows/backend.yml", "postgres")
            else:
                state = "present"
        rows.append({
            "id": d["id"], "date": str(d.get("date", "")), "area": d.get("area", ""), "decision": d.get("decision", ""),
            "by": d.get("decided_by", ""), "status": d.get("status", ""), "superseded_by": d.get("superseded_by", ""),
            "check": check, "kind": (c or {}).get("kind", "review only"), "state": state, "url": url,
        })
    return rows


def screenshots(out):
    shots = []
    tree = gh("api", f"repos/{REPO}/git/trees/ci-screenshots?recursive=1") or {}
    pngs = [t["path"] for t in tree.get("tree", []) if t["path"].endswith(".png")]
    if not pngs:
        return shots
    folders = {str(Path(p).parent).replace("\\", "/") for p in pngs}
    latest = max(folders, key=lambda f: int(f.rsplit("/", 1)[-1]) if f.rsplit("/", 1)[-1].isdigit() else 0)
    (out / "shots").mkdir(parents=True, exist_ok=True)
    for p in sorted(x for x in pngs if x.startswith(latest + "/")):
        name = Path(p).name
        urllib.request.urlretrieve(f"https://raw.githubusercontent.com/{REPO}/ci-screenshots/{p}", out / "shots" / name)
        shots.append({"name": Path(p).stem, "file": "shots/" + name, "run": latest,
                      "url": f"https://github.com/{REPO}/blob/ci-screenshots/{p}"})
    return shots


def build(out):
    plan = yaml.safe_load((PAGE / "plan.yaml").read_text(encoding="utf-8")) or {}
    order = [o["issue"] for o in plan.get("order", [])]
    nexts = {o["issue"]: o["next"] for o in plan.get("order", [])}
    now = dt.datetime.now(dt.timezone.utc)

    issues = gh("issue", "list", "-s", "open", "-L", "200", "--json", "number,title,labels,url,updatedAt")
    tasks = []
    for i in issues:
        names = [x["name"] for x in i["labels"]]
        if {"dashboard", "daily-summary"} & set(names):
            continue
        tasks.append({
            "number": i["number"], "title": i["title"], "url": i["url"], "sev": (label(names, "sev:") or ["S4"])[0],
            "type": (label(names, "type:") or [""])[0], "areas": label(names, "area:"),
            "owners": label(names, "agent:ctm3-"), "decision": "decision" in names,
            "next": nexts.get(i["number"], "See the issue"), "waiting": "", "updated": i["updatedAt"],
        })
    tasks.sort(key=lambda t: order.index(t["number"]) if t["number"] in order else 100 + int(t["sev"][1:]) * 1000 + t["number"])
    for n, t in enumerate(tasks, 1):
        t["rank"] = n

    since = (now - dt.timedelta(days=3)).strftime("%Y-%m-%d")
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_dashboard as bd  # the pinned issue's check logic, shared

    runs = bd.latest_main_runs()
    live = probe(LIVE + "/")
    sites = {
        "live": {"url": LIVE, "code": live["code"], "version": version(probe(LIVE + "/version.json"))},
        "pages": {"url": PAGES, "code": probe(PAGES)["code"]},
    }
    local_url = os.environ.get("CTM_LOCAL_URL")
    if local_url:
        sites["local"] = {"url": local_url, "code": probe(local_url + "/")["code"],
                          "version": version(probe(local_url + "/version.json")), "note": "Runs on a PC only while its local server is started."}

    out.mkdir(parents=True, exist_ok=True)
    data = {
        "generatedAt": now.isoformat(timespec="minutes"),
        "mainSha": (os.environ.get("GITHUB_SHA") or subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip())[:7],
        "tasks": tasks,
        "ownerDecisions": owner_decisions([i["number"] for i in issues], plan.get("owner_input", [])),
        "openPrs": gh("pr", "list", "-s", "open", "--json", "number,title,url,isDraft,headRefName"),
        "mergedPrs": gh("pr", "list", "-s", "merged", "-L", "40", "--search", f"merged:>={since}", "--json", "number,title,url,mergedAt"),
        "closedIssues": gh("issue", "list", "-s", "closed", "-L", "40", "--search", f"closed:>={since}", "--json", "number,title,url,closedAt"),
        "decisions": decision_rows(runs, bd),
        "workflows": [{"name": r.get("name"), "file": wf, "conclusion": r.get("conclusion"), "url": r.get("html_url"),
                       "at": r.get("updated_at")} for wf, r in sorted(runs.items())],
        "shots": screenshots(out),
        "sites": sites,
    }
    (out / "data.js").write_text("window.CTM_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    # the open page fetches data.json every 30 seconds to show each rebuild without a reload
    (out / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    (out / "index.html").write_text((PAGE / "index.html").read_text(encoding="utf-8").replace("__PLENIX_BASE__", plenix_base()), encoding="utf-8")
    shutil.copyfile(PAGE / "app.js", out / "app.js")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"tasks={len(tasks)} owner={len(data['ownerDecisions'])} decisions={len(data['decisions'])} shots={len(data['shots'])} live={live['code']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_site")
    build(Path(ap.parse_args().out).resolve())
