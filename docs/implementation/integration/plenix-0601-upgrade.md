# Plenix 0.60.1 pin upgrade

Owner authorized upgrading as-is from0.58.0. All six shell assets and settings.PLENIX_BASE now pin0.60.1; strict shell-order/version assertion updated to the same version. No CDN files copied, feature changes, CSS patches, PDF overrides or Card markup changes included.

All six live assets return HTTP200. All208 frontend tests pass. Existing header/account Chromium regression passes against the local preview: native utilities/account menu, photo/email rendering and initials fallback, no sample email. This is scoped browser validation, not complete EN/AR/PDF/record-header acceptance. Existing CTM PDF fallback remains until its separate integration is changed and verified.

Previous QA candidate8572195 remains immutable in Git history; QA must record whether it tests that candidate or this newer CDN upgrade. Existing test results cannot be silently transferred. No main merge or production deployment.
