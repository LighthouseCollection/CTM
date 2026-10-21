import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-for-server")
os.environ["CTM_ENVIRONMENT"] = "test"
from .settings import *

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = ["testserver", "localhost"]
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CTM_SCAN_REQUIRED = False
MEDIA_ROOT = BASE_DIR / ".test-media"
MIDDLEWARE = [
    item for item in MIDDLEWARE if item != "whitenoise.middleware.WhiteNoiseMiddleware"
]
