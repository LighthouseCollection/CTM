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

Status values: `Locked`, `Superseded YYYY-MM-DD`, `Applied`, `Partially applied`.

Seed this from `docs/implementation/reviews/owner-clarifications-*.md`,
`docs/architecture/CTM-council-navigation-and-layout.md` and the integration
screen map when the first UI slice runs.
