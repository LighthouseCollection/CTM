#!/usr/bin/env bash
# Load the fictitious demo cases into live CTM (VM 107), the same data as the
# local review copy: seed_workflow_demo (33 cases, sessions, decrees, reports,
# messages) and seed_new_applications_demo (the New Applications queue), then
# seed_seat_cases: every council seat holder topped up to five open, fully
# filled cases. Prints "open cases per seat holder: <name> <email> <n>".
#
#   preflight -> database backup -> run the seeders once, as the database
#   owner role, in a throwaway container from the live image with live's
#   upload folder -> on any failure, restore the backup.
#
# Both seeders refuse if live holds any non-demo case, and refuse (before any
# write) if a council account's role differs from their roster. Fictional
# names only; no email, payment or signature is sent or faked.
#
# Run as root on the VM:  bash deploy/live-seed-demo.sh
# From the PVE shell, use the copy in the release that live runs:
#   qm guest exec 107 --timeout 900 -- bash -c 'bash /opt/ctm/releases/$(docker inspect -f "{{.Config.Image}}" $(docker ps -q --filter name=ctm-live- | head -1) | cut -d: -f2)/deploy/live-seed-demo.sh'
set -euo pipefail

NET_INT="deploy_ctm-internal"
LIVE_IP="172.20.1.8"
PG="deploy-postgres-1"
ROOT="/opt/ctm"
MEDIA_DIR="$ROOT/media-live"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$ROOT/backups"
DUMP="$BACKUP_DIR/pre-demo-seed-$STAMP.sql.gz"
CONFIRM="FICTITIOUS-DEMO-DATA-ONLY"
ENV_FILE=""
SEEDED="no"

log() { printf '[live-seed-demo %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
[[ $EUID -eq 0 ]] || { echo "run as root"; exit 2; }
exec 9>/run/ctm-live-update.lock; flock -n 9 || { echo "a live update is running; try again later"; exit 2; }

cleanup() { if [[ -n "$ENV_FILE" ]]; then rm -f "$ENV_FILE"; fi; }
trap cleanup EXIT

restore_db() {
  log "restoring database from $(basename "$DUMP")"
  docker stop "$LIVE" >/dev/null 2>&1 || true
  docker exec "$PG" sh -c 'export PGPASSWORD="$POSTGRES_PASSWORD"; dropdb -U "$POSTGRES_USER" --force "$POSTGRES_DB"'
  gunzip -c "$DUMP" | docker exec -i "$PG" sh -c 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres' >/dev/null
  docker start "$LIVE" >/dev/null
}

on_error() {
  local code=$?
  trap - ERR
  log "FAILED (exit $code)"
  if [[ "$SEEDED" == "yes" ]]; then
    restore_db || log "DATABASE RESTORE FAILED: restore $DUMP by hand"
    log "database restored; live is unchanged"
  else
    log "nothing was written; live is unchanged"
  fi
  exit 1
}
trap on_error ERR

# --- 1. preflight -------------------------------------------------------------
LIVE="$(docker ps --filter "network=$NET_INT" --format '{{.Names}}' | while read -r n; do
  ip="$(docker inspect -f "{{(index .NetworkSettings.Networks \"$NET_INT\").IPAddress}}" "$n")"
  if [[ "$ip" == "$LIVE_IP" ]]; then echo "$n"; fi; done | head -1 || true)"
[[ -n "$LIVE" ]] || { log "no running container holds $LIVE_IP on $NET_INT"; exit 2; }
IMAGE="$(docker inspect -f '{{.Config.Image}}' "$LIVE")"
docker inspect "$PG" >/dev/null
log "live: $LIVE ($IMAGE)"
install -d -m 0700 "$ROOT/secrets"
ENV_FILE="$(umask 077; mktemp "$ROOT/secrets/demo-seed-XXXXXX.env")"
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$LIVE" \
  | grep -vE '^(PATH|LANG|GPG_KEY|PYTHON_VERSION|PYTHON_SHA256|PYTHONDONTWRITEBYTECODE|PYTHONUNBUFFERED|PIP_NO_CACHE_DIR)=' \
  | grep -v '^$' >"$ENV_FILE"
MEDIA_IN="$(docker exec "$LIVE" printenv CTM_MEDIA_ROOT || echo /srv/ctm/media)"
[[ -d "$MEDIA_DIR" ]] || { log "upload folder $MEDIA_DIR is missing"; exit 2; }

# --- 2. backup ----------------------------------------------------------------
install -d -m 0700 "$BACKUP_DIR"
docker exec "$PG" sh -c 'export PGPASSWORD="$POSTGRES_PASSWORD"; pg_dump --create -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip >"$DUMP"
gzip -t "$DUMP"
[[ "$(stat -c%s "$DUMP")" -gt 10000 ]]
log "database backup: $DUMP ($(du -h "$DUMP" | cut -f1))"

# --- 3. seed as the owner role ------------------------------------------------
OWNER_SEED='
import os, subprocess, sys, urllib.parse as u
p = u.urlsplit(os.environ["DATABASE_URL"])
user = u.quote(os.environ["POSTGRES_USER"], safe="")
pw = u.quote(os.environ["POSTGRES_PASSWORD"], safe="")
host = p.hostname + (":%d" % p.port if p.port else "")
os.environ["DATABASE_URL"] = u.urlunsplit((p.scheme, "%s:%s@%s" % (user, pw, host), p.path, p.query, ""))
confirm = sys.argv[1]
for command in ["seed_workflow_demo", "seed_new_applications_demo", "seed_seat_cases"]:
    subprocess.run(["python", "manage.py", command, "--live-fictitious", "--confirmation", confirm], check=True)
'
SEEDED="yes"
docker run --rm --env-file "$ENV_FILE" --network "$NET_INT" -v "$MEDIA_DIR:$MEDIA_IN" "$IMAGE" \
  python -c "$OWNER_SEED" "$CONFIRM" | { grep '^open cases per seat holder: ' || true; }
chown -R 1000:1000 "$MEDIA_DIR"

# --- 4. report (counts only) --------------------------------------------------
COUNTS="$(docker exec -i "$PG" sh -c 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
select count(*) filter (where origin in ('synthetic', 'demo')), count(*) from tribunal_case;
SQL
)"
log "demo cases / all cases on live: ${COUNTS/|/ / }"
log "done; backup kept at $DUMP"
