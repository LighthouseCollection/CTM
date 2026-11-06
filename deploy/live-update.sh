#!/usr/bin/env bash
# Update the hand-started live CTM container on VM 107 to a newer commit.
#
# Live today is not the Compose `django` service: it is one container started by
# hand on the `deploy` project's networks, with fixed IP 172.20.1.8 on
# deploy_ctm-internal (the 10.0.0.40:8000 listener forwards there) and its
# uploads inside the container (no volume). This script replaces it safely:
#
#   preflight -> database backup -> fetch code -> build -> migrate (owner role)
#   -> start candidate -> health + CDN + Microsoft reachability checks
#   -> swap (stop old, copy uploads to /opt/ctm/media-live, take IP .8)
#   -> health check through 10.0.0.40:8000 -> automatic rollback on any failure.
#
# The old container is stopped, never deleted. Settings are copied from the
# running container into a root-only file; no value is ever printed.
#
# Run as root on the VM:  bash deploy/live-update.sh [commit]   (default: main)
set -Eeuo pipefail

REPO="https://github.com/LighthouseCollection/CTM.git"
NET_INT="deploy_ctm-internal"
NET_EGR="deploy_ctm-egress"
LIVE_IP="172.20.1.8"
PG="deploy-postgres-1"
HOST_HDR="ctm.lighthouseway.org"
FRONT="http://10.0.0.40:8000"
ROOT="/opt/ctm"
MEDIA_DIR="$ROOT/media-live"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$ROOT/backups"
DUMP="$BACKUP_DIR/pre-update-$STAMP.sql.gz"
PHASE="preflight"
MIGRATED="no"
SWAPPED="no"
NEW=""
OLD=""

