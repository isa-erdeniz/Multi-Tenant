"""
Django settings for mehlr_1.0 — ErdenizTech AI Engine.
"""
import os
from pathlib import Path

from celery.schedules import crontab
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default=(
        'localhost,127.0.0.1,'
        'erdeniztech.com,www.erdeniztech.com,'
        'dressifye.com,www.dressifye.com,'
        'hairinfinitye.com,www.hairinfinitye.com,'
        'stylecoree.com,www.stylecoree.com,'
        'styleforhuman.com,www.styleforhuman.com,'
        'stylecore.com,www.stylecore.com'
    ),
    cast=lambda v: [s.strip() for s in v.split(',')]
)
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default=(
        'http://localhost:8000,'
        'https://erdeniztech.com,https://www.erdeniztech.com,'
        'https://dressifye.com,https://www.dressifye.com,'
        'https://hairinfinitye.com,https://www.hairinfinitye.com,'
        'https://stylecoree.com,https://www.stylecoree.com,'
        'https://styleforhuman.com,https://www.styleforhuman.com,'
        'https://stylecore.com,https://www.stylecore.com'
    ),
    cast=lambda v: [s.strip() for s in v.split(',')]
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_htmx',
    'rest_framework',
    'mehlr',
    'apps.tenant',
]
try:
    import erdeniz_security  # type: ignore[reportMissingImports]
    INSTALLED_APPS += [
        'erdeniz_security',
        'axes',
        'rest_framework_simplejwt',
        'rest_framework_simplejwt.token_blacklist',
        'corsheaders',
    ]
except ImportError:
    pass

MIDDLEWARE = [
    'apps.tenant.middleware.ErdenizSecurityMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'apps.tenant.middleware.TenantMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]
try:
    import whitenoise  # noqa
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
except ImportError:
    pass
try:
    import erdeniz_security  # type: ignore[reportMissingImports]
    MIDDLEWARE = (
        ['erdeniz_security.middleware.SecurityHeadersMiddleware'] +
        list(MIDDLEWARE) +
        ['erdeniz_security.middleware.RequestSanitizationMiddleware',
         'erdeniz_security.middleware.APIAuthenticationMiddleware',
         'erdeniz_security.middleware.APIRateLimitMiddleware',
         'erdeniz_security.middleware.AuditMiddleware',
         'axes.middleware.AxesMiddleware']
    )
except ImportError:
    pass

ROOT_URLCONF = 'config.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.tenant.context_processors.tenant_context',
            ],
            'loaders': [
                ('apps.tenant.loaders.TenantTemplateLoader', []),
                ('django.template.loaders.filesystem.Loader', [BASE_DIR / 'templates']),
                ('django.template.loaders.app_directories.Loader', []),
            ],
        },
    },
]
WSGI_APPLICATION = 'config.wsgi.application'

# VERITABANI — PostgreSQL (Production) veya SQLite (geliştirme)
try:
    import dj_database_url  # type: ignore[reportMissingImports]
    _db_url = config('DATABASE_URL', default='')
    if _db_url:
        DATABASES = {
            'default': dj_database_url.config(
                default=_db_url,
                conn_max_age=600,
                conn_health_checks=True,
            )
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
except ImportError:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'tr-tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'mehlr' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
try:
    import whitenoise  # noqa
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
except ImportError:
    pass
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# MEHLR Ayarları (Production: PRIMARY_MODEL, FALLBACK_MODEL, LOG_LEVEL)
MEHLR_CONFIG = {
    'ENGINE_VERSION': '1.0',
    'MAX_TOKENS': 4096,
    'TEMPERATURE': 0.7,
    'RATE_LIMIT_PER_MINUTE': config('MEHLR_RATE_LIMIT', default=15, cast=int),
    'CACHE_TTL': config('MEHLR_CACHE_TTL', default=300, cast=int),
    'MAX_CONVERSATION_HISTORY': config('MEHLR_MAX_CONVERSATION_HISTORY', default=20, cast=int),
    'PRIMARY_MODEL': config('MEHLR_PRIMARY_MODEL', default='gemini-2.5-flash'),
    'FALLBACK_MODEL': config('MEHLR_FALLBACK_MODEL', default='gemini-2.5-flash'),
    'LOG_LEVEL': config('MEHLR_LOG_LEVEL', default='INFO'),
}
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
INTER_SERVICE_API_KEY = config('INTER_SERVICE_API_KEY', default='')

# Dressifye — harici API (Adım 2: dressifye_client)
DRESSIFYE_API_URL = config('DRESSIFYE_API_URL', default='https://api.dressifye.com/v1')
DRESSIFYE_API_KEY = config('DRESSIFYE_API_KEY', default='your-secret-key')

# dressifye-saas köprüsü — Celery + Webhook (Adım 3)
GARMENT_CORE_WEBHOOK_URL = config('GARMENT_CORE_WEBHOOK_URL', default='')
GARMENT_CORE_WEBHOOK_SECRET = config('GARMENT_CORE_WEBHOOK_SECRET', default='')

# dressifye-saas okuma API'si — Mehlr AI bağlamı için (Adım 4)
# Boş bırakılırsa sistem Dressifye API'ye veya mock'a düşer.
GARMENT_CORE_API_URL = config('GARMENT_CORE_API_URL', default='')
GARMENT_CORE_API_KEY = config('GARMENT_CORE_API_KEY', default='')
# hangi tenant_slug'lar için dressifye-saas'u dene (virgülle, ör. dressifye,stylecoree)
GARMENT_CORE_TENANT_SLUGS = config(
    'GARMENT_CORE_TENANT_SLUGS',
    default='dressifye,stylecoree,hairinfinitye,styleforhuman',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)

# Celery — broker (Redis önerilir)
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'sync-active-users-hourly': {
        'task': 'mehlr.tasks.batch_sync_all_active_users',
        'schedule': crontab(minute=0),
    },
    'cleanup-old-data-nightly': {
        'task': 'mehlr.tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),
    },
}

