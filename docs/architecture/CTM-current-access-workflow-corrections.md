# CTM current access and workflow corrections — 2026-10-20

Authority: latest direct user corrections. These supersede conflicting earlier architecture statements. Documentation reconciliation only; no live authentication system was implemented.

## Authority

Admin and secretary have default case-operation authority within the agreed functional roles, not merely system-level administration. The assigned case worker/case manager remains responsible for investigations and routine case notifications. A case worker does not manage decrees. Decree preparation/issuance/release remains with authorized admin/secretary; presidential approval/signature remains the president's authority. Default administration does not waive applicant isolation, source preservation, signed medical-release restrictions or immutable closed proceedings.

Only an existing admin can add a council member. Secretary status alone cannot create council membership. There is no public request, application, self-registration or request-to-join workflow for council membership. Admin preauthorizes the council account, binds the intended Microsoft identity and sends an invitation; Microsoft sign-in alone does not enroll a member. This latest statement specifically changes member creation, without inventing changes to previously agreed deactivation/reactivation or role-edit permissions.

## Provider-managed authentication; no CTM passwords

Council sign-in uses Microsoft organizational authentication. Applicants use Google or Apple sign-in. Remove CTM email/password registration, password hashes/credentials, change-password forms, forgot-password/reset flows and local-password fallback from the production package design. Email remains a contact/matching attribute, not a standalone password login. Identity-provider credential recovery is handled by the relevant provider, not CTM.

CTM retains its own account authorization, active/suspended status, provider identity links, secure application sessions, invitation redemption and audit. Provider login does not bypass admin authorization, verified applicant linkage or existing privacy restrictions. Provider outage does not unlock a local login. Preserve stable person/account identity across cases; use provider-validated identity and established verified-email rules, not an untrusted email supplied in a form. Apple sign-in remains browser/web sign-in; this specification does not establish that every Apple identity exposes the same contact address the user supplies to staff. Exact pending-invitation email matching remains enforced.

Applicant self-service account creation through the approved providers remains the previously agreed rule; the latest restriction concerns adding council members. No separate Google/Apple password is stored by CTM. External priests retain the separately approved request-scoped direct-link workflow with 30-day expiry, without needing a provider or CTM password account.

## Decrees

Remove the replacement-decree workflow from current requirements and from the open-decisions list. Do not implement replacement/superseding-decree orchestration, decree-voiding triggers, clerical replacement certificate flows or new decisions inferred from that removed item. This does not remove the separately confirmed appeal process or its decree issuance under the original case, nor signature, entitlement, explicit release or preservation requirements. Preserve historical decisions and files; removal of a proposed workflow never authorizes deletion. Any future request for a replacement is new scope, not silently inferred now.

## Marriage matching — already settled

Exact marriage date plus both spouses' exact birth dates automatically links independent submissions for the same marriage. Compare the spouses as a pair, accounting for reversed applicant/spouse roles. This works when the certificate number is unavailable and even when supplied certificate numbers differ. Preserve each supplied certificate number and its source rather than overwriting either.

Do not use exact names or church/location spelling as gates. Missing values are not exact matches. Where the established exact match is not available, or candidates/party mapping are ambiguous, use admin/secretary review rather than inventing a certificate-only automatic link. Certificate numbers can inform review; no additional certificate-matching policy needs to be reopened in this workflow audit. Linking a marriage does not merge people, answers, payments or private access.

## Corrections to the gap review

Resolved: council membership creation, provider-managed password recovery, replacement-decree item removed, marriage matching no longer listed as unresolved. Default admin/secretary authority is restored subject to functional boundaries, while case workers cannot manage decrees. Previously identified prototype password, reset and registration-request controls are superseded prototype behavior, not implementation requirements.
