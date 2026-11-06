# Dispatcher, mode P (template v2.4 §6; gaps G-5, G-10, G-11; decision D-0040)

**Problem.** Sessions start only when the owner or another session starts them,
so Ready work waits (template §6.4: a nudge is a dispatcher failure).

**Mode P.** A poller on this Windows agent host, started by Task Scheduler every
`heartbeat_min`. No self-hosted runner (mode R needs a private repository; CTM is
public, D-0016). No UI, no database: GitHub (labels, PRs, the heartbeat issue) and
`agents.config.yaml` are the state; the host keeps only a small session file per
running role.

**Parts (inside the tooling cap)**
| Part | File | Does |
|---|---|---|
| Poller | `scripts/dispatcher/poll.cjs` | Fetches `main`, reads the registry and GitHub (Ready issues, open PRs), reads session files and last-activity, applies the rules, starts or stops sessions, updates the heartbeat issue. `--dry-run` prints the plan only; `--launch-test` checks every non-parked role can be launched (G0) |
| Rules | `scripts/dispatcher/decide.cjs` | Pure function state → actions, unit-tested |
| Launcher | inside `poll.cjs` | `claude -p --agent <role> --model <model>` headless, detached, `NODE_OPTIONS=--max-old-space-size` from `memory_limit`; stop = `taskkill /T /F` |
| Activity hook | `scripts/dispatcher/activity-hook.cjs` | SessionStart / PostToolUse / Stop write `<state>/activity/<role>.json`. Passed only to the sessions the poller starts (`--settings`), so the shared `.claude/settings.json` is unchanged |
| Heartbeat issue | pinned "Dispatcher heartbeat" | Last run time and the §6.5 health line |
| Watchdog | `.github/workflows/dispatcher-watchdog.yml` | Daily, GitHub-hosted: heartbeat older than 2 × `heartbeat_min` → one `process` issue (sev:S1) |
| Install | `scripts/dispatcher/install.sh` | Creates the dispatcher worktree and registers the Task Scheduler task (owner runs it once) |

**Rules (template §6.2, as built)**
1. Ready = role label + `ready_label`, for lane roles. A task role's work = an open PR that carries its label (it removes the label when its gate row is filled).
2. A PR that is ready for review and has no `gates:assigned` gets the label of every applicable task role (`always`, or `applies_to_paths` matches a changed file) plus `gates:assigned`.
3. Start a role when it has work, is not running, is not `parked`, and: it is a gate or task role (they run on top of `slots`, D-0025), or fewer than `slots` long-work sessions run. Order by `priority`. Nothing starts while free memory is below `start_new_below_free_gb`.
4. A running session idle for `idle_exit_min` with no work → stop. A session with work and no activity for `stall_min` → nudge comment; on the second stall → stop, back to Ready, note for `docs/lessons.md`.
5. A task session running longer than `short_task_cap_min` → stop; it is queued as long work next time.
6. Ready depth under `ready_min` in the build lanes, or Backlog and Ready both empty → wake `refill_role` (at most once per `stall_min`).
7. A Ready issue with no registered role label → one `process` issue. A registry problem (`check_registry.cjs` fails) → one `process` issue, nothing starts.

**Tokens (lesson L-18).** The poller acts with the host's `gh` login (a user token), so its label changes wake nothing on GitHub by design: it starts the sessions itself. The watchdog only opens an issue; it hands nothing off. The GitHub App (gap G-7) is deferred by the owner (2026-11-06), so any workflow hand-off stays an explicit `workflow_dispatch`; nothing here waits on an App token.

**Not built:** mode R, the lane Stop hook that blocks exit while Ready items exist, the board Project field moves (no `project` scope yet, see `sdlc.md` §9).

**Done when:** `decide` tests pass, `poll.cjs --dry-run` and `--launch-test` run against the live repository, the watchdog passes zizmor, and D-0040 points at the watchdog job.

**Install (owner, once; until then sessions are started by hand as today).**
`bash scripts/dispatcher/install.sh` from Git Bash: creates the `ctm3-wt/dispatcher`
worktree, runs the registry check and `--launch-test`, and registers the Task
Scheduler task "CTM3 Dispatcher" every `heartbeat_min` (while logged on). Each
poll may start headless sessions, which use the account's Claude usage.
Try `node scripts/dispatcher/poll.cjs --dry-run` first. Remove with `--remove`.
