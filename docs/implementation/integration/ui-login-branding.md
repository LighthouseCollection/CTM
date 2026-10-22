# Login branding

Owner-requested layout: the two exact institutional lines and diocesan seal outside the login container; CTM logo at its top inside. Implemented with existing Plenix PageContent/Center/Stack/Inline/Panel/Image/Text/Button components and published utility classes. Authentication endpoints, provider availability and POST/CSRF flow remain unchanged.

Assets: diocese-seal.png copied from supplied lacopts_seal_001.png; diocese-seal.svg copied from supplied Desktop/diocese_logo.svg as image fallback. CTM reuses tribunal-logo-cropped.svg. No raster editing, remote asset references or new branding text were introduced.

Validation: browser_login_branding.py at390/768/1440: images decode; exact header/card placement; EN/AR language switching; no horizontal overflow or page errors; configured synthetic provider POST handoff. Actual provider authentication is outside this visual test. 236 frontend tests pass; independent review found no actionable issue.

Delivered on UI draft PR21, not deployed. Governance must publish the exact successor and collect static assets coherently before production acceptance. Local screenshots: .tmp/login-branding-1440.png and .tmp/login-branding-390.png.

Owner refinement: heading now reads “Sign in”; welcome/council-use copy and the login language switch are removed. CTM logo/title are centered. Institutional branding uses the AppShell header slot; the login card is centered horizontally and vertically in the remaining main area with the published justify-center utility. Three-width regression checks actual card/logo geometry, absence of removed copy/control and provider POST handoff.
