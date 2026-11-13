# Master plan: CTM

Kept by the lead PM, "CTM4 - PM" (team core), under Project Plan 3.4 §4. It feeds the Ready queue and is reviewed at
every release, and whenever Backlog and Ready both run empty. Status lives on GitHub (issues, PRs, labels
`status:ready` and `status:in-progress`). This file holds the plan, not progress notes. Rewritten for CTM4 on
2026-11-13 (#339). The CTM3 version is in git history.

## 1. Vision

CTM is the diocese council tribunal's case system.
Applicants file and follow their case privately. The council (members, president, secretary and admin) runs initial
review, sessions, hearings, votes, decrees and appeals in one place, in English and Arabic. The server and the
database enforce permissions. The app looks and behaves like Plenix, at the version pinned in `ctm/settings.py`.

## 2. Users and outcomes

1. An applicant files, corrects and follows a case without paper, and never sees another applicant's data (the permission and RLS test suites stay green).
2. The secretary prepares and runs a council session entirely in CTM: agenda, attendance, outcomes and adjournment (session behavior tests; the member's review of the session screens).
3. Council members sign in with Microsoft only, and get session reminders with a calendar invite they can confirm (D-0036 tests; the first real reminder delivered).
4. Every screen works the same in English and Arabic on the pinned Plenix CDN, and feels fast (i18n check with 0 problems; CDN smoke test in EN/AR; the speed budget check passes, #314).
5. The live site always runs current `main`, deployed by CI with backup and rollback after a member merges (a deploy run per merge; `/version.json` matches `main`).

## 3. Scope and non-goals

**In scope:** the applicant portal, the council portal, sessions and hearings, decrees, appeals, email communications
(and text messages once a provider exists), EN/AR, the Plenix UI, and speed.

**Non-goals:** mobile layouts (desktop only, member's decision), passwords (Microsoft only for the council), telephone
integration (a manual call log instead), replacement decrees, and invented institutional wording.

## 4. Milestones

| Milestone | Epics | State |
|---|---|---|
| M0 Foundation (CTM4 Phase 0, gate G0) | E-00 | current |
| M1 Fast and finished screens | E-09, E-10, E-11 | current |
| M2 Sessions complete | E-01, E-02 | next |
| M3 Live integrations | E-03, E-04, E-05 | outline |
| M4 Acceptance | E-06 | outline |
| M5 Institutional content | E-07, E-08 | outline; waits on members and the institution |

## 5. Epics

| Id | Outcome | Packages (issues) | Milestone | Status |
|---|---|---|---|---|
| E-00 | 5 | Cutover end (PR #341, D-0075); inventory and design audit issues; the §9 checks, run or recorded N/A; launch test; dashboard | M0 | in progress |
| E-09 | 4 | Speed (#308): step 2 #342 / PR #318, step 3 (load code on demand); server-paged lists #312 / PR #317; optimistic saves #313 (after #342) | M1 | in progress |
| E-10 | 4 | Screen fixes the member asked for: footer #324 / PR #327; historical entry layout #329 / PR #333; Home cards #323 / PR #326; Key Dates #239; Settings > Users #328 / PR #331 (member picks) | M1 | in progress |
| E-11 | 5 | Repository clean-up #337 (repository files only; the folders on the old server belong to a member); close stale CTM3 issues and PRs | M1 | ready |
| E-01 | 2 | Session screen polish: #110 (waits on Plenix PLX-024/025), #115 | M2 | open |
| E-02 | 3 | Session reminders, .ics invite and attendance confirmation (#116, spec PR #130, D-0036) | M2 | database done; backend next |
| E-03 | 3 | Email delivery verified on the real server (#54) | M3 | open; blocks E-02 delivery |
| E-04 | 1 | Priest report link by email or text (#84, D-0033) | M3 | open |
| E-05 | 5 | Local copy equals live (#95) | M3 | code part done |
| E-06 | 1 | Acceptance items #8, #9, #10, #11, #12 and the F-series findings #155–#165 | M4 | open |
| E-07 | 4 | Institutional texts entered and approved in CTM (#81, D-0032) | M5 | open |
| E-08 | 4 | Arabic words that need a member or the institution (#120) | M5 | waits on a member |

Council features that need a spec first: case deletion (#176) and council membership settings (#175). They go into
M2 once they are specified.

## 6. Lanes and owners

From the role registry (`.agents/agents.config.yaml`):

| Lane | Role | Gate |
|---|---|---|
| spec | `pm` | G1 |
| design | `design-director` | G2 |
| architecture | `architect` | G3 |
| plan | `delivery-lead` | G4 |
| build | `engineer`, `database-engineer` (migrations, RLS and grants only) | PR open |
| locale | `i18n-engineer` | G6 |
| docs | `technical-writer` | G7 |
| verify | `code-reviewer`, `qa`, `design-critic`, `accessibility-auditor`, `security-reviewer` | G5a–G5e |

No release role is registered. Releases are the CI deploy that runs on every merge to `main`, and a member merges.
When slots are scarce, the PM follows the registry's `priority` order, and each active lane keeps `ready_min` Ready items.

## 7. Evergreen backlog

Recorded needs only (plan §4.5):
- Browser scripts that no longer match the app, and none run in CI (#51, DR-009)
- Plenix requests PLX-024 and PLX-025 (`docs/implementation/plenix-requests.md`)
- The CTM3 role registry is still checked by CI (`agents.config.yaml`, `.claude/agents/ctm3-*.md`). Retire it in one PR that updates D-0025 and D-0041 (`docs/project-rules.md`)
- `scripts/db_owner_guard.cjs` still expects the CTM3 label `agent:ctm3-database-engineer`
- The generated `.agents/RULES.md` states a Plenix version that differs from the pin in `ctm/settings.py`. It is regenerated from the intake by a member, not edited

## 8. Risks and open decisions

- No email provider is configured (#54), so reminders, notices and report links can't be delivered yet.
- There is no staging site (D-0038): every merge goes straight to live, and rollback is the safety net.
- Arabic legal terms need the institution (#120).
- Waiting on a member: merge #341 (ends cutover); pick a Settings > Users design (#328 / PR #331); choose how the live account clean-up runs (#299 / PR #332).

## 9. Change log

- 2026-11-06: skeleton created from template v2.4 (CTM3).
- 2026-11-13: rewritten for CTM4 (#339). Added M0 and M1 (speed and the screen fixes the member asked for), the lane table from the CTM4 registry, and the risks waiting on a member.
