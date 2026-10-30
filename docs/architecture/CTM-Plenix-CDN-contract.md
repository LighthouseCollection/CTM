# CTM Plenix CDN contract — pinned 0.76.0

Pin history: 0.58.0 (2026-10-20, the user's original instructions below), then 0.68.0, then 0.76.0 (owner, 2026-10-30, CTM-5). Every Plenix link in CTM uses the current pin.

User-supplied integration instructions, 2026-10-20. This is the authoritative CTM presentation contract and supersedes prior speculative CDN/runtime details. CTM pins one release rather than following a mutable latest URL. No Plenix distribution/component files are copied into CTM. No frontend was scaffolded by this documentation step.

## Page bootstrap

Set the document element to `<html lang="en" data-plx-density-policy="compact">`. The html element is the document root, not a child of head. Load the following assets in head in exactly this order, without asynchronous reordering:

```html
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/theme-boot.js"></script>
<link rel="stylesheet" href="https://design-system.lighthouseway.org/cdn/0.76.0/fonts.css">
<link rel="stylesheet" href="https://design-system.lighthouseway.org/cdn/0.76.0/plenix.css">
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/vendor/react.production.min.js"></script>
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/vendor/react-dom.production.min.js"></script>
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/plenix.js"></script>
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/plenix-icons-plenix.js"></script>
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/plenix-engines.js"></script>
```

- `plenix-icons-plenix.js` registers the Plenix icon set so icons draw at once (Plenix 0.74.0). `icons-all.css` is no longer published; icons draw only through the `Icon` component or `Plenix.iconMarkup`.
- `plenix-engines.js` loads the rich-text, chart and PDF engines (Plenix 0.74.0). Load it only on a page that shows one of them; the external report page does not.

The global build provides `window.Plenix`. React and ReactDOM come from the matching pinned vendor assets; do not also inject a second bundled React runtime into the same component tree. CTM application initialization follows the dependencies. Django can serve the document shell, secure sessions, CSRF-protected endpoints and application assets under the same origin.

Bundler alternative: use `https://design-system.lighthouseway.org/cdn/0.76.0/plenix.esm.js`, with React 18 as a peer dependency, and `plenix.d.ts` for types. Choose one coherent global or ESM integration path; do not mix runtimes accidentally. No production Node server is required merely to render browser React components.

## Mandatory presentation rules

- Build only with documented Plenix components/patterns and `plx-` classes.
- Use only documented `--plx-sys-*` and `--plx-comp-*` tokens; no raw colors or numeric font sizes.
- No inline styles and no `!important`, including integration/runtime output from third-party UI libraries.
- If a needed component or value is missing, identify it and ask the user rather than inventing an equivalent component or token.
- Pin all Plenix asset/reference paths to 0.76.0. Published-version immutability is supplied by the user; no automatic upgrade occurs.
- Keep CDN library code external; record URLs and integration code, not copied source/distribution files.

## Documentation and discovery

Base: https://design-system.lighthouseway.org/cdn/0.76.0/

- Version manifest: https://design-system.lighthouseway.org/cdn/index.json
- Component index: https://design-system.lighthouseway.org/cdn/0.76.0/docs/index.json
- Component reference: `docs/<id>.md` beneath the pinned base; inspect before choosing props/patterns.
- Tokens: `tokens/tokens.json` and documented token CSS beneath the base.
- Icons: draw through the `Icon` component (`<Icon name>`), or `iconMarkup(icon)` where a page writes HTML. Bare `plx-icon--<name>` classes draw nothing since 0.74.0.
- Changelog: `CHANGELOG.md` beneath the pinned base.
- JSON API: https://design-system.lighthouseway.org/api/v1/ for tokens, components, exports, taxonomy, guidance and icons. Confirm compatibility with the pinned release before using API responses; an unversioned API must not silently introduce components/tokens from a newer release.

These URLs and module/runtime details are supplied by the user. Availability and export/component contents require actual access verification before implementation; a saved contract is not proof every URL loaded successfully.

## Arabic and third-party adapters

When Arabic is selected, use the published language resources and semantic `lang="ar" dir="rtl"`, preserving compact density policy. Keep the temporary Arabic styling as an independently replaceable asset until the Arabic Plenix CDN is ready. The existing prototype bridge was authored before these strict rules and contains legacy classes, raw values and fallback font definitions; it is prototype-only reference, not an approved production Plenix adapter. Do not claim it already satisfies this contract. Before reuse, translate its necessary behavior into documented Plenix classes/tokens, and ask about missing Arabic typography/layout tokens. Do not invent values or silently modify the user's Plenix source.

Uppy/PhotoSwipe/Video.js/PDF.js remain functionality candidates. Their default UI/CSS must not bypass Plenix rules; inspect rendered DOM/runtime styles, not just application source. Where a library can be used behind documented Plenix controls, use that supported boundary. If embedded controls cannot comply, report the concrete missing component/capability and seek a documented solution rather than copying a design-system control or introducing ad hoc styling.

No real user/case text, token or secret belongs in CDN URLs or static bundles. Loading CDN assets is presentation code execution in the browser, so trust/pin the source; it is not an external processing permission for case documents.

## NPM alternative — not current default

The user also permits the GitHub Packages route: configure `@plenix-ds:registry=https://npm.pkg.github.com` in `.npmrc`, authenticate with a GitHub token scoped to `read:packages`, then install `@plenix-ds/react`. Keep actual tokens in environment/secret configuration and out of committed files/logs. Pin the package version and lock dependencies if this alternative is selected; do not replace the chosen CDN delivery silently. No token has been requested or used here.
