# Council demo walkthrough

A step-by-step path through the council workspace that follows the governance demo acceptance order. It is meant for integration testers on the combined build (real API, synthetic demo records). Each step names the screen, the acting role and what to confirm. Steps that depend on backend PR #7 contracts are marked **(PR #7)**.

Roles: **S** admin/secretary, **P** President, **M** assigned council member (case manager), **O** other council member.

| # | Role | Screen | Do | Confirm |
|---|---|---|---|---|
| 1 | S | Home | Open "Review applications" from Needs attention | Queue lists only submitted petitions (no later petitions) |
| 2 | S | Completeness review | Open an application; try Return with empty instructions; then Return with text, or Accept | Empty return is blocked; applicant name, submission time, labels and manifest shown **(PR #7)**; download only for clean files |
| 3 | S | Tribunal Sessions | Create a session on a free date; try the same date again | One session per date; upcoming/past grouping |
| 4 | S | Session | Add the accepted case to Part 1; Record assignment (member + authorizer) | Authorizer list and record control follow F15 flags **(PR #7)**; same person may authorize and record |
| 5 | S | Session | Record attendance; add an assigned case to Part 2 | Agenda reloads after each attendance save |
| 6 | M | Session | Present case (needs own attendance as present); open Recommendations and update | Formal hearing title; first save offers Send Immediately / Send after council session **(PR #7)**; per-hearing attendance shown |
| 7 | M | Session | Schedule testimony (times on the session date) | Overlap and end-before-start blocked; invitation listed with response state |
| 8 | S | Session | Reschedule session (new date, reason, new times for every invitation) **(PR #7)** | Moves to the replacement session |
| 9 | M | Case → Reports → Requests | New request: applicant intake (template, topic/category view) or in-person interview **(PR #7)**; Send / Start | Foundational questions locked; Arabic blocked without approved wording; frozen snapshot shown |
| 10 | M | Case → Petition | Read both spouses' submissions; add an internal note; edit own note **(PR #7)** | Findings listed read-only **(PR #7)** |
| 11 | M | Case → Professional Assessments | Request a psychological assessment | Contents hidden without council-scope release; never in ordinary Reports |
| 12 | M | Case → Communications | Send a message (individual or both spouses); record a call | Exact send options; call time stored with time zone |
| 13 | M or S | Case → Decision & Voting | Record type, grounds and per-spouse entitlements | Deferred not offered; nullity requires both certificates |
| 14 | O, M | Decision & Voting | Each votes; S records a vote on behalf of a member | Full roster always listed; tally updates; former members' votes kept |
| 15 | P or S | Decision & Voting | President approves (or S records President's approval) | Denial warns the case will close |
| 16 | S | Case → Decree | Store signed PDF → safety check → signature record → Issue | Each step gated; issuance closes the case; certificate stays hidden |
| 17 | S | Decree | Release to the entitled spouse; withdraw if released in error; reload | Release history persists after reload **(PR #7)**; notice-only spouse has no control |
| 18 | S | Archived → case → Appeals | Pending appeal or later petition: record Accept/Decline against the heard hearing **(PR #7)** | Correct endpoint and wording for appeal vs later petition |
| 19 | any council | Search, Statistics, Case Audit, Timeline | Search a phrase; view counts; review audit and timeline | Search posts the phrase (no URL); counts not rates; case manager history |

Switch the interface to Arabic at any step: layout becomes right-to-left, names and references keep their own direction, and every label, notice and validation message is Arabic (decision-type labels stay in approved English with a notice until approved Arabic labels exist).

Known open items at the time of writing: reviewed Arabic question wording (D9), external priest delivery (D10), approved decree templates (D14), report authorship for revision (D19).
