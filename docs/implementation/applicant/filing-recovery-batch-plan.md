# Next ten batches: filing actions and retained checkout recovery

Continue the approved applicant design against backend acafe29/d724ba5. Preserve
module boundaries, pinned Plenix 0.58.0, exact supplied declarations and EN/AR.
Shared shell sources and backend/migrations remain with their owners.

1. Integrate own draft deletion capability and explicit confirmation.
2. Verify stale/missing action versions and foreign-owner denial.
3. Integrate returned filing withdrawal while preventing draft deletion.
4. Verify joint filing participation and case closure safety.
5. Verify own pending appeal withdrawal and immutable fee/history.
6. Integrate original retained checkout declaration, signer and same candidate.
7. Reject unsafe URLs and missing/expired expiry; recheck at navigation time.
8. Verify processing/paid/changed candidates block resume and fresh checkout.
9. Exercise uncertainty, interrupted navigation, denied refresh and EN/AR layouts.
10. Consolidate real API evidence, remaining dependencies and proposed integration.

Use test-first fixes for gaps. Real API acceptance archives the backend into a
fresh isolated SQLite workspace. Provider-create output may be a controlled fixture;
no real provider charge, expiry callback or payment success is claimed. Local expiry
only hides resume and never clears the pending payment hold. Review precedes push.
