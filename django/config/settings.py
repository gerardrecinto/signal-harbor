import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-secret-key-change-in-prod")

DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "signals",
]

MIDDLEWARE = [
    "signals.middleware.ApiKeyMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

# Signal Harbor settings
SIGNAL_HARBOR_API_KEY: str = os.environ.get("SIGNAL_HARBOR_API_KEY", "dev-api-key")
SIGNAL_HARBOR_RISK_LOOKBACK_HOURS: int = int(os.environ.get("SIGNAL_HARBOR_RISK_LOOKBACK_HOURS", "24"))
SIGNAL_HARBOR_CACHE_TTL_SECONDS: int = int(os.environ.get("SIGNAL_HARBOR_CACHE_TTL_SECONDS", "60"))
SIGNAL_HARBOR_REDIS_URL: str = os.environ.get("SIGNAL_HARBOR_REDIS_URL", "redis://localhost:6379/0")
