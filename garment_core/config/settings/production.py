"""
Garment Core — Canlı ortam ayarları.

Ortam: DJANGO_SETTINGS_MODULE=config.settings.production
Zorunlu: SECRET_KEY. CSRF_TRUSTED_ORIGINS varsayılan olarak garmentcore.com; Railway URL için env ile geçersizleştirin.
"""
from .base import *  # noqa: F401, F403

import sentry_sdk
from django.core.exceptions import ImproperlyConfigured

# Production'da DEBUG varsayılan False
DEBUG = env.bool("DEBUG", default=False)

if DEBUG:
    import warnings

    warnings.warn("DEBUG=True production ayarlarında — canlıda kapatın.", RuntimeWarning)

# SECRET_KEY zorunlu; canlıda (DEBUG=False) django-insecure-* kabul edilmez
_secret = env("SECRET_KEY", default="")
if not _secret.strip():
    raise ImproperlyConfigured(
        "Production için ortam değişkeni SECRET_KEY tanımlayın."
    )
if _secret.startswith("django-insecure-") and not DEBUG:
    raise ImproperlyConfigured(
        "DEBUG=False iken güvenli bir SECRET_KEY kullanın (django-insecure- yasak)."
    )
SECRET_KEY = _secret

# Database — DATABASE_URL (PostgreSQL önerilir)
if env("DATABASE_URL", default=""):
    db_config = env.db("DATABASE_URL")
    db_config["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=600)
    DATABASES = {"default": db_config}

# Host / CSRF — joker yok; tam alan adlarını virgülle listeleyin
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
        ".railway.app",
        ".up.railway.app",
    ],
)

# HTTPS kökenleri — env ile tam liste (ör. Railway önizleme URL’si eklemek için)
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["https://garmentcore.com", "https://www.garmentcore.com"],
)

# TLS / çerez güvenliği (health check veya HTTP proxy testinde SECURE_SSL_REDIRECT=False geçici)
_use_tls = env.bool("USE_TLS", default=True)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=_use_tls)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=_use_tls)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=_use_tls)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000 if _use_tls else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=bool(SECURE_HSTS_SECONDS))
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Static files — S3 kullanılmıyorsa Whitenoise
STATIC_ROOT = BASE_DIR / "staticfiles"
if not env.bool("USE_S3", default=False):
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media — S3 kullanılmıyorsa yerel depolama (Railway'de ephemeral!)
# Railway container yeniden başladığında yerel media dosyaları silinir.
# Kalıcı depolama için USE_S3=True ve AWS credentials kullanın.
if not env.bool("USE_S3", default=False):
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# Sentry (varsa)
SENTRY_DSN = env.str("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)

# Railway / reverse proxy arkasında HTTPS algısı
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Celery — canlıda broker varsa eager kapalı (Redis URL tanımlı ve CELERY_TASK_ALWAYS_EAGER=False)
CELERY_TASK_ALWAYS_EAGER = env.bool(
    "CELERY_TASK_ALWAYS_EAGER",
    default=not bool(env("REDIS_URL", default="").strip()),
)
CELERY_TASK_EAGER_PROPAGATES = CELERY_TASK_ALWAYS_EAGER

# --- E-posta (SendGrid SMTP veya EMAIL_URL) ---
_sendgrid_key = env.str("SENDGRID_API_KEY", default="")
if _sendgrid_key:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env.str("EMAIL_HOST", default="smtp.sendgrid.net")
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="apikey")
    EMAIL_HOST_PASSWORD = _sendgrid_key
    DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="noreply@garmentcore.com")
    SERVER_EMAIL = env.str("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
elif env("EMAIL_URL", default=""):
    _email = env.email_url("EMAIL_URL")
    for _ek, _ev in _email.items():
        globals()[_ek] = _ev
    DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="noreply@garmentcore.com")
    SERVER_EMAIL = env.str("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

# --- Loglama: Railway’de konsol; isteğe bağlı dosya (DJANGO_LOG_FILE=/path/app.log) ---
_log_level = env.str("LOG_LEVEL", default="INFO")
_log_handlers = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": "verbose",
    },
}
_loggers_root = ["console"]

_django_log_file = env.str("DJANGO_LOG_FILE", default="").strip()
if _django_log_file:
    _log_handlers["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": _django_log_file,
        "maxBytes": env.int("DJANGO_LOG_FILE_MAX_BYTES", default=5 * 1024 * 1024),
        "backupCount": env.int("DJANGO_LOG_FILE_BACKUP_COUNT", default=3),
        "formatter": "verbose",
    }
    _loggers_root.append("file")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": _log_handlers,
    "root": {
        "handlers": _loggers_root,
        "level": _log_level,
    },
    "loggers": {
        "django": {
            "handlers": _loggers_root,
            "level": env.str("DJANGO_LOG_LEVEL", default=_log_level),
            "propagate": False,
        },
        "django.request": {
            "handlers": _loggers_root,
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": _loggers_root,
            "level": "WARNING",
            "propagate": False,
        },
    },
}