# CTM council Microsoft sign-in package requirement

> **Current authority — latest corrections (2026-10-20):** [Access and workflow corrections](CTM-current-access-workflow-corrections.md) supersede conflicting older passages below. Admin/secretary retain functional case authority; case workers do not manage decrees; only existing admins add council members; no council membership requests. Microsoft for council and Google/Apple for applicants handle authentication/recovery; CTM has no local password system or fallback. Replacement-decree workflow is removed. The settled exact marriage-date/both-DOB matching rule is not an open decision.


Confirmed by user, 2026-10-20. Microsoft sign-in is a required capability of the CTM delivery package, not merely a future optional idea. This is the package/architecture specification; the current HTML prototype has no deployed authentication server and no Microsoft connection has been configured or tested.

## Account and sign-in workflow

Admin creates the council member's CTM access record, chooses the role and sends an invitation. No public council self-registration or automatic access based on a lacopts email suffix. The member chooses Sign in with Microsoft and authenticates using their organizational lacopts identity. Microsoft authenticates identity; CTM checks its own active preauthorized council account, role and case-assignment permissions on every authorized operation.

This supersedes the council email/password-only restriction by adding Microsoft organizational sign-in. Local password access is removed by the latest correction; applicants use Google/Apple only. Applicant sign-in cannot grant a council role. Council Microsoft sign-in is distinct from the private no-account external-priest report link.

Use Microsoft OpenID Connect authorization-code flow with server-side validation, anti-forgery state, nonce and PKCE. Restrict the configured council provider to the intended organizational tenant; do not accept arbitrary personal Microsoft accounts or unrelated organizations. Validate issuer, audience, signature and token lifetime. Bind the CTM identity to validated tenant ID plus immutable Microsoft object ID, not a mutable email string alone. Initial linking requires an active unredeemed admin invitation/preauthorization and explicit recipient identity matching; ambiguous/different-email identities require admin resolution rather than silently joining accounts. Verified Microsoft identity is not proof of a council role.

After successful redemption, preserve invitation/identity-link provenance and issue the normal secure CTM session. Deactivated CTM accounts cannot sign in or continue using existing CTM sessions. Role changes and case assignment checks remain authoritative in CTM. There is no local password fallback; provider failure cannot grant access. No Microsoft password or token is sent by email. Invitation email carries an activation/sign-in link, not a reusable password.

## Package and system settings

Ship the server-side Microsoft provider adapter, callback/sign-in/logout handling, invitation redemption and identity-link records, localized Sign in with Microsoft control, setup validation, configuration template and deployment instructions. Display connection status and safe error handling if unconfigured. A local VM, Azure VM or AWS deployment uses the same provider configuration with its registered HTTPS callback URL; moving hosting does not move the Microsoft tenant.

Admin system settings/configuration contain tenant ID, application/client ID, expected issuer, configured external base URL and callback URI, enabled/connection state and a protected server-side credential reference where a confidential client requires one. Secret fields are write-only/masked, redacted from logs/audit and never shipped as frontend constants. Redirect URI/base URL changes require matching application-registration configuration. Ordinary account preferences cannot edit the provider or assign council roles.

Deployment dependencies: identify the Microsoft organization that manages lacopts identities, obtain authorized tenant/application registration access, register CTM and its callback, and provision credentials through the approved server-side secret store. These facts are not established by owning an Azure subscription or personal Microsoft account. No tenant IDs, exact email domain, keys, licenses or administrator consent have been invented or obtained here.

Reuse existing account/login/session audit systems. Proposed identity record: account_identity_links(account_id, provider_config_id, tenant_id, microsoft_object_id, linked_at, linking_actor/invitation_id), unique on validated tenant/object identity. Store invitation state separately with recipient, expiry, redemption and revocation provenance. The CTM account remains stable across email changes; do not rebind on a new email claim automatically.

## Required eventual validation

- Admin-preauthorized member can redeem an invitation and sign in; unauthorized lacopts user cannot.
- Wrong tenant, wrong audience, invalid state/nonce, expired/replayed invitation or untrusted tokens cannot create or link a council account.
- Email changes do not change the bound Microsoft object or CTM account.
- Applicant and external-priest sign-ins do not acquire council privileges.
- Disabled members and revoked CTM sessions are rejected independently of a still-valid Microsoft session.
- Missing credentials/provider outage produces a useful localized error without granting access or inventing an offline login.
- Deployment redirects and secret handling are verified against the actual tenant before release.

Microsoft references: [identity platform](https://learn.microsoft.com/en-us/entra/identity-platform/v2-overview), [single/multitenant apps](https://learn.microsoft.com/en-us/entra/identity-platform/single-and-multi-tenant-apps), [app registration](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app). These describe the integration; they do not confirm a lacopts tenant has been connected.


## Initial VM deployment address — confirmed 2026-10-20

The user will initially install CTM on their own VM and access it at **https://ctm.lighthouseway.org**. Both applicant and council portals belong to this application origin; exact portal route paths are implementation details. Django sessions, CSRF origin checks, reverse-proxy/HTTPS settings and approved identity-provider callback registrations must use this canonical address. Payment/email callbacks use the same configured public application base URL where applicable. Do not invent a VM IP, DNS record, reverse proxy product or active provider connection from the supplied hostname.

Application availability at this address does not make case data public. Authentication, admin-only council enrollment, applicant isolation and private file/search access remain required. Database, search, processing services and storage management endpoints stay private. Whether network access will also be restricted by VPN must follow the final access decision; browser reachability and external provider webhook reachability must be configured explicitly rather than assumed.

This selects the initial own-VM deployment, while a later Azure/private-server move remains a separate future discussion. No DNS, certificate, VM, deployment or network setting was changed or verified by documenting the URL. All host-specific settings remain configurable for portability.
