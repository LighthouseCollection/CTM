# Screen decisions register

One accepted decision per screen element. Builders and the UI finish gate treat
these as **locked**: a layout that stays stable is part of the product's
trustworthiness, and CTM lost many commits to toggled icons and layouts.

- Only explicit owner decisions go here (from `ctm-owner-interview`, owner
  clarifications or issue comments quoted with a link) - not discussions or
  proposals.
- Changing a decision needs a new dated owner decision: mark the old row
  `Superseded YYYY-MM-DD` and add a new row. Never edit or delete old rows.
- `Applied in` names the commit or file that implements the decision, so the
  drift auditor can check it.
- Maintained by `ctm3-product-lead` and the team lead; audited by `ctm3-drift-auditor`.

| Date | Screen | Element | Decision | Why | Source | Status | Applied in |
|---|---|---|---|---|---|---|---|
| 2026-10-22 | Council case overview (Marriage, Separation, Summary) | Shared facts | Shown once from the first formal submission; discrepancy marker opens both spouses' values and sources | D-0029 | [#14 owner comment](https://github.com/LighthouseCollection/CTM/issues/14#issuecomment-6332044146) | Locked | Not built |
| 2026-11-04 | Council request: external priest report | Private link panel | No on-screen or copy link; email when working, else paper form | D-0030 | #10 decision card | Locked | Not built (#55) |
| 2026-11-05 | All CTM screens | Page templates | Every screen uses the Plenix CDN page template for its kind (lists, records, settings, forms, sign-in) at the pinned version; documented components and tokens only | D-0034 | Owner, Product Lead session 2026-11-05 (#97) | Locked | In progress (#97) |
| 2026-11-05 | Applicant application form | Page template | `Wizard` (wizard.md): Your answers (server order, unchanged validation) → Documents → Review answers; completing the wizard is the existing Review gate for filing; `DraftState` shows the saved version and confirms discarding unsaved edits; filing, lifecycle, payments and supplements stay below | D-0034 | #97 slice 5 | Applied | #97 slice 5 |
| 2026-11-05 | Applicant portal lists | Page templates | Decrees and documents on `FileList`; notifications on `ResourceList`; appointments and requests on `CTMShell.Workspace` (list + reading pane, `EmptyState` when nothing is listed); payment history and answer history on `CTMShell.Table` | D-0034 | #97 slice 5 | Applied | #97 slice 5 |
| 2026-11-05 | Council case lists, case summary, separation details | Separation grounds | Grounds are shown as EN/AR labels (Infidelity; Abandonment; Abuse; Leaving or changing the faith; Addiction; Misrepresentation or concealment before marriage), never the stored code; "Desertion" is renamed "Abandonment" and the old code reads as Abandonment | D-0035 | Owner, Product Lead session 2026-11-05 | Applied | `static/ctm/council.js` `groundsText` (#120) |

Status values: `Locked`, `Superseded YYYY-MM-DD`, `Applied`, `Partially applied`.

Seed this from `docs/implementation/reviews/owner-clarifications-*.md`,
`docs/architecture/CTM-council-navigation-and-layout.md` and the integration
screen map when the first UI slice runs.
