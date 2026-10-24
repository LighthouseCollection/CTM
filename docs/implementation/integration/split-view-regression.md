# Restored split workspace regression

Date: 2026-10-21. Checkout: CTM-Integration (the local preview served on port 18844).

The newer integration shell had not retained the earlier application shell's table/detail presentation. Restored the documented Plenix SplitView, DataTable and ReadingPane composition across Tribunal Sessions, Cases, Search, Archived, Communications, Reports, Hearings, Evidence, Documents, Professional Assessments, Decision & Voting, Appeals, Decree and Case Audit. Appeals was listed twice in the request; there are fourteen distinct pages.

Existing report revision, file viewer, session action, assessment request, decision/vote, decree and appeal modules remain the detail implementations. Main and case navigation remain independently collapsible. No custom split-pane CSS or additional UI library was introduced. Search retains its empty table/detail composition before a query. Reports retains its Completed/Requests tabs without shrinking the reader to content height.

## Validation

- `node --test tests/frontend/council.test.cjs tests/frontend/council-shell.test.cjs tests/frontend/council-case.test.cjs tests/frontend/council-media.test.cjs tests/frontend/council-decree.test.cjs`: 97 passed.
- `scripts/browser_split_workspaces.py`: all fourteen pages have a visible left table/right reading pane, with split height over 500px at the tested desktop viewport. Also checks session selection, case preview/open, report answer selection, file selection and audit selection. No browser page errors.
- `scripts/browser_navigation.py`: main rail/case pane remain independent.
- Browser tests used `node scripts/council_fixture.cjs 18859 secretary --contract=pr7 --decree-read`, an isolated synthetic in-memory API fixture. They do not establish production authorization, backend or database acceptance. Fixture server stopped after checks.

Fixture command and `CTM_REVIEW_URL` overrides are documented in the browser scripts. Existing broader integration changes were preserved; no merge, commit, deployment or credentialed-server restart was performed.
