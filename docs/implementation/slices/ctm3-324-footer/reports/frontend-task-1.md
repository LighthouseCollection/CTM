# Frontend task 1: the Plenix footer in the council and applicant shell (#324)

## Layout statement
- Template: the existing AppShell (`application-shell`, `page-structures-footer`) with its documented `footer` slot holding a `StatusBar` (`status-region`). No page template changes.
- What leads: page content as before; the footer is a thin line under both panes (side nav and main) naming the portal.
- Density: unchanged. Spacing above the footer is Plenix's `PageContent` bottom padding (`--plx-comp-page-content-padding-block`); no CTM CSS.

## Cause of the flush bottom
- No footer was passed to `AppShell`, so the panes ran to the window's bottom edge.
- On scrolling pages (Home and other non-list/detail pages) CTM wrapped the content in a Stack with `plx-u-flex-1 plx-u-min-h-0`. That Stack shrank below its content, the content overflowed it, and `PageContent`'s bottom padding was lost. The wrapper now keeps `plx-u-min-h-0` only on split list/detail pages (their panes scroll on their own); other pages scroll in `PageContent`, so Plenix's padding stays.

## State matrix
| Region | Loading | Empty | Error | Read-only |
|---|---|---|---|---|
| Footer (StatusBar) | static text, always shown | n/a | n/a | n/a |
Page states are unchanged (this task only adds the shell footer).

## Files
- `static/ctm/app.js`: `footer: h(P.StatusBar, { start: t(council ? "council" : "applicant") })`; `masterDetail` computed once and used for the AppShell `page` and the wrapper's classes.
- `tests/frontend/shell-footer.test.cjs`: contract test (footer is a StatusBar, existing keys, no styling, min-h-0 only on master-detail).
- `scripts/browser_shell_footer.py`: real-CDN browser check with synthetic fixtures, EN/AR, council and applicant.

## Plenix doc ids used
`page-structures-footer`, `status-region`, `application-shell`.

## Strings
No new keys. Reused `council` ("Council portal" / "بوابة المجلس") and `applicant` ("Applicant portal" / "بوابة مقدم الطلب"), already in both dictionaries.

## TDD evidence
- Ran: `node --test tests/frontend/shell-footer.test.cjs` before the change: 0 pass, 3 fail (RED). After: 3 pass. Added the min-h-0 test: 1 fail (RED), then pass after the change.
- Ran: `node --test tests/frontend/*.test.cjs`: 566 pass, 0 fail.
- Ran: `node scripts/check_frontend_contract.cjs --base origin/main`: OK (Plenix CDN 1.6.1).
- Ran: `node scripts/check_i18n.cjs --base origin/main`: 0 problems.
- Ran: `node scripts/check_ownership.cjs`: OK.
- Ran: `uv run --group browser python scripts/browser_shell_footer.py`: OK (council/applicant x EN/AR; footer present, side nav's last item and the scrolled-to-bottom content end above the footer with PageContent's padding; All Active Cases keeps its bounded column).
- Skipped: `opengrep` (not installed on this host; CI runs it).
- Skipped: `browser_smoke.py`, `browser_split_workspaces.py`, `browser_navigation.py` fail the same way on `origin/main` in this environment (connection refused / outdated sign-in heading), so they say nothing about this change.

## Screenshots (fictional data)
`.tmp/ctm-footer-{council,applicant}-{en,ar}-{before,after}[-bottom].png`, `.tmp/ctm-footer-council-en-after-cases.png`; shared on the `ci-screenshots` branch under `preview-324/` and on the PR.

## Scope self-check
- Only `static/ctm/app.js` (shared shell, the issue names both shells), a new test and a new browser script.
- No CSS, no inline style, no new strings, no backend.
- The sign-in page's AppShell is not part of the council/applicant shells and is unchanged.
