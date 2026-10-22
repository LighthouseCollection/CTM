# CDN dependencies after review against Plenix 0.60.1

Governance upgraded the immutable pin to 0.60.1. CTM consumes documented APIs; no distribution copies or raw styling overrides were introduced.

- **Avatar background/border:** resolved for uncolored light-theme avatars in 0.60.1. Browser regression verifies transparent photo on white and a 1px grey border. Dark-theme behavior remains unchanged upstream; universal white across themes is not claimed. Account photo storage/editing remains a separate backend contract.
- **Card heading icons:** documented Card.icon is now available and adopted for council/app container cards. Panel and navigation icons remain native CDN slots.
- **Embedded PDF:** upstream assets repaired in 0.60.1; council C04 owns the consumer implementation, integrated in base 0b10a61. UI removed its overlapping unpublished implementation. Authorized rendering and browser fallback are checked against the council implementation.
- **Global peer-section spacing:** current session uses flat heading/table peers and Stack gaps. This is not proof of a global correction after nesting cleanup. CDN still needs acceptance across page/split hosts, densities, RTL and mobile without restoring nested containers.
- **Account menu localization:** no documented Account strings contract for localized menu labels/trigger was identified. Remains upstream.

Session detail now uses documented RecordPage.Header with default size/surface, meta and actions. CDN documentation: https://design-system.lighthouseway.org/cdn/0.60.1/docs/record-page.md .
