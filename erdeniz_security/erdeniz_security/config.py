"""
erdeniz_security/config.py — Merkezi güvenlik konfigürasyonu.
Tüm ErdenizTech projeleri bu ayarları kullanır. Hassas değerler env'den okunur.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

SECURITY_SETTINGS = {
    "KEY_ROTATION_DAYS": 90,
    "HASH_ALGORITHM": "argon2id",
    "MIN_PASSWORD_LENGTH": 12,
    "SESSION_TIMEOUT_MINUTES": 30,
    "MAX_LOGIN_ATTEMPTS": 5,
    "LOCKOUT_DURATION_MINUTES": 30,
    "AUDIT_LOG_ENABLED": True,
    "SECURE_HEADERS_ENABLED": True,
}


def _safe_config(key: str) -> Any:
    try:
        from decouple import config as decouple_config
        return decouple_config(key, default="")
    except Exception:
        return os.environ.get(key, "")


def get_security_settings(project_name: str | None = None) -> dict[str, Any]:
    """Proje adına göre güvenlik ayarları (varsayılan: MAX seviye)."""
    out = dict(SECURITY_SETTINGS)
    out["project_name"] = project_name or "default"
    return out


def validate_configuration() -> list[str]:
    """Eksik env ve güvensiz ayarları kontrol eder; AppConfig.ready'de çağrılabilir."""
    errors: list[str] = []
    for key in ("SECRET_KEY", "FIELD_ENCRYPTION_KEY", "ERDENIZ_ENCRYPTION_KEY"):
        if not (os.environ.get(key) or _safe_config(key)):
            errors.append(f"Ortam değişkeni eksik veya boş: {key}")
    try:
        from decouple import config as decouple_config
        settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
        is_test_or_dev = "tests.settings" in settings_module or os.environ.get("ERDENIZ_SECURITY_DEV") == "1"
        if not is_test_or_dev and decouple_config("DEBUG", default=True, cast=bool):
            errors.append("DEBUG=True production ortamında kapatılmalı.")
    except Exception:
        pass
    return errors


def get_django_security_settings() -> dict[str, Any]:
    """Django settings için güvenlik bloğu. FIELD_ENCRYPTION_KEY env'den."""
    field_key = os.environ.get("FIELD_ENCRYPTION_KEY", "")
    return {
        "PASSWORD_HASHERS": [
            "erdeniz_security.hashers.ErdenizArgon2Hasher",
            "erdeniz_security.hashers.ErdenizBcryptHasher",
            "django.contrib.auth.hashers.Argon2PasswordHasher",
            "django.contrib.auth.hashers.PBKDF2PasswordHasher",
            "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
        ],
        "LANGUAGE_CODE": "tr",
        "LANGUAGES": [("tr", "Türkçe"), ("en", "English")],
        "USE_I18N": True,
        "USE_L10N": True,
        "LOCALE_PATHS": [],  # Proje locale klasörü apps.py ready() ile eklenir
        "AUTHENTICATION_BACKENDS": [
            "axes.backends.AxesStandaloneBackend",
            "django.contrib.auth.backends.ModelBackend",
        ],
        "AUTH_PASSWORD_VALIDATORS": [
            {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
            {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
            {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
            {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
        ],
        "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_AGE": 1800,
        "SESSION_EXPIRE_AT_BROWSER_CLOSE": True,
        "SESSION_ENGINE": "django.contrib.sessions.backends.db",
        "CSRF_COOKIE_SECURE": True,
        "CSRF_COOKIE_HTTPONLY": True,
        "CSRF_COOKIE_SAMESITE": "Lax",
        "SECURE_SSL_REDIRECT": True,
        "SECURE_PROXY_SSL_HEADER": ("HTTP_X_FORWARDED_PROTO", "https"),
        "SECURE_HSTS_SECONDS": 31536000,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": True,
        "SECURE_HSTS_PRELOAD": True,
        "SECURE_BROWSER_XSS_FILTER": True,
        "SECURE_CONTENT_TYPE_NOSNIFF": True,
        "X_FRAME_OPTIONS": "DENY",
        "AXES_FAILURE_LIMIT": 5,
        "AXES_COOLOFF_TIME": 0.5,
        "AXES_LOCKOUT_CALLABLE": None,
        "AXES_RESET_ON_SUCCESS": True,
        "FIELD_ENCRYPTION_KEY": field_key,
    }


# Projeler: from erdeniz_security.config import get_django_security_settings
#          locals().update(get_django_security_settings())
# .env yüklendikten sonra çağrılırsa FIELD_ENCRYPTION_KEY doğru okunur.
DJANGO_SECURITY_SETTINGS = get_django_security_settings()


@dataclass
class ErdenizSecurityConfig:
    """Tip-güvenli güvenlik konfigürasyonu. settings.py'de kullanım için."""

    project_name: str = "default"
    encryption_key: str = field(default_factory=lambda: os.environ.get("ERDENIZ_ENCRYPTION_KEY", ""))
    field_encryption_key: str = field(default_factory=lambda: os.environ.get("FIELD_ENCRYPTION_KEY", ""))
    key_rotation_days: int = 90
    hash_algorithm: str = "argon2id"
    min_password_length: int = 12
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    audit_log_enabled: bool = True
    secure_headers_enabled: bool = True
    debug: bool = False
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 1
    rate_limit_anon: str = "100/hour"
    rate_limit_user: str = "1000/hour"
    rate_limit_api_key: str = "5000/hour"

    def validate(self) -> list[str]:
        """Konfigürasyonu doğrula. Hata listesi döndür."""
        errors: list[str] = []
        if not self.encryption_key:
            errors.append("encryption_key (ERDENIZ_ENCRYPTION_KEY) tanımlı olmalı")
        if not self.field_encryption_key:
            errors.append("field_encryption_key (FIELD_ENCRYPTION_KEY) tanımlı olmalı")
        if self.min_password_length < 8:
            errors.append("min_password_length en az 8 olmalı")
        if self.jwt_access_token_minutes > 60:
            errors.append("jwt_access_token_minutes production'da ≤60 önerilir")
        if self.debug:
            errors.append("debug=True production ortamında kapatılmalı")
        return errors

    @classmethod
    def from_env(cls, project_name: str = "default") -> "ErdenizSecurityConfig":
        """Ortam değişkenlerinden ErdenizSecurityConfig oluştur."""
        return cls(project_name=project_name)

    def to_django_settings(self) -> dict[str, Any]:
        """Django settings.py'ye uygulanabilecek dict üret."""
        from datetime import timedelta
        base = get_django_security_settings()
        base.update({
            "SESSION_COOKIE_AGE": self.session_timeout_minutes * 60,
            "AXES_FAILURE_LIMIT": self.max_login_attempts,
            "AXES_COOLOFF_TIME": self.lockout_duration_minutes / 60,
        })
        if "SIMPLE_JWT" not in base:
            base["SIMPLE_JWT"] = {}
        base["SIMPLE_JWT"].update({
            "ACCESS_TOKEN_LIFETIME": timedelta(minutes=self.jwt_access_token_minutes),
            "REFRESH_TOKEN_LIFETIME": timedelta(days=self.jwt_refresh_token_days),
        })
        return base
