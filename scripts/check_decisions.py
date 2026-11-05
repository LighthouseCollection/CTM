"""Decision coverage check: every decision in decisions.yaml is valid and names
the check that enforces it (or a review_only reason), and that check exists.

Run: uv run --no-project --with pyyaml==6.0.3 python scripts/check_decisions.py
Exit 1 on any problem. Decisions without an enforcing check are listed (not a
failure when they carry a review_only reason).
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["id", "date", "area", "decision", "why", "decided_by", "status"]
STATUSES = {"active", "superseded", "retired"}
KINDS = {"ci-job", "workflow", "test", "hook", "script", "config"}


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def check_ref(kind, ref):
    if kind == "ci-job":
        if "#" not in ref:
            return f"ci-job ref '{ref}' must be '<workflow>#<job>'"
        wf, job = ref.split("#", 1)
        p = ROOT / wf
        if not p.is_file():
            return f"workflow {wf} does not exist"
        jobs = (load(p) or {}).get("jobs") or {}
        return None if job in jobs else f"job '{job}' not in {wf} (jobs: {', '.join(jobs)})"
    return None if (ROOT / ref).exists() else f"{kind} {ref} does not exist"


def main():
    data = load(ROOT / "decisions.yaml")
    items = data.get("decisions") or []
    problems, gaps, ids = [], [], set()
    for i, d in enumerate(items):
        did = d.get("id", f"#{i + 1}")
        for key in REQUIRED:
            if not d.get(key):
                problems.append(f"{did}: missing '{key}'")
        if not re.fullmatch(r"D-\d{4}", str(did)):
            problems.append(f"{did}: id must look like D-0001")
        if did in ids:
            problems.append(f"{did}: duplicate id")
        ids.add(did)
        if d.get("status") not in STATUSES:
            problems.append(f"{did}: status must be one of {sorted(STATUSES)}")
        by = str(d.get("decided_by", ""))
        if by != "owner" and not by.startswith("agent:ctm-"):
            problems.append(f"{did}: decided_by must be 'owner' or 'agent:ctm-<role>'")
        check, review = d.get("check"), d.get("review_only")
        if not check and not review:
            problems.append(f"{did}: needs a 'check' or a 'review_only' reason")
        if check:
            kind, ref = check.get("kind"), str(check.get("ref", ""))
            if kind not in KINDS:
                problems.append(f"{did}: check.kind must be one of {sorted(KINDS)}")
            else:
                err = check_ref(kind, ref)
                if err:
                    problems.append(f"{did}: {err}")
        elif d.get("status") == "active":
            gaps.append(f"{did}: {review}")
    for d in items:
        sup = d.get("superseded_by")
        if d.get("status") == "superseded" and sup not in ids:
            problems.append(f"{d.get('id')}: superseded_by '{sup}' is not a decision id")

    print(f"Decisions: {len(items)} ({sum(1 for d in items if d.get('status') == 'active')} active)")
    if gaps:
        print(f"Active decisions with no enforcing check ({len(gaps)}):")
        for g in gaps:
            print("  -", g)
    if problems:
        print(f"Decision check FAILED ({len(problems)}):")
        for p in problems:
            print("  -", p)
        return 1
    print("Decision check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
