"""Record any ctm_qa01 statement running longer than 10 s (full text, wait state) while tests run."""
import json
import time

import psycopg

from bootstrap_db import superuser
from qa_env import EVIDENCE

seen = {}
out = EVIDENCE / "long-running-queries.json"
while True:
    try:
        with superuser() as conn:
            rows = conn.execute(
                "SELECT pid, usename, state, wait_event_type, wait_event, pg_blocking_pids(pid), "
                "extract(epoch FROM now()-query_start), query FROM pg_stat_activity "
                "WHERE datname='ctm_qa01' AND state <> 'idle' AND now()-query_start > interval '10 seconds'").fetchall()
        for pid, user, state, wtype, wevent, blockers, secs, query in rows:
            seen[pid] = {"pid": pid, "user": user, "state": state, "wait": f"{wtype}/{wevent}", "blockers": blockers,
                         "seconds": round(float(secs)), "query": query}
        if rows:
            out.write_text(json.dumps(list(seen.values()), indent=2) + "\n", encoding="utf-8")
    except psycopg.Error:
        pass
    time.sleep(3)
