# Master plan — CTM 3.0

Owner: `ctm3-product-lead`. Template v2.4 §4. The Ready queue is fed from this
plan; it is reviewed at every release and whenever Backlog + Ready runs low.
Status lives on GitHub; this file holds the plan, not progress notes.

## 1. Vision

CTM is the diocese council tribunal's case system:
applicants file and follow their case privately, and the council (members,
president, secretary, admin) runs initial review, sessions, hearings, votes,
decrees and appeals in one place, in English and Arabic, with permissions
enforced by the server and the database.

## 2. Users and outcomes

1. An applicant files, corrects and follows a case without paper, and never sees another applicant's data (measured by the permission and RLS test suites staying green).
2. The secretary prepares and runs a council session (agenda, attendance, outcomes, adjourn) entirely in CTM (session flow behaviour tests; owner review of the session screens).
3. Council members sign in with Microsoft only and are reminded of sessions with a calendar invite they can confirm (D-0036 tests; first real reminder delivered).
4. Every screen works the same in English and Arabic, on the pinned Plenix CDN (i18n check 0 problems; CDN smoke EN/AR).
5. Live always runs current `main`, deployed automatically with backup and rollback (deploy run per merge; `/version.json` matches `main`).

## 3. Scope and non-goals

In scope: applicant portal, council portal, sessions and hearings, decrees, appeals, communications by email (and text once a provider exists), EN/AR, Plenix UI.
Non-goals: mobile layouts (desktop only, owner), passwords (Microsoft only for council), telephone integration (manual call log), replacement decrees, invented institutional wording.

## 4. Milestones

| Milestone | Epics |
|---|---|
| M1 Sessions complete | E-01, E-02 |
| M2 Live integrations | E-03, E-04, E-05 |
| M3 Acceptance | E-06 |
| M4 Institutional content | E-07, E-08 |

## 5. Epics

| Id | Outcome served | Area | Milestone | Status |
|---|---|---|---|---|
| E-01 | 2 | Session screens polish (#110 waits on Plenix PLX-024/025, #115 buttons) | M1 | in progress |
| E-02 | 3 | Session reminders, .ics invite, attendance confirmation (#116, D-0036) | M1 | database done; backend next |
| E-03 | 3 | Email delivery verified on the real server (#54) | M2 | open; blocks E-02 delivery |
| E-04 | 1 | Priest report link by email or text (#84, D-0033) | M2 | open |
| E-05 | 5 | Local copy equals live, Microsoft sign-in locally (#95) | M2 | code part done |
| E-06 | 1 | Perplexity acceptance items (#8, #9, #10, #11, #12) | M3 | open |
| E-07 | 4 | Institutional texts entered and approved in CTM (#81, D-0032) | M4 | open |
| E-08 | 4 | Arabic words that need the owner or institution (#120, 17 terms) | M4 | waiting on owner/institution |

## 6. Lanes and owners

From the role registry (`agent-limits.yaml` today; `agents.config.yaml` once G-3 lands): spec — ctm3-product-lead; design — ctm3-design-director; architecture — ctm3-solution-architect; plan — ctm3-delivery-lead; build — ctm3-frontend-engineer, ctm3-backend-engineer, ctm3-database-engineer; locale — ctm3-i18n-engineer; docs — ctm3-technical-writer; release — ctm3-release-engineer.

## 7. Evergreen backlog

Recorded needs only (template §4.5):
- QA browser scripts that no longer match the app and run in no CI job (#51)
- Plenix requests PLX-024, PLX-025 (`docs/implementation/plenix-requests.md`)
- Template v2.4 process gaps G-2 .. G-11 (`docs/implementation/template-v2.4-gap.md`)
- Old worktrees left after the 2026-11-06 cleanup (`archive/CLEANUP-2026-11-06.md`, outside git)

## 8. Risks and open decisions

- Email provider not configured (#54): reminders, notices and report links cannot be delivered until it is.
- No staging stack (D-0038): merges go straight to live; rollback is the safety net.
- Arabic legal terms need the institution (#120).

## 9. Change log

- 2026-11-06: skeleton created from template v2.4 (`docs/implementation/template-v2.4-gap.md`).
