"""
erdeniz_security/api_security.py — API güvenlik katmanı.
JWT, API key, request signing, rate limit konfigürasyonu. Ayrı modül/klasör yok.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from datetime import timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ─── JWT ─────────────────────────────────────────────────────────────────────

ERDENIZ_JWT_SETTINGS = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "TOKEN_OBTAIN_SERIALIZER": "erdeniz_security.api_security.ErdenizTokenObtainSerializer",
}


def _get_erdeniz_token_serializer():
    try:
        from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
        return TokenObtainPairSerializer
    except ImportError:
        return None


try:
    from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as _Base

    class ErdenizTokenObtainSerializer(_Base):
        """Token obtain + audit (IP, User-Agent, success/fail)."""

        def validate(self, attrs: dict) -> dict:
            request = self.context.get("request")
            ip = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "") if request else ""
            ua = request.META.get("HTTP_USER_AGENT", "") if request else ""
            try:
                data = super().validate(attrs)
                try:
                    from .audit import log_event
                    log_event("API_AUTH_SUCCESS", (request.path[:255] if request else "token"), getattr(request, "_erdeniz_project", "api"), request=request, success=True, details={"ip": ip, "user_agent": ua[:200]})
                except Exception as e:
                    logger.debug("Audit: %s", e)
                return data
            except Exception as e:
                try:
                    from .audit import log_event
                    log_event("API_AUTH_FAIL", (request.path[:255] if request else "token"), getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"ip": ip, "reason": str(e)[:200]})
                except Exception:
                    pass
                raise
except ImportError:
    ErdenizTokenObtainSerializer = None  # type: ignore[misc, assignment]

# ─── API Key ─────────────────────────────────────────────────────────────────

def _hash_api_key(key: str) -> str:
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        return ph.hash(key)
    except ImportError:
        return hashlib.sha256(key.encode()).hexdigest()


def _verify_api_key_hash(plain: str, hashed: str) -> bool:
    try:
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError
        ph = PasswordHasher()
        ph.verify(hashed, plain)
        return True
    except (ImportError, VerifyMismatchError):
        return hashlib.sha256(plain.encode()).hexdigest() == hashed


class ErdenizAPIKeyManager:
    """Proje bazlı API key yönetimi. Key düz metin saklanmaz."""

    PREFIX = "erd_"
    PREFIX_LEN = 8

    def create_api_key(
        self,
        project_name: str,
        permissions: list[str],
        expires_in_days: int = 90,
        created_by: Any = None,
    ) -> tuple[str, str]:
        """API key üret. Dönen full_key sadece bir kez gösterilir."""
        from django.utils import timezone
        raw = secrets.token_urlsafe(32)
        prefix = (self.PREFIX + raw[:4]).lower()[: self.PREFIX_LEN]
        full_key = f"{prefix}_{raw}"
        hashed = _hash_api_key(full_key)
        from .models import ErdenizAPIKey
        expires_at = timezone.now() + timedelta(days=expires_in_days)
        ErdenizAPIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            project=project_name,
            permissions=permissions,
            expires_at=expires_at,
            created_by=created_by,
        )
        try:
            from .audit import log_event
            log_event("API_KEY_CREATE", project_name, project_name, user=created_by, details={"prefix": prefix, "permissions": permissions})
        except Exception:
            pass
        return prefix, full_key

    def validate_api_key(self, key: str) -> dict | None:
        """API key doğrula. Return: {project, permissions, created_at, expires_at, is_valid} veya None."""
        from django.utils import timezone
        from .models import ErdenizAPIKey
        if not key or "_" not in key:
            return None
        prefix = key.split("_", 2)[0] + "_" + key.split("_", 2)[1] if key.count("_") >= 2 else key[: self.PREFIX_LEN]
        try:
            obj = ErdenizAPIKey.objects.get(prefix=prefix, is_active=True)
        except ErdenizAPIKey.DoesNotExist:
            try:
                from .audit import log_event
                log_event("API_AUTH_FAIL", "api_key", "api", success=False, details={"reason": "invalid_prefix"})
            except Exception:
                pass
            return None
        if not _verify_api_key_hash(key, obj.hashed_key):
            try:
                from .audit import log_event
                log_event("API_AUTH_FAIL", "api_key", obj.project, success=False, details={"reason": "invalid_key"})
            except Exception:
                pass
            return None
        if obj.expires_at and timezone.now() > obj.expires_at:
            try:
                from .audit import log_event
                log_event("API_AUTH_FAIL", "api_key", obj.project, success=False, details={"reason": "expired"})
            except Exception:
                pass
            return None
        obj.usage_count += 1
        obj.last_used_at = timezone.now()
        obj.save(update_fields=["usage_count", "last_used_at"])
        try:
            from .audit import log_event
            log_event("API_AUTH_SUCCESS", "api_key", obj.project, details={"prefix": prefix})
        except Exception:
            pass
        return {
            "project": obj.project,
            "permissions": obj.permissions or [],
            "created_at": obj.created_at,
            "expires_at": obj.expires_at,
            "is_valid": True,
        }

    def revoke_api_key(self, key_prefix: str) -> bool:
        from .models import ErdenizAPIKey
        updated = ErdenizAPIKey.objects.filter(prefix=key_prefix).update(is_active=False)
        if updated:
            try:
                from .audit import log_event
                log_event("API_KEY_REVOKE", key_prefix, "api", details={"prefix": key_prefix})
            except Exception:
                pass
        return updated > 0

    def rotate_api_key(self, key_prefix: str, created_by: Any = None) -> tuple[str, str] | None:
        from django.utils import timezone
        from .models import ErdenizAPIKey
        try:
            old = ErdenizAPIKey.objects.get(prefix=key_prefix, is_active=True)
        except ErdenizAPIKey.DoesNotExist:
            return None
        old.is_active = False
        old.save(update_fields=["is_active"])
        prefix, full_key = self.create_api_key(old.project, old.permissions, 90, created_by)
        try:
            from .audit import log_event
            log_event("API_KEY_ROTATE", old.project, old.project, details={"old_prefix": key_prefix, "new_prefix": prefix})
        except Exception:
            pass
        return prefix, full_key

    def list_api_keys(self, project_name: str | None = None) -> list[dict]:
        from .models import ErdenizAPIKey
        qs = ErdenizAPIKey.objects.filter(is_active=True).order_by("-created_at")
        if project_name:
            qs = qs.filter(project=project_name)
        return [
            {"prefix": o.prefix, "project": o.project, "permissions": o.permissions, "created_at": o.created_at, "expires_at": o.expires_at, "usage_count": o.usage_count}
            for o in qs
        ]


# ─── Request Signing (HMAC-SHA256) ───────────────────────────────────────────

class RequestSigner:
    """Projeler arası API isteklerini imzala ve doğrula."""

    def __init__(self, secret: str | bytes) -> None:
        self._secret = secret.encode() if isinstance(secret, str) else secret

    def sign_request(
        self,
        method: str,
        url: str,
        body: str | bytes,
        timestamp: float | None = None,
    ) -> dict[str, str]:
        timestamp = timestamp or time.time()
        nonce = secrets.token_urlsafe(16)
        body_b = body.encode() if isinstance(body, str) else body
        body_hash = hashlib.sha256(body_b).hexdigest()
        message = f"{method.upper()}\n{url}\n{timestamp}\n{nonce}\n{body_hash}"
        sig = hmac.new(self._secret, message.encode(), hashlib.sha256).hexdigest()
        return {
            "X-Erdeniz-Timestamp": str(int(timestamp)),
            "X-Erdeniz-Nonce": nonce,
            "X-Erdeniz-Signature": sig,
        }

    def verify_request(self, request: Any) -> bool:
        """Gelen isteğin imzasını doğrula (timestamp ±5 dk, nonce tek kullanım)."""
        ts_h = request.META.get("HTTP_X_ERDENIZ_TIMESTAMP") or request.headers.get("X-Erdeniz-Timestamp")
        nonce_h = request.META.get("HTTP_X_ERDENIZ_NONCE") or request.headers.get("X-Erdeniz-Nonce")
        sig_h = request.META.get("HTTP_X_ERDENIZ_SIGNATURE") or request.headers.get("X-Erdeniz-Signature")
        if not all((ts_h, nonce_h, sig_h)):
            return False
        try:
            ts = int(ts_h)
        except ValueError:
            return False
        if abs(time.time() - ts) > 300:
            return False
        body = getattr(request, "body", b"") or b""
        if hasattr(body, "decode"):
            body = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
        body_hash = hashlib.sha256(body.encode() if isinstance(body, str) else body).hexdigest()
        url = request.build_absolute_uri() if hasattr(request, "build_absolute_uri") else request.get_full_path() if hasattr(request, "get_full_path") else ""
        method = getattr(request, "method", "GET") or "GET"
        message = f"{method.upper()}\n{url}\n{ts_h}\n{nonce_h}\n{body_hash}"
        expected = hmac.new(self._secret, message.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig_h)


# ─── Rate limits ─────────────────────────────────────────────────────────────

ERDENIZ_RATE_LIMITS = {
    "default": {"anon": "100/hour", "user": "1000/hour", "api_key": "5000/hour"},
    "auth": {"login": "5/minute", "register": "3/minute", "password_reset": "3/hour"},
    "sensitive": {"export": "10/hour", "bulk_update": "5/hour", "decrypt": "50/hour"},
}


# ─── DRF exception handler ────────────────────────────────────────────────────

def secure_exception_handler(exc: Exception, context: dict) -> Any | None:
    """DRF exception handler; hassas bilgi sızdırmadan yanıt."""
    try:
        from rest_framework.views import exception_handler
        response = exception_handler(exc, context)
        if response is not None:
            request = context.get("request")
            try:
                from .audit import log_event
                log_event(
                    "SECURITY_ALERT" if response.status_code >= 500 else "API_AUTH_FAIL",
                    (request.path[:255] if request else "api"),
                    getattr(request, "_erdeniz_project", "api"),
                    request=request,
                    success=False,
                    details={"status": response.status_code},
                )
            except Exception:
                pass
        return response
    except Exception:
        return None
