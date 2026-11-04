# Selected CTM application foundation: Django + Plenix React CDN

Confirmed by user, 2026-10-20. Django is selected as the application backend; Plenix CDN supplies the React-based presentation components. Rails and Frappe are evaluated alternatives, not active implementation choices. No backend/frontend application was scaffolded by this documentation update. Exact supported Django/React versions and actual Plenix CDN module/asset contract remain setup details.

## Compatible responsibilities

React runs the interactive interface in the browser. Django runs on the CTM server, controls authentication sessions, authorization, workflows, database access and processing orchestration. PostgreSQL remains authoritative. Plenix's React implementation is compatible with Django; the frontend and backend do not have to use the same language or framework.

Serve the compiled CTM React frontend and Django application endpoints under the same application origin through the deployment reverse proxy. Plenix components/styles can be loaded from the approved versioned CDN contract; connect them to CTM application code rather than expecting the CDN to supply case workflows. Keep private CTM data in responses from CTM, never in CDN URLs or static bundles. Frontend libraries necessarily execute with the application's browser privileges; pin and trust release assets accordingly. The CDN does not receive case data for storage/processing merely because components are loaded from it.

Use Django-backed secure sessions and CSRF-protected state-changing requests. Enforce every business permission on the server, including uploads, media/range requests, search, medical-release scope and account status. React hiding controls is not authorization. Keep provider secrets server-side; no Microsoft/Google/Apple credentials or search admin keys in browser bundles. External identity providers remain responsible for user passwords/recovery, and admin-only council preauthorization still applies.

React can be integrated into server-rendered pages or used for portal-wide client rendering; this is a packaging choice, not a new framework decision. For the current package, prefer same-origin browser assets/endpoints and avoid an unnecessary separately managed frontend server. A normal production React build can be served as static assets; Node-based development/build tooling does not by itself require a production Node application service. Do not introduce Next.js/SSR unless a real requirement warrants it.

## Plenix verification before implementation

Confirm the exact CDN URLs, release version, module/global exports, React/ReactDOM peer/runtime requirements, stylesheet/token imports, icon dependencies, licensing and Arabic support. The local Plenix repository package manifest was inspected, but no published CDN build or actual CTM component integration has been verified. Do not load two incompatible React runtimes or assume a React component library works as a CSS-only link. Third-party recorder/viewers use contained Plenix adapters; the temporary Arabic bridge remains replaceable when Arabic CDN assets are ready.

## Deployment

One Linux CTM VM, multiple containers, approximately ten demo users. Hosting remains Azure or a private server with VPN access, to be decided later. The framework selection does not finalize hardware, Linux distribution, exact service versions or credentials. Preserve private database/files/models/configuration and tested restores independently of container image lifecycle.

References: [React integration into an existing stack](https://react.dev/learn/add-react-to-an-existing-project), [Django AJAX CSRF](https://docs.djangoproject.com/en/5.2/howto/csrf/).


## Pinned Plenix CDN contract — 2026-10-20

[Plenix CDN contract (pinned 0.76.0)](CTM-Plenix-CDN-contract.md) is authoritative: load theme-boot, fonts, plenix CSS, matching React/ReactDOM vendor scripts and plenix.js in the user's specified order, using window.Plenix (or the documented ESM alternative with React 18 peer). Use documented Plenix components/patterns, plx- classes and --plx-sys-*/--plx-comp-* tokens only; no inline styles, raw colors, numeric font sizes or !important. Ask for missing components/values. No CDN assets are copied. The old prototype Arabic bridge is not yet compliant production styling; its necessary behavior must be reconciled against documented tokens before use.


## Initial VM deployment address — confirmed 2026-10-20

The user will initially install CTM on their own VM and access it at **https://ctm.lighthouseway.org**. Both applicant and council portals belong to this application origin; exact portal route paths are implementation details. Django sessions, CSRF origin checks, reverse-proxy/HTTPS settings and approved identity-provider callback registrations must use this canonical address. Payment/email callbacks use the same configured public application base URL where applicable. Do not invent a VM IP, DNS record, reverse proxy product or active provider connection from the supplied hostname.

Application availability at this address does not make case data public. Authentication, admin-only council enrollment, applicant isolation and private file/search access remain required. Database, search, processing services and storage management endpoints stay private. Whether network access will also be restricted by VPN must follow the final access decision; browser reachability and external provider webhook reachability must be configured explicitly rather than assumed.

This selects the initial own-VM deployment, while a later Azure/private-server move remains a separate future discussion. No DNS, certificate, VM, deployment or network setting was changed or verified by documenting the URL. All host-specific settings remain configurable for portability.


## Locked council navigation and layout map — 2026-10-20

[Council navigation and layout](CTM-council-navigation-and-layout.md) records the user's locked hierarchy, Communications directly after Case Overview, Appeals beneath Decision, no case list in navigation, and the persistent sidebar avatar/name trigger with a hidden account/system menu subject to documented Plenix support. It distinguishes agreed case-report split view from proposed evidence/document/communication/assessment layouts and optional search/appeal previews. No unverified custom Plenix shell or component has been built.
