# Microsoft callback identity lifetime fix

Governance reported a real preauthorized Microsoft admin callback on candidate
a2844f7 rendering Sign Up Closed. allauth SocialLogin.is_existing queries Account
again after AccountAdapter.pre_social_login returns. The adapter previously closed
its provider_identity scope before that query; restrictedctm_app RLS hid the bound
account, sending the validated council identity into closed Microsoft signup.

The patch extends only a successfully provider/CTM-validated identity from the
social adapter to the existing DatabaseActorMiddleware response boundary, using a
request-owned ExitStack. The initial validation scope exits before installing the
longer scope, preserving correct GUC restoration order. Lookup remains scoped by
the existing provider-validated SocialLogin instance wrapper. Ordinary session
bootstrap, Microsoft specific-tenant/preauthorized-subject/active/nonapplicant
checks and closed council signup remain unchanged. No migration, SQL policy,
grant, provider credential or settings change is required.

Six restrictedctm_app SQL-session tests invoke the actual allauth completion and
Django middleware/session/last-login flow after a synthetic validated-response
boundary: first Microsoft link and returning link both redirect and establish a
usable session; original hook lifetime reproduces Sign Up Closed; unmatched
subject, inactive account, applicant role and generic tenant remain denied.
Success and denial both restore provider GUCs, remove the request scope and leave
Account hidden outside the authorized context. No test callback route is registered
in application URLs. OAuth/network/provider cryptographic validation is not mocked
as live evidence: governance must independently retry the genuine callback on its
exact integrated successor build. Never expose the synthetic test endpoint publicly.

Governance owns serial integration/deployment and independent real-provider retry.
Backend performs no shared-server operation, migration, merge or deployment.
