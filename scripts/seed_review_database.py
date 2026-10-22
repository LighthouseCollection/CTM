"""Seed only an existing local review SQLite DB; never connect to operational DBs."""

import argparse
import os
import secrets
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
parser = argparse.ArgumentParser()
parser.add_argument("database", type=Path)
args = parser.parse_args()
database = args.database.resolve()
review_root = (root / ".tmp").resolve()
if (
    not database.is_relative_to(review_root)
    or database.name != "isolated.sqlite3"
    or not database.is_file()
):
    raise SystemExit("Only an existing .tmp review isolated.sqlite3 is allowed.")
os.environ["DJANGO_SETTINGS_MODULE"] = "ctm.settings_test"
os.environ["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["CTM_SYNTHETIC_DEMO"] = "true"
from django.conf import settings

settings.DATABASES["default"]["NAME"] = str(database)
settings.MEDIA_ROOT = database.parent / "media"
import django

django.setup()
from django.core.management import call_command

call_command("seed_workflow_demo")
