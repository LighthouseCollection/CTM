# ctm3-48 — remove CTM's own styles (brief)

Issue: LighthouseCollection/CTM#48. Decision: D-0022 (owner, 2026-11-03):
remove `static/ctm/ctm.css` and inline styles, replace them with Plenix parts,
**all at once with one preview at the end**. Plenix pinned at 0.86.0
(`PLENIX_BASE` in `ctm/settings.py`).

Measured on main `aec10de`: `ctm.css` is 612 lines, 68 `ctm-*` classes, 16 Plenix internal classes reached into
(`.plx-*`), 5 `!important`, 55 raw hex color
fallbacks. CTM JavaScript has **no** inline `style` props (the two `style:`
hits are `Intl.NumberFormat` options). The only `<style>` block is the A4
print page `tribunal/templates/tribunal/priest_request_print.html` (allowed
exception until Plenix has a printable page, PLX-010).

## Acceptance

| ID | Done when |
|---|---|
| AC-1 | `static/ctm/ctm.css` is deleted and `shell.html` no longer links it |
| AC-2 | Every row of `inventory.md` is applied: the screen uses the named Plenix component/prop, no `ctm-*` styling class remains in `static/ctm/*.js` |
| AC-3 | No raw colors, numeric font sizes, inline `style`, `!important` or `.plx-*` overrides anywhere in `static/ctm/` (`check_frontend_contract.cjs`, opengrep green) |
| AC-4 | Behavior is unchanged: votes, attendance, photo change, report recipients, case edit/read, session create/edit work as before (frontend + PostgreSQL tests green) |
| AC-5 | EN and AR: every touched screen renders in both, RTL mirrored, no new strings without both languages (`check_i18n.cjs`) |
| AC-6 | The only styling left is the print template (PLX-010); "needs Plenix" items are filed (PLX-008..PLX-011, plenix-ds/pds issues) |
| AC-7 | One preview at the end: the check's EN desktop screenshots (+ AR and 390px for the screens in `design.md` §4) are posted on #48 |
