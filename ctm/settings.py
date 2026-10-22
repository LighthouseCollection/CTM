import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "Set DJANGO_SECRET_KEY; no production fallback secret is provided."
    )
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,ctm.lighthouseway.org"
).split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "DJANGO_CSRF_TRUSTED_ORIGINS", "https://ctm.lighthouseway.org"
).split(",")
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "allauth.socialaccount.providers.microsoft",
    "django_celery_beat",
    "tribunal",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "tribunal.middleware.PrivateResponseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "tribunal.middleware.DatabaseSessionIdentityMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tribunal.middleware.ActiveAccountMiddleware",
    "tribunal.middleware.DatabaseActorMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "ctm.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "ctm.wsgi.application"
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if (
    not DEBUG
    and os.environ.get("CTM_ENVIRONMENT") != "test"
    and not DATABASE_URL.startswith(("postgres://", "postgresql://"))
):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "Production requires an explicit PostgreSQL DATABASE_URL."
    )
DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL or f"sqlite:///{BASE_DIR / 'development.sqlite3'}", conn_max_age=60
    )
}
AUTH_USER_MODEL = "tribunal.Account"
AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]
SITE_ID = 1
SOCIALACCOUNT_ONLY = True
# Provider-only mode has no CTM email/password verification flow; adapter requires verified identity.
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_SIGNUP_FIELDS = ["email*", "first_name*", "last_name*"]
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False
SOCIALACCOUNT_ADAPTER = "tribunal.auth.AccountAdapter"
ACCOUNT_ADAPTER = "tribunal.auth.ProviderOnlyAdapter"
SOCIALACCOUNT_PROVIDERS = {}
MICROSOFT_TENANT_ID = os.environ.get("MICROSOFT_TENANT_ID", "")
for provider, prefix in [
    ("google", "GOOGLE"),
    ("apple", "APPLE"),
    ("microsoft", "MICROSOFT"),
]:
    client_id = os.environ.get(f"{prefix}_CLIENT_ID")
    if client_id:
        config = {
            "APPS": [
                {
                    "client_id": client_id,
                    "secret": os.environ.get(f"{prefix}_CLIENT_SECRET", ""),
                    "key": os.environ.get(f"{prefix}_KEY_ID", ""),
                }
            ]
        }
        if provider == "microsoft":
            config["tenant"] = os.environ.get("MICROSOFT_TENANT_ID", "organizations")
        SOCIALACCOUNT_PROVIDERS[provider] = config
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("ar", "العربية")]
TIME_ZONE = "America/Los_Angeles"
USE_TZ = True
USE_I18N = True
STATIC_URL = "/static/"
STATIC_ROOT = Path(os.environ.get("CTM_STATIC_ROOT", BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_ROOT = Path(os.environ.get("CTM_MEDIA_ROOT", BASE_DIR / "private-media"))
FILE_UPLOAD_PERMISSIONS = 0o600
DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = not DEBUG
if os.environ.get("CTM_TRUST_PROXY_SSL", "false").lower() == "true":
    # Deployment must restrict ingress to the proxy, which overwrites this header.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_BEAT_SCHEDULE = {
    "dispatch-durable-outbox": {
        "task": "tribunal.tasks.dispatch_outbox",
        "schedule": 30.0,
    },
    "draft-retention": {"task": "tribunal.tasks.retention", "schedule": 3600.0},
}
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "ctm@lighthouseway.org")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
CLAMAV_HOST = os.environ.get("CLAMAV_HOST", "")
CLAMAV_PORT = int(os.environ.get("CLAMAV_PORT", "3310"))
CTM_SCAN_REQUIRED = True
CTM_TRIBUNAL_ID = os.environ.get("CTM_TRIBUNAL_ID", "")
PLENIX_BASE = "https://design-system.lighthouseway.org/cdn/0.58.0/"
