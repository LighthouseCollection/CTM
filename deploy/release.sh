#!/usr/bin/env bash
# CTM release: backup -> build -> migrate -> restart -> health check -> automatic rollback.
# Runs on the CTM VM (self-hosted GitHub runner) from .github/workflows/deploy.yml.
# Usage: deploy/release.sh staging|production <commit-sha>
#
# Never prints secret values: the env file is sourced, never echoed, and every
# database command reads its password from the container's own environment.
set -Eeuo pipefail

TARGET="${1:?usage: release.sh staging|production <commit-sha>}"
TAG="${2:?usage: release.sh staging|production <commit-sha>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$TARGET" in
  staging)
    PROJECT="${CTM_STAGING_PROJECT:-ctm-staging}"
    ENV_FILE="${CTM_STAGING_ENV_FILE:-/srv/ctm-staging/.env}"
    STATE_DIR="${CTM_STAGING_STATE_DIR:-/srv/ctm-staging}"
    HEALTH_URL="${CTM_STAGING_HEALTH_URL:-http://10.0.0.40:8001/health/}"
    COMPOSE_FILES=(-f "$HERE/docker-compose.yml" -f "$HERE/docker-compose.release.yml" -f "$HERE/docker-compose.staging.yml")
    ;;
  production)
    # No default: the production project must match the one already running
    # (`docker compose ls` on the VM), or Compose would start an empty database.
    PROJECT="${CTM_PROD_PROJECT:?Set CTM_PROD_PROJECT to the running production Compose project}"
    ENV_FILE="${CTM_PROD_ENV_FILE:-/srv/ctm/.env}"
    STATE_DIR="${CTM_PROD_STATE_DIR:-/srv/ctm}"
    HEALTH_URL="${CTM_PROD_HEALTH_URL:-https://ctm.lighthouseway.org/health/}"
    COMPOSE_FILES=(-f "$HERE/docker-compose.yml" -f "$HERE/docker-compose.release.yml")
    ;;
  *) echo "::error::unknown target '$TARGET'"; exit 2 ;;
esac

BACKUP_DIR="$STATE_DIR/backups"
APP_SERVICES=(django celery-default celery-documents celery-media celery-beat)
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP="$BACKUP_DIR/pre-deploy-$STAMP.sql.gz"
OUT="${GITHUB_OUTPUT:-/dev/null}"
PHASE="preflight"
MIGRATED="no"

log() { printf '[release %s %s] %s\n' "$TARGET" "$(date -u +%H:%M:%S)" "$*"; }
dc() { CTM_IMAGE_TAG="$CURRENT_TAG" docker compose -p "$PROJECT" --env-file "$ENV_FILE" "${COMPOSE_FILES[@]}" "$@"; }

health_check() {
  # /health/ must report ok, and the sign-in page and /version.json must
  # answer 200 through the same URL users reach (#63: a 502 behind the proxy).
  local i body base="${HEALTH_URL%/health/}"
  for i in $(seq 1 30); do
    if body="$(curl -fsS --max-time 5 "$HEALTH_URL" 2>/dev/null)" && grep -q '"status": *"ok"' <<<"$body" \
      && curl -fsS --max-time 5 -o /dev/null "$base/" \
      && curl -fsS --max-time 5 "$base/version.json" 2>/dev/null | grep -q '"version"'; then
      log "health ok ($base: /health/, /, /version.json; try $i)"
      return 0
    fi
    sleep 5
  done
  log "health check failed: $base (/health/, / or /version.json)"
  return 1
}

running_tag() {
  local id
  id="$(dc ps -q django 2>/dev/null || true)"
  [[ -n "$id" ]] && docker inspect --format '{{.Config.Image}}' "$id" | sed 's/.*://'
}

restore_dump() {
  log "restoring database from $(basename "$DUMP")"
  dc stop "${APP_SERVICES[@]}" || true
  dc exec -T postgres sh -c 'export PGPASSWORD="$POSTGRES_PASSWORD"; dropdb -U "$POSTGRES_USER" --maintenance-db=postgres --force "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" -O "$POSTGRES_USER" "$POSTGRES_DB"'
  gunzip -c "$DUMP" | dc exec -T postgres sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null
}

rollback() {
  local code=$?
  trap - ERR
  log "FAILED during '$PHASE' (exit $code); rolling back"
  echo "failed_phase=$PHASE" >>"$OUT"
  if [[ "$PHASE" == "preflight" || "$PHASE" == "backup" ]]; then
    log "nothing was changed; no rollback needed"
    echo "rolled_back=not-needed" >>"$OUT"
    exit "$code"
  fi
  if [[ "$MIGRATED" == "yes" && -s "$DUMP" ]]; then
    restore_dump || { log "DATABASE RESTORE FAILED: restore $DUMP by hand"; echo "rolled_back=restore-failed" >>"$OUT"; exit "$code"; }
  fi
  if [[ -n "$PREVIOUS_TAG" ]]; then
    CURRENT_TAG="$PREVIOUS_TAG"
    log "restarting previous image $PREVIOUS_TAG"
    if dc up -d --no-build --remove-orphans && health_check; then
      echo "rolled_back=yes" >>"$OUT"
    else
      echo "rolled_back=unhealthy" >>"$OUT"
    fi
  else
    log "no previous release: stopping the application services"
    dc stop "${APP_SERVICES[@]}" || true
    echo "rolled_back=stopped" >>"$OUT"
  fi
  exit "$code"
}

