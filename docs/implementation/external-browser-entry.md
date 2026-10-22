Current validation: **813 PostgreSQL passed, 1 skipped**, migration rollback/reapply through0046;16 new physical-role browser-entry regressions and Chromium fragment-transport smoke passed. No model/route/migration/grant changes in this continuation.

# External priest browser entry

Backend issue #2 / council C05. The existing `/external/reports/{id}/` route now
redirects explicit HTML GET navigation without an Authorization header to the
council-owned `/static/ctm/external-report.html`. Browsers retain the original
fragment on that redirect; the existing page reads `#r=<request>&t=<token>`, removes
it from the address bar, and fetches the original endpoint using Bearer transport.
The relative external-report.js path now resolves under the static directory.

No frontend asset is copied or edited. Governance must include council commit
0133b9d9fef7bf6f89b2f06fa48fb9b614487e50 or its accepted successor in the combined
static build. This backend branch alone does not contain those council assets.
This is a generic browser entry, not an assertion that a request exists or is valid.
The redirect does no request-row lookup, sets no cookie and exposes no case data.
Its destination has no request ID, query credentials, token or arbitrary next URL.
The browser retains only its existing fragment, which is never sent as HTTP URL data.

Django5.2's Accept preference parser chooses JSON first for absent/wildcard Accept.
Explicit JSON preference, HTMLq=0, any Authorization header (including blank or
invalid), POST and unsupported methods retain existing JSON/error contracts. Valid
Bearer requests remain JSON even with HTML Accept. All route responses vary on
Accept and Authorization and retain private/no-store/no-referrer/nosniff middleware.
No authentication, capability expiry/reissue/closure, saved-response or submission
rule changes. No route/model/migration/grant expansion; migration leaf stays0046.

Verification:16 physicalctm_app tests cover browser negotiation, no request-row
lookup, no cookie/data/query forwarding, API failure concealment, invalid/valid
Bearer precedence and non-GET behavior. Browser transport smoke uses the actual
Django route and verbatim council HTML on a disposable localhost WSGI server with
in-memory test settings, no real database. Chromium with JavaScript disabled proves
redirect fragment inheritance and two actual HTTP paths without token/fragment.
This deliberately does not claim form rendering, CDN availability or capability
submission acceptance. The council's existing UI/capability tests remain separate.

Reproduce with a Python environment containing project dependencies, Playwright
and installed Chromium:

    python scripts/browser_external_entry_transport.py --boot-html /path/to/pinned/council/external-report.html

Or omit --boot-html in a combined checkout containing that exact council asset.
No bearer, case data, credential or real server operation is needed. Full browser
entry/form acceptance requires governance's combined static build and exact SHA,
then council/QA verification. Remaining C05 receipt, recording, paper/print and
actual invitation delivery contracts remain unfinished.
