# Plenix CDN — current pin and later changes

`CTM-Plenix-CDN-contract.md` is the owner's original contract (2026-10-20, pinned
0.58.0). It is a registered build-spec source: its sha256 is pinned in
`docs/architecture/build-spec/source-register.json` and checked by
`validate_spec.py`, so **do not edit it**, nor the other registered files that link to it.
Changes since the contract go here.

- **Current pin:** `PLENIX_BASE` in `ctm/settings.py` is the only source of truth.
  `scripts/bump_plenix.cjs` (`.github/workflows/plenix-upgrade.yml`) updates every
  pin outside `docs/`. Pin history: 0.58.0 (2026-10-20), 0.68.0, 0.76.0 (owner,
  2026-10-30, CTM-5), then automatic upgrades.
- **Load order** (after the contract's six assets, same pinned base):
  `plenix-icons-plenix.js` registers the Plenix icon set so icons draw at once
  (Plenix 0.74.0). `plenix-engines.js` loads the rich-text, chart and PDF engines
  (0.74.0). Load the engines only on a page that shows one of them; the
  external report page does not.
- **Icons:** draw through the `Icon` component (`<Icon name>`), or
  `Plenix.iconMarkup(icon)` where a page writes HTML. `icons-all.css` is no longer
  published, and bare `plx-icon--<name>` classes draw nothing since 0.74.0.
