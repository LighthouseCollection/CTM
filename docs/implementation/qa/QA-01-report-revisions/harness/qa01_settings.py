"""Isolated QA-01 settings. Never use publicly: built on ctm.settings_test (relaxed transport/scan).

QA01_DB_ROLE selects the credential: 'qa_owner' for migrate/seed, 'ctm_app' for the HTTP runtime.
Email uses the in-memory backend; Stripe/transcription credentials are empty; Celery runs eagerly.
"""

import os
from pathlib import Path

import dj_database_url

from ctm.settings_test import *  # noqa: F401,F403
from qa_env import RUN_DIR, load_env

_role = os.environ.get("QA01_DB_ROLE", "ctm_app")
DATABASES = {"default": dj_database_url.parse(load_env()[_role])}
MEDIA_ROOT = RUN_DIR / "media"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
DEBUG = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
STRIPE_SECRET_KEY = ""
STRIPE_WEBHOOK_SECRET = ""
