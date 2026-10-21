# Desktop-R: applicant portal

Implement the applicant journey in LighthouseCollection/CTM on branch
work/desktop-r-applicant, in your own clone. Read governance.md and the approved
build-spec schema, permissions, interface and acceptance contracts first.

Start with saved draft editing and approved question rendering; then review,
required uploads, declaration, payment/waiver display, submission and returned
application corrections. Preserve originals and applicant isolation. Do not
invent successful external payment states or add local passwords.

Own applicant frontend modules and their tests. Shared backend/migrations belong
to VM-FRM; request missing endpoints on this issue. Coordinate shell/app.js hooks
through governance. Use Plenix CDN0.58.0, English/Arabic and RTL. Open a draft PR
early and report concrete checks, dependencies and remaining work on this issue.
Do not merge or deploy independently.
