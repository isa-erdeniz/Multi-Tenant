"""
Garment Core — Geliştirme ortamı ayarları.
"""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "127.0.0.1:8000"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Debug toolbar (development.txt'te yüklü)
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# Güvenlik uyarılarını geliştirmede sustur
SILENCED_SYSTEM_CHECKS = [
    "security.W004",
    "security.W008",
    "security.W012",
    "security.W016",
    "security.W018",
]