# --- preflight -------------------------------------------------------------
[[ "$TAG" =~ ^[0-9a-f]{40}$ ]] || { echo "::error::commit must be a full 40-character SHA"; exit 2; }
[[ -r "$ENV_FILE" ]] || { echo "::error::env file $ENV_FILE is missing on the server"; exit 2; }
mkdir -p "$BACKUP_DIR"
CURRENT_TAG="$TAG"
# Tag the images that are running now, so a rollback can restart exactly them
# (also on the first release through this script, before images were tagged).
PREVIOUS_TAG=""
PREVIOUS_COMMIT="$(cat "$STATE_DIR/deployed-tag" 2>/dev/null || echo unknown)"
for pair in django:ctm-app celery-documents:ctm-docworker celery-media:ctm-mediaworker; do
  svc="${pair%%:*}"; repo="${pair#*:}"
  id="$(dc ps -q "$svc" 2>/dev/null || true)"
  if [[ -n "$id" ]]; then
    docker tag "$(docker inspect --format '{{.Image}}' "$id")" "$repo:rollback-$STAMP"
    PREVIOUS_TAG="rollback-$STAMP"
  fi
done
log "deploying $TAG (previous commit: $PREVIOUS_COMMIT, rollback images: ${PREVIOUS_TAG:-none}) to project $PROJECT"
echo "commit=$TAG" >>"$OUT"
echo "previous=$PREVIOUS_COMMIT" >>"$OUT"
trap rollback ERR

# --- 1. backup (abort on failure) -----------------------------------------
PHASE="backup"
if [[ -n "$(dc ps -q postgres 2>/dev/null)" ]]; then
  dc exec -T postgres sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-password' | gzip >"$DUMP.part"
  gzip -t "$DUMP.part"
  [[ "$(stat -c %s "$DUMP.part")" -gt 1024 ]] || { echo "::error::database dump is empty"; false; }
  mv "$DUMP.part" "$DUMP"
  chmod 600 "$DUMP"
  log "database backup $DUMP ($(du -h "$DUMP" | cut -f1))"
  echo "backup=$DUMP" >>"$OUT"
else
  log "no running database yet (first deploy): nothing to back up"
  echo "backup=none-first-deploy" >>"$OUT"
fi
if [[ "$TARGET" == "production" ]]; then
  # Media snapshot. RESTIC_REPOSITORY and RESTIC_PASSWORD_FILE come from the env file.
  set -a; # shellcheck disable=SC1090
  . "$ENV_FILE"; set +a
  [[ -n "${RESTIC_REPOSITORY:-}" ]] || { echo "::error::RESTIC_REPOSITORY is not set in $ENV_FILE; refusing to deploy without a media snapshot"; exit 3; }
  restic backup --quiet --tag "pre-deploy-$STAMP" "${CTM_MEDIA_DIR:-/srv/ctm/media}"
  log "media snapshot pre-deploy-$STAMP"
fi

# --- 2. build ---------------------------------------------------------------
PHASE="build"
dc build --pull

# --- 3. migrate (as the owner role; the runtime roles are RLS-subject) -----
PHASE="migrate"
dc up -d --wait postgres redis
MIGRATED="yes"
# `migrate` (docker-compose.release.yml) connects as the owner role; Compose
# fills in the password from the env file, so it never reaches a command line.
dc --profile release run --rm --no-deps -T migrate

if [[ "$TARGET" == "staging" ]]; then
  PHASE="seed"
  # Synthetic accounts only; seed_demo refuses to run without this flag.
  dc --profile release run --rm --no-deps -T -e CTM_SYNTHETIC_DEMO=true migrate python manage.py seed_demo
fi

# --- 4. restart ---------------------------------------------------------------
PHASE="restart"
dc up -d --no-build --remove-orphans

# --- 5. health check on the deployed commit -----------------------------------
PHASE="health"
health_check
[[ "$(running_tag)" == "$TAG" ]] || { log "running image is not $TAG"; false; }

trap - ERR
echo "$TAG" >"$STATE_DIR/deployed-tag"
echo "rolled_back=no" >>"$OUT"
# Keep the 14 newest pre-deploy dumps and the 3 newest rollback image sets.
ls -1t "$BACKUP_DIR"/pre-deploy-*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f || true
for repo in ctm-app ctm-docworker ctm-mediaworker; do
  docker image ls --format '{{.Repository}}:{{.Tag}}' "$repo" | grep ':rollback-' | sort -r | tail -n +4 | xargs -r docker rmi >/dev/null || true
done
log "deployed $TAG"
