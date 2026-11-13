# Tidy-up check of open CTM3 screen issues (#348)

Checked 2026-11-13 against `main` at bcc8e79 (Plenix CDN 1.8.0). Verification only: no product code changed.

**Ran:** read the code on `main` and each issue thread; one verdict comment posted on each issue.
**Skipped:** desktop browser look and new screenshots. The agent host has no Playwright, uv or PostgreSQL, so no screenshot path exists. Earlier screenshots are on the `ci-screenshots` branch (see #193, #194).

| Issue | Verdict | What is left or what delivered it |
|---|---|---|
| #193 Side nav too wide | done | PRs #192, #207 (D-0047, D-0048) |
| #194 Spacing on case page | done | PR #202; seeder fixed |
| #195 Read-only labels | partly done | Plenix 1.1.0 + PR #275 done; shorter labels not applied |
| #197 Textarea alignment | done | Plenix 1.1.0 (pds#947); no browser re-check |
| #198 Grey bar behind actions | done | Plenix 1.1.0 (pds#948); no CTM override |
| #217 D-0050 sweep | partly done | spouse cards, #268 gaps, post-release screenshots |
| #240 Spouse cards | partly done | title still has CTM ID and portal badge, no role badge, photo control, header click workaround |
| #242 Timeline | done | PR #277, #306 |
| #259 Unassigned | done (code) | PR #276; placeholder cut still open as pds#993, needs browser look |
| #260 Parties' photos | done | PR #278 |
| #263 Back item | partly done | other panes still use ghost Buttons |
| #264 Plenix 1.2 alignment | partly done | all four workarounds still on `main` |
| #268 D-0050 gaps | not done | icon-less Panel, "Label: value" texts remain |
| #272 No skeletons | done | PR #282 |
| #273 PropertyGroup tiles | done | PR #275; guard test not found |
| #310 Row hover | done (Plenix) | Plenix 1.7.0 (pds#1187), CTM on 1.8.0; no CTM change needed; no browser look |
| #184 Actions column, Close label | not done | `kind: "center"`, 240px caps, `closeLabel: "Cancel"` |
| #110 "#" column width | partly done | still `5rem`; needs browser look on 1.8.0 |
| #220 Presiding photo | not done | person icon only |

Done and ready for the PM to close: #193, #194, #197, #198, #242, #260, #272, #273, #310 (and #259 once pds#993 is confirmed).
