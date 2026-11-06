#!/usr/bin/env node
// Activity hook (template v2.4 §9, G-11): writes <state>/activity/<role>.json on
// SessionStart, PostToolUse and Stop. Only sessions the dispatcher starts load it
// (claude --settings), and only they have CTM_ROLE set. Never blocks a session.
"use strict";
const fs = require("fs");
const path = require("path");

let input = "";
process.stdin.on("data", (c) => { input += c; });
process.stdin.on("end", () => {
  try {
    const role = process.env.CTM_ROLE;
    const state = process.env.CTM_DISPATCH_STATE;
    if (!role || !state || !/^ctm3-[a-z0-9-]+$/.test(role)) return;
    let event = "activity";
    try { event = JSON.parse(input).hook_event_name || event; } catch { /* not JSON */ }
    const dir = path.join(state, "activity");
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, `${role}.json`), JSON.stringify({ ts: new Date().toISOString(), event }));
  } catch { /* never fail the session */ }
});