log() { printf '[live-update %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
[[ $EUID -eq 0 ]] || { echo "run as root"; exit 2; }
exec 9>/run/ctm-live-update.lock; flock -n 9 || { echo "another update is running"; exit 2; }

restore_db() {
  log "restoring database from $(basename "$DUMP")"
  docker exec "$PG" sh -c 'export PGPASSWORD="$POSTGRES_PASSWORD"; dropdb -U "$POSTGRES_USER" --force "$POSTGRES_DB"'
  gunzip -c "$DUMP" | docker exec -i "$PG" sh -c 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres' >/dev/null
}

rollback() {
  local code=$?
  trap - ERR
  log "FAILED during '$PHASE' (exit $code); rolling back"
  if [[ -n "$NEW" ]]; then docker rm -f "$NEW" >/dev/null 2>&1 || true; fi
  if [[ "$MIGRATED" == "yes" ]]; then
    [[ "$SWAPPED" == "yes" ]] || docker stop "$OLD" >/dev/null 2>&1 || true
    restore_db || log "DATABASE RESTORE FAILED: restore $DUMP by hand"
  fi
  if [[ -n "$OLD" ]]; then docker start "$OLD" >/dev/null && log "old container $OLD running again"; fi
  log "ROLLED BACK. Live is the previous version."
  exit 1
}
trap rollback ERR

# --- 1. preflight -------------------------------------------------------------
OLD="$(docker ps --filter "network=$NET_INT" --format '{{.Names}}' | while read -r n; do
  ip="$(docker inspect -f "{{(index .NetworkSettings.Networks \"$NET_INT\").IPAddress}}" "$n")"
  if [[ "$ip" == "$LIVE_IP" ]]; then echo "$n"; fi; done | head -1 || true)"
[[ -n "$OLD" ]] || { log "no running container holds $LIVE_IP on $NET_INT"; exit 2; }
OLD_IMAGE="$(docker inspect -f '{{.Config.Image}}' "$OLD")"
log "live now: $OLD ($OLD_IMAGE)"
docker inspect "$PG" >/dev/null
SHA="$(git ls-remote "$REPO" "${1:-refs/heads/main}" | cut -c1-7)"
[[ -n "$SHA" ]] || SHA="${1:0:7}"
[[ -n "$SHA" ]] || { log "cannot resolve commit"; exit 2; }
IMAGE="ctm-application:$SHA"
NEW="ctm-live-$SHA"
[[ "$OLD" != "$NEW" ]] || { log "live already runs $SHA"; exit 0; }
docker rm -f "$NEW" >/dev/null 2>&1 || true
NEW=""
log "updating to $SHA"
FREE_GB="$(df -BG --output=avail / | tail -1 | tr -dc 0-9)"
(( FREE_GB >= 8 )) || { log "only ${FREE_GB} GB free; need 8"; exit 2; }

# --- 2. backup ----------------------------------------------------------------
PHASE="backup"
install -d -m 0700 "$BACKUP_DIR"
docker exec "$PG" sh -c 'export PGPASSWORD="$POSTGRES_PASSWORD"; pg_dump --create -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip >"$DUMP"
[[ "$(gunzip -c "$DUMP" | head -c 100000 | grep -c 'CREATE DATABASE')" -ge 1 ]]
log "database backup: $DUMP ($(du -h "$DUMP" | cut -f1))"

# --- 3. fetch code + build ----------------------------------------------------
PHASE="build"
SRC="$ROOT/releases/$SHA"
if [[ ! -d "$SRC/.git" ]]; then
  rm -rf "$SRC"
  git clone -q "$REPO" "$SRC"
fi
git -C "$SRC" fetch -q origin
git -C "$SRC" checkout -q "$SHA"
CDN="$(grep -oE 'cdn/[0-9]+\.[0-9]+\.[0-9]+/' "$SRC/ctm/settings.py" | head -1)"
log "building $IMAGE (design system $CDN); this takes a few minutes"
docker build -q -f "$SRC/deploy/Dockerfile" -t "$IMAGE" "$SRC" >/dev/null
log "built $IMAGE"

# --- 4. settings: copy the running container's own environment ---------------
ENV_FILE="$ROOT/secrets/live-$SHA.env"
install -d -m 0700 "$ROOT/secrets"
( umask 077
  docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$OLD" \
    | grep -vE '^(PATH|LANG|GPG_KEY|PYTHON_VERSION|PYTHON_SHA256|PYTHONDONTWRITEBYTECODE|PYTHONUNBUFFERED|PIP_NO_CACHE_DIR)=' \
    | grep -v '^$' >"$ENV_FILE" )
MEDIA_IN="$(docker exec "$OLD" printenv CTM_MEDIA_ROOT || echo /srv/ctm/media)"
log "settings copied ($(wc -l <"$ENV_FILE") names); uploads live at $MEDIA_IN in the old container"

# --- 5. migrate as the owner role --------------------------------------------
PHASE="migrate"
OWNER_MIGRATE='
import os, urllib.parse as u
p = u.urlsplit(os.environ["DATABASE_URL"])
user = u.quote(os.environ["POSTGRES_USER"], safe="")
pw = u.quote(os.environ["POSTGRES_PASSWORD"], safe="")
host = p.hostname + (":%d" % p.port if p.port else "")
os.environ["DATABASE_URL"] = u.urlunsplit((p.scheme, "%s:%s@%s" % (user, pw, host), p.path, p.query, ""))
os.execvp("python", ["python", "manage.py", "migrate", "--noinput"])
'
MIGRATED="yes"
docker run --rm --env-file "$ENV_FILE" --network "$NET_INT" "$IMAGE" python -c "$OWNER_MIGRATE"
log "migrations applied"

# --- 6. start the candidate beside the old container -------------------------
PHASE="candidate"
install -d -m 0700 -o 1000 -g 1000 "$MEDIA_DIR"
NEW="ctm-live-$SHA"
docker create --name "$NEW" --restart unless-stopped --env-file "$ENV_FILE" \
  --network "$NET_INT" -v "$MEDIA_DIR:$MEDIA_IN" "$IMAGE" >/dev/null
docker network connect "$NET_EGR" "$NEW"
docker start "$NEW" >/dev/null

CHECK='
import os, re, socket, sys, time, urllib.request
H = {"Host": os.environ["HOST_HDR"], "X-Forwarded-Proto": "https"}
def get(path):
    req = urllib.request.Request("http://127.0.0.1:8000" + path, headers=H)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, r.read().decode("utf-8", "replace")
for i in range(40):
    try:
        s, b = get("/health/")
        if s == 200 and re.search(r"\"status\": *\"ok\"", b):
            break
    except Exception:
        pass
    time.sleep(3)
else:
    sys.exit("health never became ok")
s, b = get("/version.json"); assert s == 200 and "version" in b, "version.json"
s, b = get("/"); assert s == 200, "home page"
cdn = os.environ["CDN"]
assert cdn in b, "page does not load " + cdn
for h in ("login.microsoftonline.com", "graph.microsoft.com"):
    socket.create_connection((h, 443), timeout=10).close()
print("checks ok: /health/, /version.json, home page on " + cdn + ", Microsoft reachable")
'
docker exec -e HOST_HDR="$HOST_HDR" -e CDN="$CDN" "$NEW" python -c "$CHECK"

# --- 7. swap ------------------------------------------------------------------
PHASE="swap"
log "switching: stopping $OLD (kept for rollback)"
docker stop "$OLD" >/dev/null
SWAPPED="yes"
docker cp "$OLD:$MEDIA_IN/." "$MEDIA_DIR/"
chown -R 1000:1000 "$MEDIA_DIR"
log "uploads copied to $MEDIA_DIR ($(du -sh "$MEDIA_DIR" | cut -f1))"
docker network disconnect "$NET_INT" "$NEW"
docker network connect --ip "$LIVE_IP" "$NET_INT" "$NEW"

# --- 8. check through the real front door -------------------------------------
PHASE="health"
ok=""
for i in $(seq 1 20); do
  if curl -fsS --max-time 5 -H "Host: $HOST_HDR" -H "X-Forwarded-Proto: https" "$FRONT/health/" | grep -q '"status": *"ok"' \
    && curl -fsS --max-time 10 -H "Host: $HOST_HDR" -H "X-Forwarded-Proto: https" "$FRONT/" | grep -q "$CDN"; then
    ok=1; break
  fi
  sleep 3
done
[[ -n "$ok" ]] || false
trap - ERR
docker update --restart no "$OLD" >/dev/null
log "DONE. Live is $NEW ($IMAGE, design system $CDN)."
log "Previous: $OLD (stopped, kept). Backup: $DUMP. Uploads: $MEDIA_DIR"
