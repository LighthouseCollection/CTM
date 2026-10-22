#!/usr/bin/env bash
# Rebuild the disposable QA-01 database from scratch: roles, migrations, grants, fixtures.
# Run from anywhere; ASSEMBLY points at the local (unpushed) integration checkout.
set -euo pipefail
HARNESS="$(cd "$(dirname "$0")" && pwd)"
ASSEMBLY="${ASSEMBLY:-$HARNESS/../../../../../../CTM-QA-assembly}"
cd "$ASSEMBLY"
if command -v cygpath >/dev/null; then SEP=";"; H="$(cygpath -w "$HARNESS")"; A="$(cygpath -w "$PWD")"; else SEP=":"; H="$HARNESS"; A="$PWD"; fi
export PYTHONPATH="$H$SEP$A"
RUN="uv run --frozen --python 3.12 python"
$RUN "$HARNESS/bootstrap_db.py" create
QA01_DB_ROLE=qa_owner DJANGO_SETTINGS_MODULE=qa01_settings $RUN manage.py migrate --noinput >/dev/null
$RUN "$HARNESS/bootstrap_db.py" grant >/dev/null
$RUN "$HARNESS/seed.py"
