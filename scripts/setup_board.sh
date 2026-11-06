#!/usr/bin/env bash
# Creates the CTM board (project-plan template v2.4 §4.3, gap G-2) once.
# Labels (status:ready, status:in-progress, size:*, agent:ctm3-*) already exist.
# Needs a gh token with the project scope:  gh auth refresh -s project
# Usage: bash scripts/setup_board.sh [owner]     (default LighthouseCollection)
set -euo pipefail
OWNER="${1:-LighthouseCollection}"
TITLE="CTM 3.0 board"

gh auth status 2>&1 | grep -q "'project'" || { echo "gh token lacks the project scope: run  gh auth refresh -s project"; exit 1; }

num=$(gh project list --owner "$OWNER" --format json --jq ".projects[] | select(.title == \"$TITLE\") | .number" | head -1)
if [ -z "$num" ]; then
  num=$(gh project create --owner "$OWNER" --title "$TITLE" --format json --jq .number)
  echo "created project $num"
fi
have=$(gh project field-list "$num" --owner "$OWNER" --format json --jq '.fields[].name')
field() { # name type [options]
  if grep -qx "$1" <<<"$have"; then echo "field $1 exists"; return; fi
  if [ "$2" = SINGLE_SELECT ]; then
    gh project field-create "$num" --owner "$OWNER" --name "$1" --data-type SINGLE_SELECT --single-select-options "$3" >/dev/null
  else
    gh project field-create "$num" --owner "$OWNER" --name "$1" --data-type "$2" >/dev/null
  fi
  echo "field $1 created"
}
# Columns: group the board view by Stage (views cannot be made by API).
field Stage SINGLE_SELECT "Backlog,Ready,In progress,Verify,Integrate,Done"
# Lanes come from agents.config.yaml.
lanes=$(node -e 'const r=require("./scripts/lib/registry.cjs").load();console.log([...new Set(r.roles.filter(x=>x.lane).map(x=>x.lane))].join(","))')
field Lane SINGLE_SELECT "$lanes"
field Priority SINGLE_SELECT "P0,P1,P2"
field Size SINGLE_SELECT "BUG,XS,S,M,L"
field Epic TEXT
field Owner TEXT
gh project link "$num" --owner "$OWNER" --repo "$OWNER/CTM" >/dev/null 2>&1 || true
echo "Board: https://github.com/users/$OWNER/projects/$num  (Milestone is the issue's own field; set the board view to group by Stage)"
