"""
Django settings for the GeoConnect project (config package).

Phase 1 — project setup:
- PostgreSQL database (via environment variables)
- Django REST Framework + CORS
- Django Channels + Redis channel layer (wired; WebSockets arrive in later phases)
- Environment variables loaded from backend/.env
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from backend/.env (development only).
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "insecure-dev-key-change-me")

# SECURITY WARNING: don't run with DEBUG turned on in production!
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

allowed_hosts = os.environ.get("ALLOWED_HOSTS", "")
if not allowed_hosts.strip():
    allowed_hosts = "localhost,127.0.0.1" if DEBUG else "*"
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(",") if host.strip()]

# Behind Render's TLS-terminating proxy, trust X-Forwarded-Proto so Django
# treats requests as HTTPS (affects secure cookies / absolute URLs).
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
# "daphne" must be the first app so the dev server serves ASGI (WebSocket-ready).
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "channels",
    # Project apps
    "accounts",
    "locations",
    "rooms",
    "messages.apps.MessagesConfig",
    "notifications",
    "events",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — PostgreSQL
#
# Production (Render/Railway) provides a single DATABASE_URL string; development uses
# the individual DB_* variables from backend/.env.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "geoconnect"),
        "USER": os.environ.get("geoconnect_db_9u0a_user", "geo_connect"),
        "PASSWORD": os.environ.get("QaVgqvABHclI3fJgAq8y3BCGbeSScX1n", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

database_url = os.environ.get("DATABASE_URL")
if database_url:
    from urllib.parse import urlsplit

    parsed = urlsplit(database_url)
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "127.0.0.1",
        "PORT": parsed.port or "5432",
    }

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

# ---------------------------------------------------------------------------
# Django Channels — Redis channel layer
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

# Built React app (frontend/dist copied here by the Docker build).
# WhiteNoise serves these files at their natural URL paths (/assets/...),
# so the SPA's own hashed bundles resolve without a /static/ prefix.
FRONTEND_BUILD_DIR = BASE_DIR / "frontend_dist"

# Media (user uploads such as profile pictures — used from Phase 2 on)
MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

WHITENOISE_ROOT = FRONTEND_BUILD_DIR if FRONTEND_BUILD_DIR.is_dir() else None

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Session-based auth only: the SPA signs in once and the session +
        # CSRF token protect every request. Basic auth is intentionally absent
        # so credentials are never sent on the wire.
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# ---------------------------------------------------------------------------
# CORS — allows the React dev server (Vite) to call the API
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# The React dev server is on a different origin; accept requests that carry
# a valid X-CSRFToken header (set up for the session-based auth in Phase 2).
CSRF_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_HTTPONLY = False

SESSION_COOKIE_SAMESITE = "Lax"