# Django REST Framework — Dressifye API throttle
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'dressifye': config('DRESSIFYE_API_THROTTLE', default='120/minute'),
    },
}

# CACHE — Redis (Production) veya LocMem (geliştirme)
REDIS_URL = config('REDIS_URL', default='')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient', 'MAX_ENTRIES': 2000},
            'KEY_PREFIX': 'mehlr',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'OPTIONS': {'MAX_ENTRIES': 500},
        }
    }

# GÜVENLİK (sadece DEBUG=False iken)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'

# LOGGING
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'mehlr': {'format': '[{asctime}] [{levelname}] {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'mehlr'},
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'mehlr.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'mehlr',
        },
    },
    'loggers': {
        'mehlr': {
            'handlers': ['console', 'file'],
            'level': config('MEHLR_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}

LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/mehlr/'

# ErdenizTech güvenlik ayarları (opsiyonel — paket yoksa sessiz geç)
try:
    from erdeniz_security.api_security import ERDENIZ_JWT_SETTINGS  # type: ignore[reportMissingImports]
    SIMPLE_JWT = ERDENIZ_JWT_SETTINGS
    REQUEST_SIGNING_SECRET = config('REQUEST_SIGNING_SECRET', default='')
    INTER_SERVICE_SIGNING_SECRET = config('INTER_SERVICE_SIGNING_SECRET', default='')
    from erdeniz_security.network_guard import get_cors_settings  # type: ignore[reportMissingImports]
    _cors = get_cors_settings('mehlr')
    CORS_ALLOWED_ORIGINS = _cors['CORS_ALLOWED_ORIGINS']
    CORS_ALLOW_CREDENTIALS = _cors['CORS_ALLOW_CREDENTIALS']
    CORS_ALLOWED_METHODS = _cors['CORS_ALLOWED_METHODS']
    CORS_ALLOWED_HEADERS = _cors['CORS_ALLOWED_HEADERS']
    REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'rest_framework_simplejwt.authentication.JWTAuthentication',
            'rest_framework.authentication.SessionAuthentication',
        ],
        'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
        'DEFAULT_THROTTLE_CLASSES': [
            'rest_framework.throttling.AnonRateThrottle',
            'rest_framework.throttling.UserRateThrottle',
        ],
        'DEFAULT_THROTTLE_RATES': {'anon': '100/hour', 'user': '1000/hour'},
        'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
        'EXCEPTION_HANDLER': 'erdeniz_security.api_security.secure_exception_handler',
    }
except Exception:
    pass

# Ecosystem registry — tüm marka kökenlerini CORS'a ekle (erdeniz_security şemasından bağımsız)
try:
    from erdeniz_security.ecosystem_registry import iter_ecosystem_origins  # type: ignore

    _eco = list(iter_ecosystem_origins())
    if _eco and "CORS_ALLOWED_ORIGINS" in globals():
        CORS_ALLOWED_ORIGINS = list(dict.fromkeys([*CORS_ALLOWED_ORIGINS, *_eco]))  # type: ignore[name-defined]
except Exception:
    pass
