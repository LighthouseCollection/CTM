# CDN dependencies after review against Plenix 0.61.0

The UI branch pins the immutable 0.61.0 release and consumes only its documented APIs. CTM does not copy CDN assets, define local visual patches, or replace native icons.

- **Avatar background/border:** 0.61.0 supplies the agreed photo treatment for light and dark surfaces. CTM passes the authoritative account image URL to `AppHeader.Account`; account photo storage/editing remains a backend account contract.
- **Card heading icons:** documented `Card.icon` remains the supported council/app container-card interface. Panel and navigation icons use native CDN slots.
- **Embedded PDF:** CTM consumes the released `DocumentViewer` and vendor path through `PLENIX_BASE`; the council C04 implementation remains its owner.
- **Global peer-section spacing:** 0.61.0 documents `Stack gap="section"` for flat peer sections and `Stack gap="sm"` within a heading/content section. CTM uses component gaps rather than raw pixel margins.
- **Account menu localization:** 0.61.0 documents `AppHeader.Account.strings`. CTM supplies all supported English and Arabic menu labels, including its accessible account trigger and display-density choices.
- **Native media aliases:** published native icon aliases are used where CTM has an applicable pre-existing icon slot. CTM does not fetch or host literal icon SVG files.

Session detail uses the documented `EntityHeader` pattern with API-derived session facts and actions. The user-selected current session remains the source of header metadata; no prototype values are hard-coded. CDN documentation: https://design-system.lighthouseway.org/cdn/0.61.0/.
