"""Same acceptance tests against an isolated PostgreSQL database, never CTM live data."""

import os
import dj_database_url
from .settings_test import *

CELERY_TASK_ALWAYS_EAGER = os.environ.get("CTM_TASKS_EAGER", "true").lower() == "true"

DATABASES = {"default": dj_database_url.parse(os.environ["CTM_TEST_DATABASE_URL"])}
