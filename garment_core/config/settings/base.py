"""
Garment Core — Temel Django ayarları.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import environ
from datetime import timedelta

from celery.schedules import crontab


def _normalize_iyzico_base_url_for_sdk(raw: str) -> str:
    """
    iyzipay, base_url'yi doğrudan http.client.HTTPSConnection(host) olarak kullanır;
    tam URL (https://...) veya şemasız //host bu yüzden 'nonnumeric port' hatasına düşer.
    Ortam değişkeni tam URL veya sadece host olabilir; çıktı her zaman host[:port] biçimindedir.
    """
    default = "sandbox-api.iyzipay.com"
    if not raw or not str(raw).strip():
        return default
    s = str(raw).strip()
    if s.startswith("//"):
        s = "https:" + s
    elif not s.startswith("http"):
        s = "https://" + s.lstrip("/")
    parsed = urlparse(s)
    host = parsed.hostname
    if not host:
        return default
    if parsed.port:
        return f"{host}:{parsed.port}"
    return host

env = environ.Env(
    DEBUG=(bool, False),
    MEHLR_ENABLED=(bool, False),
    USE_S3=(bool, False),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Ecosystem intake (marka hatları → merkez)
INTAKE_BEARER_TOKEN = env("INTAKE_BEARER_TOKEN", default="")
ECOSYSTEM_REGISTRY_PATH = env("ECOSYSTEM_REGISTRY_PATH", default="")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "rest_framework",
    "apps.core",
    "apps.legal",
    "apps.tenants",
    "apps.accounts",
    "apps.profiles",
    "apps.wardrobe",
    "apps.styling",
    "apps.tryon",
    "apps.editor",
    "apps.beauty",
    "apps.hair",
    "apps.avatar",
    "apps.looks",
    "apps.catalog",
    "apps.analytics",
    "apps.api",
    "apps.social",
    "apps.subscriptions",
    "apps.payments",
    "apps.ai_integrations",
    "apps.intake",
    "django_celery_beat",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
]

# erdeniz_security - opsiyonel (PyPI'de yoksa atla)
try:
    import erdeniz_security  # noqa: F401
    INSTALLED_APPS.insert(0, "erdeniz_security")
except ImportError:
    pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.tenants.middleware.TenantContextMiddleware",
    "apps.subscriptions.middleware.SubscriptionCheckMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.core.middleware.TrialMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

LOGIN_URL = "/hesap/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

AUTH_USER_MODEL = "accounts.DressifyeUser"
AUTHENTICATION_BACKENDS = [
    "allauth.account.auth_backends.AuthenticationBackend",
]

# django.contrib.sites (allauth için gerekli)
SITE_ID = 1

# django-allauth
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="optional")
ACCOUNT_SIGNUP_REDIRECT_URL = "/profil/onboarding/adim/1/"
LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"
ACCOUNT_FORMS = {"signup": "apps.accounts.forms.AllauthSignupForm"}  # Trial + username=email

# Redis (Celery + Cache) — REDIS_URL varsa Redis, yoksa LocMem
_redis_url = env("REDIS_URL", default="")
if _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_url,
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# CORS (production'da Cloudflare/DNS arkasında)
try:
    import corsheaders  # noqa: F401
    INSTALLED_APPS.insert(0, "corsheaders")
    MIDDLEWARE.insert(1, "corsheaders.middleware.CorsMiddleware")
    CORS_ALLOWED_ORIGINS = env.list(
        "CORS_ALLOWED_ORIGINS",
        default=[
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:8787",
            "http://127.0.0.1:8787",
            "https://dressifye.com",
            "https://www.dressifye.com",
        ],
    )
    try:
        from erdeniz_security.ecosystem_registry import iter_ecosystem_origins  # type: ignore

        _extra = list(iter_ecosystem_origins())
        CORS_ALLOWED_ORIGINS = list(
            dict.fromkeys([*CORS_ALLOWED_ORIGINS, *_extra])
        )
    except Exception:
        pass
except ImportError:
    pass

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
                "apps.core.context_processors.subscription_context",
            ],
        },
    },
]

# Database - development/production override
if env("DATABASE_URL", default=""):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# FAZ 20: Çoklu dil (tr, en, ar)
LANGUAGES = [
    ("tr", "Türkçe"),
    ("en", "English"),
    ("ar", "العربية"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# storages - S3 kullanılacaksa ekle
try:
    import storages  # noqa: F401
    INSTALLED_APPS.append("storages")
except ImportError:
    pass

USE_S3 = env.bool("USE_S3", default=False)

if USE_S3:
    # AWS S3 Ayarları
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="garment-core-media")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-central-1")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"

    # Media ve Static ayrı prefix'lerle (storage_backends.py)
    DEFAULT_FILE_STORAGE = "config.storage_backends.MediaS3Storage"
    STATICFILES_STORAGE = "config.storage_backends.StaticS3Storage"

    # URL Yapılandırması
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    MEDIA_ROOT = ""

    # S3 Güvenlik ve Önbellek Ayarları
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_QUERYSTRING_AUTH = False  # Resim linklerinin herkes tarafından görülebilmesi için

    # Ek S3 ayarları — public-read ile yüklenen dosyalar herkese açık
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_VERIFY = True
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# iyzico (SDK hostname bekler; env tam URL olabilir)
IYZICO_API_KEY = env("IYZICO_API_KEY", default="")
IYZICO_SECRET_KEY = env("IYZICO_SECRET_KEY", default="")
IYZICO_BASE_URL = _normalize_iyzico_base_url_for_sdk(
    env("IYZICO_BASE_URL", default="https://sandbox-api.iyzipay.com")
)
# Ödeme tutarı bu para biriminde gönderilir (örn. USD ile $5/$10 plan fiyatları)
IYZICO_CURRENCY = env("IYZICO_CURRENCY", default="USD")
# Webhook X-Iyz-Signature-V3 (Merchant panel → Merchant ID)
IYZICO_MERCHANT_ID = env.str("IYZICO_MERCHANT_ID", default="")
# True: imza zorunlu (canlı önerilir). False: doğrulama atlanır (yalnızca geliştirme).
IYZICO_WEBHOOK_VERIFY_SIGNATURE = env.bool("IYZICO_WEBHOOK_VERIFY_SIGNATURE", default=True)
# True: imza başlığı yoksa yine kabul (sandbox / geçiş). Canlıda False tutun.
IYZICO_WEBHOOK_ALLOW_UNSIGNED = env.bool(
    "IYZICO_WEBHOOK_ALLOW_UNSIGNED",
    default=DEBUG,
)

# Dressifye → iyzico Subscription Checkout (pricing plan ref’ler panelden)
# iyzico Subscription: aylık / yıllık pricing plan reference code (panelden)
IYZICO_PP_STARTER_MONTHLY = env.str("IYZICO_PP_STARTER_MONTHLY", default="")
IYZICO_PP_STARTER_YEARLY = env.str("IYZICO_PP_STARTER_YEARLY", default="")
IYZICO_PP_ELITE_MONTHLY = env.str("IYZICO_PP_ELITE_MONTHLY", default="")
IYZICO_PP_ELITE_YEARLY = env.str("IYZICO_PP_ELITE_YEARLY", default="")
IYZICO_PP_PLATINUM_MONTHLY = env.str("IYZICO_PP_PLATINUM_MONTHLY", default="")
IYZICO_PP_PLATINUM_YEARLY = env.str("IYZICO_PP_PLATINUM_YEARLY", default="")
IYZICO_PP_DIAMOND_MONTHLY = env.str("IYZICO_PP_DIAMOND_MONTHLY", default="")
IYZICO_PP_DIAMOND_YEARLY = env.str("IYZICO_PP_DIAMOND_YEARLY", default="")
# Geriye dönük (tek kod / tier): yeni IYZICO_PP_* boşsa get_iyzico_plan_code bunlara düşer
IYZICO_SUBSCRIPTION_PP_ELITE = env.str("IYZICO_SUBSCRIPTION_PP_ELITE", default="")
IYZICO_SUBSCRIPTION_PP_PLATINUM = env.str("IYZICO_SUBSCRIPTION_PP_PLATINUM", default="")
IYZICO_SUBSCRIPTION_PP_DIAMOND = env.str("IYZICO_SUBSCRIPTION_PP_DIAMOND", default="")
DRESSIFYE_PLAN_SLUG_STARTER = env.str("DRESSIFYE_PLAN_SLUG_STARTER", default="ucretsiz")
DRESSIFYE_PLAN_SLUG_ELITE = env.str("DRESSIFYE_PLAN_SLUG_ELITE", default="stil-plus")
DRESSIFYE_PLAN_SLUG_PLATINUM = env.str("DRESSIFYE_PLAN_SLUG_PLATINUM", default="stil-pro")
DRESSIFYE_PLAN_SLUG_DIAMOND = env.str("DRESSIFYE_PLAN_SLUG_DIAMOND", default="stil-pro")
# iyzico callback (Dressifye Worker POST proxy); örn. https://dressifye.com/odeme/abonelik-callback/
DRESSIFYE_SUBSCRIPTION_CALLBACK_URL = env.str(
    "DRESSIFYE_SUBSCRIPTION_CALLBACK_URL",
    default="https://dressifye.com/odeme/abonelik-callback/",
)

# Remove.bg (arka plan silme)
REMOVE_BG_API_KEY = env.str("REMOVE_BG_API_KEY", default="")

# OpenWeatherMap (hava durumu)
OPENWEATHER_API_KEY = env.str("OPENWEATHER_API_KEY", default="")

# MEHLR AI
MEHLR_ENABLED = env.bool("MEHLR_ENABLED", default=False)
MEHLR_URL = env.str("MEHLR_URL", default="")
MEHLR_API_KEY = env.str("MEHLR_API_KEY", default="")
MEHLR_PROJECT = env.str("MEHLR_PROJECT", default="garment_core")

# packages/garment_core TypeScript API
GARMENT_CORE_TS_ENABLED = env.bool("GARMENT_CORE_TS_ENABLED", default=False)
GARMENT_CORE_TS_URL = env.str("GARMENT_CORE_TS_URL", default="")
GARMENT_CORE_WEBHOOK_SECRET = env.str("GARMENT_CORE_WEBHOOK_SECRET", default="")
GARMENT_CORE_TS_API_KEY = env.str("GARMENT_CORE_TS_API_KEY", default="")

# django-cryptography: isteğe bağlı anahtar (boşsa SECRET_KEY türetilir)
CRYPTOGRAPHY_KEY = env.str("CRYPTOGRAPHY_KEY", default="")

# Harici AI sağlayıcıları (WearView / Zmo / Style3D)
WEARVIEW_API_KEY = env.str("WEARVIEW_API_KEY", default="")
WEARVIEW_BASE_URL = env.str("WEARVIEW_BASE_URL", default="https://api.wearview.com/v1")
WEARVIEW_WEBHOOK_SECRET = env.str("WEARVIEW_WEBHOOK_SECRET", default="")
ZMO_API_KEY = env.str("ZMO_API_KEY", default="")
ZMO_BASE_URL = env.str("ZMO_BASE_URL", default="https://api.zmo.ai/v1")
ZMO_WEBHOOK_SECRET = env.str("ZMO_WEBHOOK_SECRET", default="")
STYLE3D_API_KEY = env.str("STYLE3D_API_KEY", default="")
STYLE3D_BASE_URL = env.str("STYLE3D_BASE_URL", default="https://api.style3d.com/v1")
STYLE3D_WEBHOOK_SECRET = env.str("STYLE3D_WEBHOOK_SECRET", default="")
# True: webhook imzası yokken (yalnız DEBUG ile birlikte) kabul. Canlıda False.
AI_WEBHOOK_ALLOW_UNSIGNED = env.bool("AI_WEBHOOK_ALLOW_UNSIGNED", default=DEBUG)

# Celery 
CELERY_BROKER_URL = env("REDIS_URL", default="memory://")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="cache+memory://")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    "check-expired-subscriptions": {
        "task": "apps.subscriptions.tasks.check_expired_subscriptions",
        "schedule": crontab(hour=3, minute=0),
    },
    "reset-monthly-usage": {
        "task": "apps.subscriptions.tasks.reset_monthly_usage",
        "schedule": crontab(hour=3, minute=30),
    },
    "ai-check-pending-tasks": {
        "task": "apps.ai_integrations.tasks.check_pending_tasks",
        "schedule": crontab(minute="*/2"),
    },
    "ai-reset-monthly-credits": {
        "task": "apps.ai_integrations.tasks.reset_monthly_credits",
        "schedule": crontab(hour=4, minute=0),
    },
    "ai-cleanup-old-tasks": {
        "task": "apps.ai_integrations.tasks.cleanup_old_tasks",
        "schedule": crontab(hour=2, minute=15),
    },
}

if "test" in sys.argv:
    CELERY_TASK_ALWAYS_EAGER = True

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}
