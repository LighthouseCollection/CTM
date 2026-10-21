# CTM parallel build governance

Repository: https://github.com/LighthouseCollection/CTM

This governance chat coordinates three implementation streams. GitHub issues,
pull requests and committed documentation are the shared record across machines.
Each stream uses its own checkout and branch, based on current main. Never share
a working directory between agents. The old CTM/ctm-alpha prototype is a reference,
not the application checkout.

## Ownership

| Stream | Owner | Branch | Scope |
| --- | --- | --- | --- |
| Applicant portal | Codex on Desktop-R | work/desktop-r-applicant | Applicant screens, form rendering, draft/review/submission/returned application UI, own attachments and payments UI |
| Backend and security | Codex on VM-FRM | work/vm-frm-backend | APIs/services, migrations, PostgreSQL policies/grants, payment/provider integration, worker contracts and deployment readiness |
| Council workspace | Claude | work/claude-council | Review/return, sessions/assignment/hearings, reports, decisions/decree UI and communications |

Governance owns cross-stream contracts, shared shell integration, integration
testing, merge decisions and operational deployment. Microsoft login is verified
locally for frraphaelmaher@lacopts.org; the public route is not yet deployed.

## Collision rules

- VM-FRM alone authors schema migrations and shared backend changes. UI streams
  request missing API behavior on their issue with an example request/response.
- Keep applicant/council frontend code in separate modules. Propose a small shell
  integration patch rather than having both streams rewrite static/ctm/app.js.
  Governance coordinates shared script loading and navigation hooks.
- Do not modify protected docs/architecture/build-spec sources, replace the
  accepted question bank, introduce passwords or substitute another design system.
- Use pinned Plenix CDN0.58.0 and documented components/tokens; English/Arabic and
  RTL remain required. No invented visual values or copied CDN components.
- OCR and audio recording are low priority; clearly labelled placeholders are
  accepted. File ownership, access controls and scan requirements remain enforced.
- Never represent a fake payment, email, scan or transcription as successful.
- Do not merge your own PR, push implementation directly to main, deploy to the
  operational VM, run operational migrations or change credentials independently.

## Working cycle

1. Read approved schema, permissions, interface and acceptance contracts, then
   inspect current implementation. Preserve established behavior.
2. Claim scope on the stream issue. Post a concrete first slice and any shared
   file/API dependencies before editing shared surfaces.
3. Implement a small usable slice, with meaningful permission/business regression
   checks and browser checks for UI. Push the branch and open a draft PR early.
4. Reference the stream issue in the PR. Report implemented behavior, checks,
   remaining work and blockers. Never include secrets or case data.
5. If blocked, record the dependency and proceed with independent authorized work.
   Do not silently weaken requirements to make tests pass.
6. Governance reviews, integrates serially, runs PostgreSQL CI and end-to-end
   browser checks, and updates the tracker. Main should remain usable.

## Demo acceptance order

Applicant draft -> required files -> declaration/payment or authorized waiver ->
submission -> completeness review/return/resubmission -> council session/assignment
-> investigation/reports/communications -> hearing/type/grounds/votes/presidential
approval -> signed decree PDF/issuance/closure/explicit release -> appeals.

Genuine login is local verified. Full151-table reconciliation, RLS/grants, live
payment/email and public deployment acceptance remain incomplete. A passed local
synthetic browser script is not evidence of production readiness.
