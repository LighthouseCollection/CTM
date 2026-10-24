# Card heading icon gap — Plenix0.58.0

Status: resolved upstream in 0.60.1; documented Card.icon adopted by the UI successor branch. Original report follows.

Owner requires icons for navigation nodes and container headings. CTM now supplies documented NavList item/group icons and Panel.icon throughout its portal modules. Published CSS aliases are used, not raw Material asset filenames.

Remaining CDN requirement: CardProps in the pinned plenix.d.ts has no icon property, while PanelProps explicitly supports an icon before its heading. The published panel documentation also lists Card.title/meta/actions etc., but no Card.icon. Interactive nested cards (such as a session card inside a dashboard panel) therefore still lack the same standard icon slot.

Request: add/document a consistent Card.icon API and matching heading alignment/RTL/accessibility behavior, with CDN release notes and examples. CTM should adopt that release rather than introduce a custom card-title workaround. No Plenix files were copied/modified and no unsupported Card.icon prop was invented here.

References: https://design-system.lighthouseway.org/cdn/0.58.0/plenix.d.ts and https://design-system.lighthouseway.org/cdn/0.58.0/docs/panel.md.

Verified:180 frontend tests; actual EN/AR Home rendering, published icon alias coverage, no browser errors or horizontal overflow. This is scoped icon acceptance, not overall dashboard approval.
