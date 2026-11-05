---
name: ctm-screen-shape
description: Shape a CTM screen before anyone builds it - task, lead element, content inventory, Plenix page template, region sketch, states, wording and open decisions - with no code and no visual styling. Use for every new or reworked screen in a UI slice (ctm-product-lead writes it into brief.md).
---

# Shape a CTM screen

Method adapted (paraphrased) from pbakaus/impeccable `shape` and `layout`
(Apache-2.0), plugin87/ux-ui-agent-skills `grill-me` (MIT), educlopez/ui-craft
`shape` and state lattice (MIT), and perception-first-design's
derive-before-deciding idea. Visual styling is never decided here: Plenix owns
color, type, spacing, radius and motion.

## Mode

CTM screens are **operational** surfaces: scanability, consistency and
predictable patterns beat expression. Never propose a new visual treatment.

## Steps

1. **Read what is already decided** - `decisions/screens.md` rows for this
   screen, `docs/implementation/plenix-page-templates.md`, the locked
   navigation in `build-spec/interface-contract.md`, the glossary, and the
   permission rows. Do not ask about anything already decided.
2. **Derive before deciding** - write, for the main actor:
   - task: the one job this screen exists for, and what "done" looks like;
   - decision point: what the actor must decide here, and what they need in
     view at that moment (keep it to about 4 things); what can wait one click;
   - frequency: daily power use (council staff) vs once-in-a-lifetime
     (applicant) - this sets density.
3. **Lead element** - name the one thing that leads (e.g. case number + parties
   + status; the next session's agenda). One primary action per view.
4. **Content inventory** - every field/action with priority: **P0** visible on
   first view, **P1** one click away, **P2** rarely needed. Content reality:
   empty, one, many, longest string (long Arabic names, long case titles),
   missing optional values, mixed Arabic/Latin ids.
5. **Template** - pick the Plenix page template from the map. If none fits,
   say which capability is missing (it goes to `plenix-requests.md`).
6. **Region sketch** - a text sketch of regions, not pixels, for desktop and
   mobile, LTR and RTL:
   ```
   [EntityHeader: case no · parties · status · manager]   [ActionBar: primary | more ▾]
   [Section nav] | [PropertyList P0] [P1 in expandable sections]
   ```
7. **States** - list each one this screen can reach: loading, empty (first use
   / filtered / cleared), error with retry, forbidden, read-only closed
   proceeding, draft, conflict (409 / stale version), processing unavailable,
   success. Name the Plenix state component for each.
8. **Wording** - verbs on buttons that name the action and object ("Issue
   decree", never "OK"); errors say what happened, why, what to do; empty states
   give the next action. Reuse glossary terms; list new terms with EN and AR.
9. **Irreversible actions** - list them (send, issue, release, vote, submit,
   withdraw) with confirmation and audit behavior.
10. **Choices the builder must not invent** - list them. Each is either already
    decided (cite the row), a default assumption, or an **owner question** for
    `ctm-owner-interview`.

## Output (into the slice brief, "Screen spec" section)

```
Screen: <name / route>   Actor(s): ...   Template: <doc id>
Task / decision point / frequency: ...
Lead element: ...        Primary action: ...
Inventory: P0 ... | P1 ... | P2 ...
Content reality: ...
Region sketch (desktop / mobile, LTR / RTL): ...
States -> Plenix component: ...
Wording (EN | AR, new terms): ...
Irreversible actions: ...
Builder must not invent: decided(<row>) | default(<value>) | OWNER-Q<n>
```

Keep it under one page per screen. No colors, sizes, fonts or CSS.
