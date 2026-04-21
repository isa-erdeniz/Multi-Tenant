"""
erdeniz_security/network_guard.py — Ağ güvenlik katmanı.
CORS, webhook doğrulama, SSL yardımcıları, IP kontrolleri. Ayrı modül/klasör yok.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import ssl
import socket
from typing import Any

logger = logging.getLogger(__name__)

# ─── CORS ───────────────────────────────────────────────────────────────────

ERDENIZ_CORS_SETTINGS: dict[str, dict[str, Any]] = {
    "looopone": {
        "CORS_ALLOWED_ORIGINS": [
            "https://looopone.erdeniztech.com",
            "https://admin.looopone.erdeniztech.com",
        ],
        "CORS_ALLOW_CREDENTIALS": True,
        "CORS_ALLOWED_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "CORS_ALLOWED_HEADERS": [
            "authorization", "content-type", "x-erdeniz-timestamp",
            "x-erdeniz-nonce", "x-erdeniz-signature", "x-api-key",
        ],
    },
    "worktrackere": {
        "CORS_ALLOWED_ORIGINS": [
            "https://worktrackere.erdeniztech.com",
            "https://admin.worktrackere.erdeniztech.com",
        ],
        "CORS_ALLOW_CREDENTIALS": True,
        "CORS_ALLOWED_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "CORS_ALLOWED_HEADERS": [
            "authorization", "content-type", "x-erdeniz-timestamp",
            "x-erdeniz-nonce", "x-erdeniz-signature", "x-api-key",
        ],
    },
    "garment_core": {
        "CORS_ALLOWED_ORIGINS": [
            "https://garment-core.erdeniztech.com",
            "https://try-on.erdeniztech.com",
        ],
        "CORS_ALLOW_CREDENTIALS": True,
        "CORS_ALLOWED_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "CORS_ALLOWED_HEADERS": [
            "authorization", "content-type", "x-erdeniz-timestamp",
            "x-erdeniz-nonce", "x-erdeniz-signature", "x-api-key",
        ],
    },
    "hairinfinitye": {
        "CORS_ALLOWED_ORIGINS": [
            "https://hairinfinitye.erdeniztech.com",
            "https://admin.hairinfinitye.erdeniztech.com",
        ],
        "CORS_ALLOW_CREDENTIALS": True,
        "CORS_ALLOWED_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "CORS_ALLOWED_HEADERS": [
            "authorization", "content-type", "x-erdeniz-timestamp",
            "x-erdeniz-nonce", "x-erdeniz-signature", "x-api-key",
        ],
    },
    "edulingoe": {
        "CORS_ALLOWED_ORIGINS": [
            "https://edulingoe.erdeniztech.com",
            "https://admin.edulingoe.erdeniztech.com",
        ],
        "CORS_ALLOW_CREDENTIALS": True,
        "CORS_ALLOWED_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "CORS_ALLOWED_HEADERS": [
            "authorization", "content-type", "x-erdeniz-timestamp",
            "x-erdeniz-nonce", "x-erdeniz-signature", "x-api-key",
        ],
    },
    "stylecoree": {
        "CORS_ALLOWED_ORIGINS": [
            "https://stylecoree.erdeniztech.com",
            "https://admin.stylecoree.erdeniztech.com",
        ],
        "CORS_ALLOW_CREDENTIALS": True,
        "CORS_ALLOWED_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "CORS_ALLOWED_HEADERS": [
            "authorization", "content-type", "x-erdeniz-timestamp",
            "x-erdeniz-nonce", "x-erdeniz-signature", "x-api-key",
        ],
    },
    "drivetrackere": {
        "CORS_ALLOWED_ORIGINS": [
            "https://drivetrackere.erdeniztech.com",
            "https://admin.drivetrackere.erdeniztech.com",
        ],
        "CORS_ALLOW_CREDENTIALS": True,
        "CORS_ALLOWED_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "CORS_ALLOWED_HEADERS": [
            "authorization", "content-type", "x-erdeniz-timestamp",
            "x-erdeniz-nonce", "x-erdeniz-signature", "x-api-key",
        ],
    },
    "dressifye": {
        "CORS_ALLOWED_ORIGINS": [
            "https://dressifye.com",
            "https://www.dressifye.com",
            "https://api.dressifye.com",
        ],
        "CORS_ALLOW_CREDENTIALS": True,
        "CORS_ALLOWED_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "CORS_ALLOWED_HEADERS": [
            "authorization", "content-type", "x-erdeniz-timestamp",
            "x-erdeniz-nonce", "x-erdeniz-signature", "x-api-key",
        ],
    },
    "mehlr": {
        "CORS_ALLOWED_ORIGINS": [
            "https://erdeniztech.com",
            "https://www.erdeniztech.com",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://looopone.erdeniztech.com",
            "https://admin.looopone.erdeniztech.com",
            "https://worktrackere.erdeniztech.com",
            "https://garment-core.erdeniztech.com",
            "https://hairinfinitye.erdeniztech.com",
            "https://edulingoe.erdeniztech.com",
            "https://stylecoree.erdeniztech.com",
            "https://drivetrackere.erdeniztech.com",
            "https://dressifye.com",
            "https://www.dressifye.com",
            "https://api.dressifye.com",
            "https://mehlr.erdeniztech.com",
        ],
        "CORS_ALLOW_CREDENTIALS": True,
        "CORS_ALLOWED_METHODS": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "CORS_ALLOWED_HEADERS": [
            "authorization", "content-type", "x-erdeniz-timestamp",
            "x-erdeniz-nonce", "x-erdeniz-signature", "x-api-key",
        ],
    },
}


def get_cors_settings(project_name: str) -> dict[str, Any]:
    """Proje bazlı CORS ayarlarını döndür."""
    key = project_name.lower().replace("-", "_").replace(" ", "_")
    return ERDENIZ_CORS_SETTINGS.get(key, ERDENIZ_CORS_SETTINGS["looopone"]).copy()


# ─── Webhook ─────────────────────────────────────────────────────────────────

class WebhookVerifier:
    """Dış servislerden gelen webhook imzası doğrulama."""

    def verify_webhook(
        self,
        request: Any,
        secret: str,
        max_age_seconds: int = 300,
        header_name: str = "X-Webhook-Signature",
        timestamp_header: str = "X-Webhook-Timestamp",
    ) -> bool:
        sig = request.META.get(f"HTTP_{header_name.upper().replace('-', '_')}") or getattr(request, "headers", {}).get(header_name)
        ts_h = request.META.get(f"HTTP_{timestamp_header.upper().replace('-', '_')}") or getattr(request, "headers", {}).get(timestamp_header)
        if not sig or not ts_h:
            try:
                from .audit import log_event
                log_event("WEBHOOK_REJECTED", request.path[:255] if getattr(request, "path", None) else "webhook", getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"reason": "missing_headers"})
            except Exception:
                pass
            return False
        try:
            ts = int(ts_h)
        except ValueError:
            return False
        import time
        if abs(time.time() - ts) > max_age_seconds:
            try:
                from .audit import log_event
                log_event("WEBHOOK_REJECTED", request.path[:255] if getattr(request, "path", None) else "webhook", getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"reason": "expired_timestamp"})
            except Exception:
                pass
            return False
        body = getattr(request, "body", b"") or b""
        if hasattr(body, "decode") and isinstance(body, bytes):
            payload = body
        else:
            payload = body.encode("utf-8") if isinstance(body, str) else body
        body_str = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else str(payload)
        message = f"{ts_h}.{body_str}"
        expected = hmac.new(secret.encode() if isinstance(secret, str) else secret, message.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            try:
                from .audit import log_event
                log_event("WEBHOOK_REJECTED", request.path[:255] if getattr(request, "path", None) else "webhook", getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"reason": "invalid_signature"})
            except Exception:
                pass
            return False
        try:
            from .audit import log_event
            log_event("WEBHOOK_VERIFIED", request.path[:255] if getattr(request, "path", None) else "webhook", getattr(request, "_erdeniz_project", "api"), request=request, success=True)
        except Exception:
            pass
        return True

    def create_webhook_secret(self, service_name: str) -> str:
        """Yeni webhook secret üret."""
        return secrets.token_urlsafe(32)

    def verify_payment_webhook(self, request: Any, provider: str) -> bool:
        """Ödeme servisi webhook. provider: iyzico, stripe, paytr."""
        try:
            secret = __import__("os").environ.get(f"WEBHOOK_{provider.upper()}_SECRET", "") or __import__("decouple", fromlist=["config"]).config(f"WEBHOOK_{provider.upper()}_SECRET", default="")
        except Exception:
            secret = ""
        if not secret:
            logger.warning("Webhook secret tanımlı değil: %s", provider)
            return False
        if provider.lower() == "stripe":
            sig = request.META.get("HTTP_STRIPE_SIGNATURE") or getattr(request, "headers", {}).get("Stripe-Signature")
            if not sig:
                return False
            try:
                import stripe
                payload = request.body
                stripe.Webhook.construct_event(payload, sig, secret)
                try:
                    from .audit import log_event
                    log_event("WEBHOOK_VERIFIED", request.path[:255], getattr(request, "_erdeniz_project", "api"), request=request, success=True, details={"provider": "stripe"})
                except Exception:
                    pass
                return True
            except Exception as e:
                logger.debug("Stripe webhook: %s", e)
                try:
                    from .audit import log_event
                    log_event("WEBHOOK_REJECTED", request.path[:255], getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"provider": "stripe", "reason": str(e)[:200]})
                except Exception:
                    pass
                return False
        return self.verify_webhook(request, secret, max_age_seconds=300)


# ─── SSL ────────────────────────────────────────────────────────────────────

class SSLHelper:
    """SSL/TLS sertifika durumu ve konfig yardımcıları."""

    def check_ssl_status(self, domain: str, port: int = 443) -> dict[str, Any]:
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, port), timeout=5):
                with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
                    cert = s.getpeercert()
                    from datetime import datetime
                    not_after = cert.get("notAfter", "")
                    expires_at = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z") if not_after else None
                    days = (expires_at - datetime.utcnow()).days if expires_at else None
                    return {
                        "valid": True,
                        "issuer": dict(x[0] for x in cert.get("issuer", [])),
                        "expires_at": not_after,
                        "days_remaining": days,
                        "grade": "A" if days and days > 30 else "B" if days and days > 0 else "F",
                    }
        except Exception as e:
            return {"valid": False, "issuer": {}, "expires_at": None, "days_remaining": None, "grade": "F", "error": str(e)}

    def get_ssl_config_nginx(self, domain: str) -> str:
        return f"""
server {{
    listen 443 ssl http2;
    server_name {domain};
    ssl_certificate     /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
}}
"""

    def get_ssl_config_gunicorn(self) -> dict[str, str]:
        return {
            "keyfile": "/etc/letsencrypt/live/KEYPATH/privkey.pem",
            "certfile": "/etc/letsencrypt/live/KEYPATH/fullchain.pem",
        }


# ─── IP ─────────────────────────────────────────────────────────────────────

class IPGuard:
    """IP bazlı güvenlik kontrolleri."""

    def is_ip_allowed(self, ip: str, whitelist: list[str]) -> bool:
        if not whitelist:
            return True
        return ip in whitelist or ip.strip() in [w.strip() for w in whitelist]

    def get_client_ip(self, request: Any, trusted_proxies: list[str] | None = None) -> str:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded and trusted_proxies:
            parts = [p.strip() for p in forwarded.split(",")]
            for p in reversed(parts):
                if p and p not in trusted_proxies:
                    return p
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def check_geo_location(self, ip: str) -> dict | None:
        """Opsiyonel: IP ülke/şehir. Dış servis kullanılmazsa None."""
        return None
