# Issue 308, step 2: background loading (frontend task 2)

## Layout statement
- No screen layout changes. The change is the data layer in front of `api()`, so no Plenix template applies.
- Pages draw what they drew last time at once, then check quietly; nothing visible is added.
- Loading states stay as they are (D-0064, delayed spinner); a quiet refresh shows no loading state.

## Files
- `static/ctm/data.js` (new): the tab's memory store (allow-list, fresh 10 s, kept 5 min, 50 entries, background at most 2).
- `static/ctm/app.js`: the raw call is `fetchApi`; `api` is the store's wrapper. The session sets the account, and a 401 clears it. The shell's list pages are tracked and refreshed quietly.
- `static/ctm/council.js`: `useLoad` is tracked and refreshed quietly, never under unsaved edits (`unsavedDrafts`). Home loads the case list and the next session's agenda ahead.
- `tribunal/templates/tribunal/shell.html`: loads `data.js` first.
- `tests/frontend/data-store.test.cjs` (new); `tests/frontend/council-shell.test.cjs` (the raw function's new name).

## State matrix
| Region | Loading | Quiet refresh | Error | Unsaved edits |
|---|---|---|---|---|
| Council pages (`useLoad`) | unchanged (`loadingView`) | data swapped in, no loading state | refusal shows the existing error; a lost connection keeps what is shown | no redraw |
| Shell list pages | unchanged | data swapped in | as above | no forms on these pages |

## Privacy
- Memory only: no local or session storage, IndexedDB or service worker; `cache: "no-store"` is kept.
- Kept per account: another account, a 401 or any save clears everything.
- Never kept or loaded ahead: files, assessments, medical, audit, timeline, notifications, decisions, votes, decrees, payments, messages, the session, application records.

## Evidence
- Ran: `node scripts/check_frontend_contract.cjs --base origin/main` (OK), `node scripts/check_i18n.cjs --base origin/main` (0 new), `node scripts/check_registry.cjs` (OK), `node --check` on the changed scripts.
- Skipped locally (owner rule: tests run in CI): `node --test tests/frontend/*.test.cjs`, browser checks. CI runs them on the PR.
- Planned: before/after timings on the fixture (revisit of case list, Home -> case list).
- Strings added: none.

## Gaps
- Loading a case ahead on row hover needs a DataGrid row-hover or row-focus event (Plenix request; CTM#310 is related).
- Session in the page HTML: backend request on #308.
