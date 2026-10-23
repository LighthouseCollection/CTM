# CTM client routing design

## Goal

Keep CTM as one authenticated Plenix application while making each workspace and selected record addressable in the browser. A refresh, direct link, and browser Back/Forward must restore the same authorized view instead of returning to Home.

## Scope

- Add client-side route parsing, serialization, and browser-history synchronization to the council and applicant shells.
- Make navigation controls update the URL using `history.pushState`.
- Restore the active workspace and optional selected record from the URL when CTM boots or receives `popstate`.
- Complete the Plenix 0.68 native pill integration for routed collection views, including the Tribunal Sessions lists.
- Preserve existing permission checks and server API authorization. Invalid, unavailable, or unauthorized record IDs must render the existing authorized workspace state or its existing access/error view; routing must not fetch or display extra data.
- Preserve the current desktop shell and support the future mobile bottom navigation with the same canonical routes.

## Non-goals

- Server-rendered HTML pages for every workspace.
- A router-library migration or a second application shell.
- Changes to the database schema, API authorization model, or session management.
- Persisting unsaved edits through a hard refresh. Existing before-unload and unsaved-change protections remain authoritative.

## Native Plenix cell rendering

CTM must stop broadly opting out of the CDN’s native table treatment with `pill: false` for ordinary data fields. Every collection view follows these rules:

| Data type | Native rendering |
|---|---|
| Person or clergy name | `DataPill`, with a declared gender where available and the generic person treatment otherwise |
| Date, time, reference, count, and other compact scalar value | Native DataGrid pill cell |
| State or status | `Badge` using the approved semantic tone; it is not rendered as a disabled gray data pill |
| Actions | Plenix buttons, never a decorative pill |
| Rich custom content | Explicit custom renderer only where it conveys information a native pill cannot |

For the current Tribunal Sessions lists, session date, session time, counts, and state must no longer be explicitly configured with `pill: false`. State uses the native semantic badge. Edit, Delete, Open, and other row actions remain buttons. This preserves meaning and interaction while making the 0.68 component upgrade visible in the UI.

## Canonical routes

Routes remain same-origin and use path segments only; no case names, emails, or other sensitive values belong in URLs.

| Area | Route | Restored state |
|---|---|---|
| Council home | `/` | Home workspace |
| Sessions list | `/sessions/current`, `/sessions/upcoming`, `/sessions/archived` | Session list mode |
| Selected council session | `/sessions/{session-id}` | Session workspace and selection |
| New applications | `/applications/new` | Review queue |
| Cases | `/cases/mine`, `/cases/active`, `/cases/archived` | Matching case collection |
| Selected case | `/cases/{case-id}` | Case summary |
| Case section | `/cases/{case-id}/{section}` | Case selection and valid section: `summary`, `timeline`, `spouses`, `marriage`, `separation`, `email`, `calls`, `notes`, `petition`, `reports`, `hearings`, `evidence`, `documents`, `assessment`, `decision`, `decree`, `appeals`, or `audit` |
| CTM settings | `/settings/{tab}` | Valid settings tab: `users`, `configuration`, `data`, or `audit` |
| Account | `/account` | Account/profile workspace |

The exact public applicant routes remain unchanged unless their current application shell already has a stable route contract. This change must not redirect an applicant from an existing public URL to a council route.

## Navigation behavior

1. A normal in-app navigation updates React state and pushes one canonical route.
2. Selecting an already-active route does not add a duplicate history entry.
3. On `popstate`, CTM derives the target UI state from the path and updates React state without pushing another entry.
4. On the first load or refresh, CTM derives its initial state from the current path before rendering the selected workspace.
5. An unknown route falls back to the caller's authorized Home workspace and replaces the URL with `/`; this avoids retaining a false or inaccessible location in history.
6. Navigation that would discard an existing unsaved draft continues to pass through the current guard. The URL changes only after that navigation is accepted.

## Route utilities

Create a small framework-free module used by the application shell:

- `parseRoute(pathname)` returns normalized `page`, optional `selection`, optional case `section`, and canonical pathname.
- `routeFor(page, selection, section)` returns the canonical pathname.
- `navigate(route, { replace })` calls `history.pushState` or `history.replaceState` only after the existing guard allows navigation.
- `useRoute` or an equivalent shell-level effect subscribes to `popstate` and unbinds during teardown.

It must use `encodeURIComponent` for generated IDs and `decodeURIComponent` safely when parsing. Malformed encoded paths must be treated as unknown routes rather than throwing.

## Compatibility and deployment

- Django/Nginx must serve the CTM shell for the defined client routes when a user opens or refreshes a deep link. Existing static and API URLs remain unchanged.
- Reverse-proxy fallback must never intercept `/api/`, `/static/`, authentication callbacks, media downloads, or public applicant routes.
- Direct deep-link tests must use an authenticated session because the council workspace is protected.
- Existing live bookmarks to `/` keep working.

## Validation

1. Unit-test route parsing and serialization for every canonical route, invalid route, malformed encoding, and URL-safe ID.
2. Test initial rendering from a selected case and session route.
3. Test an in-app navigation pushes the intended route once.
4. Test Back/Forward restores list mode, selection, and valid case section without an additional history entry.
5. Test a browser refresh at a selected session, case summary, and case section returns to that view.
6. Test direct navigation to a protected route still respects the server’s authorization behavior.
7. Confirm API, static asset, Microsoft callback, download, and public applicant URLs do not get rewritten to the SPA shell.

## Acceptance criteria

- Refreshing `/sessions/{id}` returns to that session.
- Refreshing `/cases/{id}/evidence` returns to Evidence for that case.
- Browser Back/Forward moves through recent CTM views in the expected order.
- A copied browser address opens the same authorized CTM workspace for an authorized user.
- Existing in-app navigation, language selection, permissions, and unsaved-change protection continue to work.
