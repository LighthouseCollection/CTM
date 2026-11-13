/* CTM optimistic saves (issue 313, performance rule 6): a save that waits for the server feels slow, so a safe edit
   shows its new value at once, is sent in the background, and is put back if the server refuses.

   Rules:
   - Deny by default. Only the paths on SAFE are ever shown ahead. Add a path there in the same change that wires it.
   - CONFIRM_FIRST always wins, even over SAFE: votes, decisions, decrees, payments and anything legal (declarations,
     signatures, findings and outcomes, and the send / issue / sign / submit / withdraw / release steps). These are
     shown only after the server agrees, and a refusal shows nothing because there is nothing to undo.
   - run() never throws for a failed save. It returns { ok, result?, error?, shownEarly } so the caller shows its
     approved failure message (docs/content/messaging.md) and nothing else. Words stay with the caller; this file has none.
   - The caller must not run two saves of the same field at once (disable the control while one is on its way):
     revert() puts back the value that was there before this save.
   The server still decides everything; this only changes when the screen shows the answer. */
(() => {
  "use strict";

  // Never shown ahead. Matched against the whole path, query included, so nothing slips in behind a "?".
  const CONFIRM_FIRST =
    /(^|[/?&=])(votes?|decisions?|decrees?|payments?|declarations?|signatures?|findings?|outcomes?|submit|withdraw|send|issue|sign|release|adjourn)([/?&=]|$)/i;

  // Edits that are safe to show ahead (paths as the modules ask for them).
  const SAFE = [
    /^\/api\/sessions\/[^/?#]+\/attendance\/$/, // a council member's Present / Absent
  ];

  function mode(path) {
    if (typeof path !== "string" || !path) return "confirm";
    if (CONFIRM_FIRST.test(path)) return "confirm";
    return SAFE.some((pattern) => pattern.test(path)) ? "optimistic" : "confirm";
  }

  function attempt(save) {
    try {
      return Promise.resolve(save());
    } catch (error) {
      return Promise.reject(error);
    }
  }

  // path: the address being saved. save(): sends it and returns a promise. apply(): shows the new value.
  // revert(): puts the old value back (only called for an edit that was shown ahead and then refused).
  function run({ path, save, apply, revert }) {
    const early = mode(path) === "optimistic";
    if (early) apply();
    return attempt(save).then(
      (result) => {
        if (!early) apply();
        return { ok: true, result, shownEarly: early };
      },
      (error) => {
        if (early) revert();
        return { ok: false, error, shownEarly: early };
      },
    );
  }

  window.CTMOptimistic = { run, mode };
})();
