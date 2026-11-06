#!/usr/bin/env bash
# Installs the CTM dispatcher, mode P (D-0040), on this Windows agent host.
# Owner runs it once from Git Bash in any CTM checkout:
#   bash scripts/dispatcher/install.sh            install (worktree + Task Scheduler task)
#   bash scripts/dispatcher/install.sh --remove   remove the task (the worktree stays)
# The task runs  node <worktree>/scripts/dispatcher/poll.cjs  every heartbeat_min,
# only while the user is logged on. Each poll can start headless claude sessions,
# which use the account's usage.
set -euo pipefail
TASK="CTM3 Dispatcher"
if [ "${1:-}" = "--remove" ]; then
  schtasks.exe //Delete //TN "$TASK" //F
  exit 0
fi

here=$(git rev-parse --show-toplevel)
wt="$(dirname "$here")/ctm3-wt/dispatcher"
if [ ! -d "$wt" ]; then
  git -C "$here" fetch -q origin main
  git -C "$here" worktree add -q --detach "$wt" origin/main   # the poller fast-forwards it every run
fi
node "$wt/scripts/check_registry.cjs"
node "$wt/scripts/dispatcher/poll.cjs" --launch-test
for l in "gates:assigned|All applicable gate roles were labelled on this PR (D-0040)" "process|Process defect: dispatcher, registry or nudge (template v2.4 §6.4)"; do
  gh label create "${l%%|*}" --description "${l#*|}" --color ededed 2>/dev/null || true
done

minutes=$(node -e 'console.log(require(process.argv[1]).load().settings.heartbeat_min)' "$wt/scripts/lib/registry.cjs")
node_exe=$(cygpath -w "$(command -v node)")
poll=$(cygpath -w "$wt/scripts/dispatcher/poll.cjs")
schtasks.exe //Create //F //SC MINUTE //MO "$minutes" //TN "$TASK" //TR "\"$node_exe\" \"$poll\""
echo "Installed \"$TASK\" every $minutes min. Dry run first:  node \"$wt/scripts/dispatcher/poll.cjs\" --dry-run"
