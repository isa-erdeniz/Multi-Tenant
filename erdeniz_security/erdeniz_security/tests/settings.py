# Minimal Django settings for erdeniz_security tests
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SECRET_KEY = "test-secret-key-for-erdeniz-security-tests"
DEBUG = True
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "erdeniz_security",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
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
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", os.path.join(BASE_DIR, "db.sqlite3")),
    }
}
USE_TZ = True
AUTH_USER_MODEL = "auth.User"
ROOT_URLCONF = "erdeniz_security.tests.urls"

# Türkçe dil desteği
LANGUAGE_CODE = "tr"
LANGUAGES = [("tr", "Türkçe"), ("en", "English")]
USE_I18N = True
USE_L10N = True
LOCALE_PATHS = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locale")]

# Static files (required by django.contrib.staticfiles)
STATIC_URL = "/static/"
STATIC_ROOT = os.environ.get("STATIC_ROOT", "static")

# Dummy keys so encrypted_model_fields and erdeniz_security load (e.g. generate_test_env)
_DUMMY_FERNET = "QqZVHkSvAndpwD5XZC7xv9dAwqQZzeqcXPLDrBVCym4="
os.environ.setdefault("FIELD_ENCRYPTION_KEY", _DUMMY_FERNET)
os.environ.setdefault("ERDENIZ_ENCRYPTION_KEY", _DUMMY_FERNET)
FIELD_ENCRYPTION_KEY = os.environ["FIELD_ENCRYPTION_KEY"]
ERDENIZ_ENCRYPTION_KEY = os.environ.get("ERDENIZ_ENCRYPTION_KEY", "")
