"""Speed budget verdict for the main pages (#314, owner performance rule 7).

Reads the measurements written by scripts/browser_perf_budget.py for this
change (--head) and for main (--base) plus the budgets in
scripts/perf_budgets.json, prints a Markdown report (also written to
--markdown) and exits 1 when:

- a page's LCP or TBT is over its budget and main was within it (a page that is
  already over budget on main is reported as existing debt and blocks only if
  it gets slower, the same diff-aware rule as the quality gates);
- a metric got worse than main by more than max_ratio and by more than its
  noise floor (single runs on shared CI machines jitter by a few percent);
- a number is missing on either side: unknown is never a pass.

Standard library only:
  python3 scripts/check_perf_budget.py --head .tmp/perf-head.json --base .tmp/perf-base.json --markdown .tmp/perf.md
"""

import argparse
import json
import sys
from pathlib import Path

MARKER = "<!-- ctm-speed-budget -->"
NAMES = {"lcp_ms": "LCP", "tbt_ms": "TBT", "requests": "Requests", "js_bytes": "JS"}


def load(path):
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def show(metric, value):
    if value is None:
        return "unknown"
    if metric == "js_bytes":
        return f"{value / 1024:,.0f} KB"
    if metric.endswith("_ms"):
        return f"{value:,} ms"
    return f"{value:,}"


def delta(metric, head, base):
    if head is None or base is None:
        return ""
    diff = head - base
    if diff == 0:
        return " (±0)"
    pct = f" {diff / base:+.0%}".replace("-", "−") if base else ""
    sign = "+" if diff > 0 else "−"
    size = abs(diff)
    shown = f"{size / 1024:,.1f} KB" if metric == "js_bytes" else (f"{size:,} ms" if metric.endswith("_ms") else f"{size:,}")
    return f" ({sign}{shown}{pct})"


def evaluate(config, head, base):
    """Return (rows, failures, notes). Rows are per page: label, cells, verdict."""
    budgets = config["budgets"]
    regression = config["regression"]
    ratio, floors = regression["max_ratio"], regression["noise_floor"]
    rows, failures, notes = [], [], []
    if head is None:
        failures.append("No measurements for this change (the speed run did not finish): unknown, not a pass.")
        return rows, failures, notes
    if base is None:
        failures.append("No measurements for main (the comparison run did not finish): regressions are unknown, not a pass.")
    for page in config["pages"]:
        h = (head.get("pages") or {}).get(page["id"])
        b = ((base or {}).get("pages") or {}).get(page["id"]) if base else None
        label = page["label"]
        page_fail, page_debt = [], []
        cells = []
        for metric in ("lcp_ms", "tbt_ms", "requests", "js_bytes"):
            hv = h.get(metric) if h else None
            bv = b.get(metric) if b else None
            cells.append(show(metric, hv) + delta(metric, hv, bv))
            if hv is None:
                page_fail.append(f"{NAMES[metric]} unknown")
                continue
            limit = budgets.get(metric)
            if limit is not None and hv > limit:
                if bv is not None and bv > limit:
                    page_debt.append(f"{NAMES[metric]} over {show(metric, limit)} on main too")
                else:
                    page_fail.append(f"{NAMES[metric]} over budget ({show(metric, limit)})")
            if metric in regression["metrics"] and base is not None:
                if bv is None:
                    page_fail.append(f"{NAMES[metric]} unknown on main")
                elif hv - bv > max(bv * ratio, floors.get(metric, 0)):
                    page_fail.append(f"{NAMES[metric]} {hv / bv - 1:+.0%} vs main (+{show(metric, hv - bv)})" if bv else f"{NAMES[metric]} new vs main")
        for problem in (h or {}).get("problems", []):
            notes.append(f"{label}: {problem.splitlines()[0][:300]}")
        if page_fail:
            verdict = "❌ " + "; ".join(page_fail)
            failures.extend(f"{label}: {f}" for f in page_fail)
        elif page_debt:
            verdict = "⚠️ " + "; ".join(page_debt) + " (existing debt, #311)"
        else:
            verdict = "✅"
        rows.append((label, cells, verdict))
    return rows, failures, notes


def report(config, head, base, rows, failures, notes):
    budgets, reg = config["budgets"], config["regression"]
    out = [MARKER, "## Speed budget (#314)", ""]
    out.append(("**FAIL**" if failures else "**PASS**") + " · median of "
               f"{(head or {}).get('runs', '?')} cold loads per page, fictional dataset, "
               f"{config['viewport']['width']}×{config['viewport']['height']}, real Plenix CDN.")
    out.append("")
    ident = lambda d: f"`{(d.get('commit') or '?')[:10]}` (Plenix `{(d.get('plenix_base') or '?').rstrip('/').rsplit('/', 1)[-1]}`)" if d else "unknown"
    out.append(f"This change: {ident(head)} · main: {ident(base)}")
    out.append("")
    out.append("| Page | LCP | TBT (INP stand-in) | Requests | JS (decoded) | Result |")
    out.append("|---|---|---|---|---|---|")
    for label, cells, verdict in rows:
        out.append(f"| {label} | " + " | ".join(cells) + f" | {verdict} |")
    out.append("")
    out.append(f"Budgets (`scripts/perf_budgets.json`): LCP ≤ {budgets['lcp_ms']:,} ms, TBT ≤ {budgets['tbt_ms']:,} ms; "
               f"regression over {reg['max_ratio']:.0%} vs main fails once it is also above the noise floor "
               + ", ".join(f"{NAMES[k]} {show(k, v)}" for k, v in reg["noise_floor"].items()) + ".")
    if failures:
        out += ["", "**Failures**", ""] + [f"- {f}" for f in failures]
    if notes:
        out += ["", "<details><summary>Notes from the browser</summary>", ""] + [f"- {n}" for n in sorted(set(notes))] + ["", "</details>"]
    return "\n".join(out) + "\n"


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--head", required=True)
    parser.add_argument("--base")
    parser.add_argument("--budgets", default=str(here / "perf_budgets.json"))
    parser.add_argument("--markdown")
    args = parser.parse_args()
    config = json.loads(Path(args.budgets).read_text(encoding="utf-8"))
    head, base = load(args.head), load(args.base)
    rows, failures, notes = evaluate(config, head, base)
    text = report(config, head, base, rows, failures, notes)
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
