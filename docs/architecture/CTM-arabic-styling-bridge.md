# CTM temporary Arabic styling bridge

Implemented 2026-10-20 as an isolated presentation patch. User authorization to implement this patch supersedes the prior general no-prototype-edits boundary for stylesheet integration only. No business workflow or database was built.

## Current delivery

`ctm-admin/assets/localization/ctm-arabic-bridge.css` loads after existing styles in all 49 top-level admin/public HTML pages with a head element. Nested PatternFly spike/build artifacts are outside scope. Base `ctm-admin/styles.css`, existing scripts, content and workflow logic are unchanged. Each hook has `id="ctm-arabic-styles"`. Before/after page hashes are recorded in `CTM-arabic-styling-hook-manifest.json`; the original prototype source manifest is not rewritten.

Arabic rules activate only on `html[lang|="ar"][dir="rtl"]`. English retains existing styling. The locale controller must set the semantic `lang` and `dir` attributes when switching the published language bundle; CSS does not translate a label or make an English page Arabic. Locale persistence and published translation loading remain part of the future application integration. No new translations or automatic AI calls were added.

The patch includes Arabic font fallbacks (no network font dependency), normal letter spacing, more generous line height, wrapping labels/buttons, logical alignment, legacy sidebar/modal offset corrections, mixed-direction email/phone/URL controls and opt-in bidi/icon hooks. It does not blindly mirror logos, photographs, signatures, download icons or media controls. Free-form user text must use `dir="auto"`; inline case IDs/filenames use `bdi dir="ltr"` or equivalent explicit isolation. Logical properties preserve reading/DOM order without a second row reversal.

## Swap to the Plenix Arabic CDN

Keep base Plenix assets and application translation bundles separate from this bridge. When the Arabic CDN is ready, replace the stylesheet referenced by `#ctm-arabic-styles` with the compatible Arabic CDN asset in the shared layout (or the corresponding static-page links). Remove the bridge rather than loading overlapping Arabic patches together. The application keeps semantic `lang`/`dir`, language preference, resource keys and bidi markup; no case/data migration is involved. Application-specific hooks need compatibility checks against the actual future CDN contract, which is not available yet.

Current prototype uses local `styles.css`, not a verified Plenix CDN; this patch bridges the existing prototype classes without copying the design system. This is foundation coverage, not a claim of complete Arabic rendering across every component. Existing prototype physical positioning, inline page rules and runtime components require rendered checks once the actual Arabic resources/locale controller are integrated.

## Translation language policy

All UI labels, navigation, questions, prompts, comments/help, validation and system messages require Arabic equivalents when Arabic is selected. Use familiar Egyptian Arabic with formal/common wording appropriate to the context, following the user's supplied prompt and approved terminology. Prior suggestions of a mandatory formal-Arabic-only default are superseded. Private authored case content remains attributed to its source, with authorized translated versions separate; interface language never changes ownership or access.

## Reference synthesis

The six user-supplied articles are design inputs, not authority to add payment methods, SMS/WhatsApp, new gender assumptions, imported cultural imagery or business rules. Blanket mirror-everything advice is rejected in favor of semantic, component-specific handling. Fixed font-size increases are not adopted as universal rules; Arabic readability, wrapping and clipping require actual testing with the selected font. Preserve CTM IDs, USD fees and Los Angeles case-date policy.

- [UserQ: five Arabic UX considerations](https://userq.com/5-essential-considerations-for-ui-ux-in-arabic-interfaces/): RTL flow, typography, long-name accommodation; its blanket logo/media mirroring advice is not adopted.
- [freeCodeCamp: designing for Arab users](https://www.freecodecamp.org/news/designing-for-the-arab-user-basic-arabic-ux-for-business-6ff29d4c7c60/): mixed numeric direction and translation expansion; older 2017 guidance, not a modern technical standard.
- [Muzli: RTL basics](https://medium.muz.li/web-design-for-right-to-left-languages-the-basics-287329d508cf): selective mirroring, non-directional icons and undistorted images.
- [UX Republic: Arabic-speaking UX](https://www.ux-republic.com/en/design-the-user-experience-of-different-cultures-for-the-Arabic-speaking-Internet-user/): alignment, typography and form affordances; numerical font prescriptions remain contextual.
- [TheGeeX: Egyptian users](https://thegeex.org/blogs/designing-for-the-egyptian-user): contextual language register and localization beyond translation; regional commercial suggestions do not override CTM choices.
- [Code Guru: Arabic RTL UX](https://codeguru.ae/blog/designing-arabic-interfaces-right-to-left-ux-done-right/): additional Arabic layout/design reference, not a component API specification.
- [W3C structural direction](https://www.w3.org/International/questions/qa-html-dir) and [W3C inline bidi markup](https://www.w3.org/International/articles/inline-bidi-markup/): primary implementation guidance for semantic direction and mixed-script isolation.

## Verification and limits

Static checks verify every expected page has exactly one valid stylesheet path after existing styles, and integration is limited to that inserted hook. The base stylesheet hash is recorded separately and no translation text is injected by CSS. Rules are Arabic-scoped; no external imports, global image transforms or automatic data rewriting. Browser rendering, keyboard interaction, mobile overlays, real font shaping, mixed-direction caret behavior and Arabic screen-reader output have not been verified here. These remain acceptance checks before shipping Arabic mode.


## Pinned Plenix CDN contract — 2026-10-20

[Plenix CDN contract (pinned 0.76.0)](CTM-Plenix-CDN-contract.md) is authoritative: load theme-boot, fonts, plenix CSS, matching React/ReactDOM vendor scripts and plenix.js in the user's specified order, using window.Plenix (or the documented ESM alternative with React 18 peer). Use documented Plenix components/patterns, plx- classes and --plx-sys-*/--plx-comp-* tokens only; no inline styles, raw colors, numeric font sizes or !important. Ask for missing components/values. No CDN assets are copied. The old prototype Arabic bridge is not yet compliant production styling; its necessary behavior must be reconciled against documented tokens before use.
