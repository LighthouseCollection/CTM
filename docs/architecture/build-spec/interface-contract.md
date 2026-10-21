# Locked interface contract

One sign-in entry, role-routed workspace, no portal chooser. Application role comes from verified server account authorization; email/domain alone does not grant council access.

## Council navigation

```text
Home
Tribunal Sessions
Cases
Search
Archived
Statistics and Reports
```

Cases is a workspace list/table, never a nested case list in the navigation. Opening a case changes the sidebar scope:

```text
Back to Cases
Case Overview
  Summary
  Timeline
  Parties
  Marriage
  Separation
Communications
Case Review
  Petition
  Reports
  Hearings
  Evidence
  Documents
  Professional Assessments
Decision
  Decision & Voting
  Decree
  Appeals
Case Audit
```

Persistent sidebar-footer avatar/name button, only if supported by documented Plenix shell. Opens My Profile, Account Settings, CTM Settings where authorized, System Audit for admin/secretary, Sign Out. Do not permanently show menu items or duplicate avatar in header.

Home: My Cases, Needs Attention, Upcoming Council Session, Outstanding Requests; admin/secretary have tribunal overview. Use prototype useful upcoming/previous-session and new-submission content, move larger analytics to Statistics and Reports. Never imply a divorce rate from tribunal cases without a valid population denominator.

| Destination | Layout rule |
|---|---|
| Reports | Confirmed split list/detail; completed reports separate from requests. Detail tabs for report/answers, recording, transcripts/translations, attachments/history as applicable. |
| Search and Appeals | Confirmed split list/detail preview. |
| Communications, Evidence, Documents, Professional Assessments | Consistent recommended split list/detail; finalize exact component against published Plenix docs. |
| Case Overview pages, Petition | Structured overview/forms/timeline, no forced split. |
| Decision & Voting, Decree | Action/document workspace with role-gated controls. |
| Hearings | List/detail navigation; split layout not separately locked. |
| Case Audit | Searchable audit event list. |

Applicant capabilities are locked, but a detailed new applicant navigation shell was not separately approved. Implement action-focused current workflow, separate past cases, private timeline/messages, contextual documents, own fees/receipts, appointments with Confirm/Reject, own appeals/supplements, released PDF decree and account settings. Do not design a home that assumes draft, open initial case and pending appeal are universally concurrent; preserve explicit sibling-appeal exceptions instead of imposing a simplistic global one-screen state.

Plenix CDN0.58.0 is mandatory. Read `../CTM-Plenix-CDN-contract.md` before frontend work, including exact load order and token rules. Use published components, no legacy CSS transplant, unapproved fallback component or runtime inline style. React viewer/recorder integration cannot silently override design-system rules. Isolate approved Arabic RTL patch for later CDN replacement. UI bundles include equivalent English/Arabic for labels, forms/help, validation/errors/system notices, not just menu text.
