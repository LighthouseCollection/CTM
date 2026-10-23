# CTM CDN 0.68.0 adoption

Pins shell assets, icons-all and settings to released 0.68.0. Shared/native council grids opt into uniformPillWidths. Shared scalar and person display values use native pills while retaining domain fields for actions and explicit original-value sorters. Rich controls remain custom cells. Gender is recorded data only; zero and missing names remain safe.

Validation: seven adapter regressions and four shell pytest checks pass. Broader shell/adapter batch has one existing spouse-card source-assertion failure; full hosted/independent QA is not claimed. Real CDN browser fixture checked equal pill widths, 24px pill heights, M/F presentation, zero, underscore icon mask, action callback and RTL keyboard resizing without browser errors. Review-found timestamp-sort regression fixed with failing/passing test. No schema/migration/auth changes.

Deployment must preserve current runtime configuration and internal plus egress network attachments. Check Microsoft DNS/HTTPS after switching. The prior runtime remains available for rollback. Existing unrelated priest-link CI failures remain outside this upgrade.
