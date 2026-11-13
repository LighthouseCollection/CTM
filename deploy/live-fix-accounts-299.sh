#!/usr/bin/env bash
# One-time council account correction on live CTM (VM 107), issue #299.
# Owner decision (chat, 2026-11-10): delete fryouhannayoussef@lacopts.org
# (Fr. Youhanna Youssef is frjohnyoussef@lacopts.org) and correct
# "Fr. Youhana Ibrahim" / fryouhanaibrahim@ to Fr. Youhanna Ibrahim /
# fryouhannaibrahim@lacopts.org.
#
#   preflight -> [apply only] database backup -> run the management command
#   fix_council_accounts_299 once, as the database owner role, in a throwaway
#   container from the live image.
#
# dry-run (default): the whole change runs in one transaction and is rolled
#   back. It prints which tables point to the account (table names and row
#   counts only) and whether the change would apply.
# apply: backup first (abort if it fails), then the same change, committed.
#   The command is one transaction: on any refusal or error nothing is written.
#   Every change writes an AuditEvent (source maintenance:fix_council_accounts_299).
# --suspend-if-history: if history rows point to fryouhannayoussef@, suspend
#   that account instead of stopping (history is never rewritten).
#
# Run as root on the VM:  bash deploy/live-fix-accounts-299.sh [dry-run|apply] [--suspend-if-history]
# Not run yet: the owner still chooses the access route (#299).
set -euo pipefail

MODE="${1:-dry-run}"
EXTRA="${2:-}"
[[ "$MODE" == "dry-run" || "$MODE" == "apply" ]] || { echo "usage: $0 [dry-run|apply] [--suspend-if-history]"; exit 2; }
[[ -z "$EXTRA" || "$EXTRA" == "--suspend-if-history" ]] || { echo "unknown option: $EXTRA"; exit 2; }

NET_INT="deploy_ctm-internal"
LIVE_IP="172.20.1.8"
PG="deploy-postgres-1"
ROOT="/opt/ctm"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$ROOT/backups"
DUMP="$BACKUP_DIR/pre-fix-accounts-299-$STAMP.sql.gz"
CONFIRM="ISSUE-299-COUNCIL-ACCOUNTS"
ENV_FILE=""

log() { printf '[fix-accounts-299 %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
[[ $EUID -eq 0 ]] || { echo "run as root"; exit 2; }
exec 9>/run/ctm-live-update.lock; flock -n 9 || { echo "a live update is running; try again later"; exit 2; }

cleanup() { if [[ -n "$ENV_FILE" ]]; then rm -f "$ENV_FILE"; fi; }
trap cleanup EXIT

# --- 1. preflight -------------------------------------------------------------
LIVE="$(docker ps --filter "network=$NET_INT" --format '{{.Names}}' | while read -r n; do
  ip="$(docker inspect -f "{{(index .NetworkSettings.Networks \"$NET_INT\").IPAddress}}" "$n")"
  if [[ "$ip" == "$LIVE_IP" ]]; then echo "$n"; fi; done | head -1 || true)"
[[ -n "$LIVE" ]] || { log "no running container holds $LIVE_IP on $NET_INT"; exit 2; }
IMAGE="$(docker inspect -f '{{.Config.Image}}' "$LIVE")"
docker inspect "$PG" >/dev/null
log "live: $LIVE ($IMAGE); mode: $MODE${EXTRA:+ $EXTRA}"
docker run --rm "$IMAGE" python manage.py help fix_council_accounts_299 >/dev/null 2>&1 \
  || { log "the live image has no fix_council_accounts_299 command; deploy the commit that adds it first"; exit 2; }
install -d -m 0700 "$ROOT/secrets"
ENV_FILE="$(umask 077; mktemp "$ROOT/secrets/fix-accounts-299-XXXXXX.env")"
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$LIVE" \
  | grep -vE '^(PATH|LANG|GPG_KEY|PYTHON_VERSION|PYTHON_SHA256|PYTHONDONTWRITEBYTECODE|PYTHONUNBUFFERED|PIP_NO_CACHE_DIR)=' \
  | grep -v '^$' >"$ENV_FILE"

# --- 2. backup (apply only) ---------------------------------------------------
ARGS=()
if [[ "$MODE" == "apply" ]]; then
  install -d -m 0700 "$BACKUP_DIR"
  docker exec "$PG" sh -c 'export PGPASSWORD="$POSTGRES_PASSWORD"; pg_dump --create -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip >"$DUMP"
  gzip -t "$DUMP"
  [[ "$(stat -c%s "$DUMP")" -gt 10000 ]] || { log "backup too small; aborting, nothing was written"; exit 1; }
  log "database backup: $DUMP ($(du -h "$DUMP" | cut -f1))"
  ARGS=(--apply --confirmation "$CONFIRM")
fi
if [[ -n "$EXTRA" ]]; then ARGS+=("$EXTRA"); fi

# --- 3. run as the owner role -------------------------------------------------
OWNER_RUN='
import os, sys, urllib.parse as u
p = u.urlsplit(os.environ["DATABASE_URL"])
user = u.quote(os.environ["POSTGRES_USER"], safe="")
pw = u.quote(os.environ["POSTGRES_PASSWORD"], safe="")
host = p.hostname + (":%d" % p.port if p.port else "")
os.environ["DATABASE_URL"] = u.urlunsplit((p.scheme, "%s:%s@%s" % (user, pw, host), p.path, p.query, ""))
os.execvp("python", ["python", "manage.py", "fix_council_accounts_299", *sys.argv[1:]])
'
if docker run --rm --env-file "$ENV_FILE" --network "$NET_INT" "$IMAGE" python -c "$OWNER_RUN" "${ARGS[@]}"; then
  if [[ "$MODE" == "apply" ]]; then log "done (apply); backup kept at $DUMP"; else log "done (dry run; nothing was written)"; fi
else
  log "STOPPED: the command refused or failed; it runs in one transaction, so nothing was written"
  if [[ "$MODE" == "apply" ]]; then log "backup kept at $DUMP"; fi
  exit 1
fi
