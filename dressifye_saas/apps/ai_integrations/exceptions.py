"""Harici AI entegrasyonu için özel istisna hiyerarşisi (üretim gözlemi)."""

from __future__ import annotations

from typing import Any


class AIProviderError(Exception):
    """Sağlayıcı veya kota katmanında beklenen hata tabanı."""

    def __init__(self, message: str = "", *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context: dict[str, Any] = context or {}


class QuotaExceededError(AIProviderError):
    """Kullanıcının plan kotası veya harici AI kotası yetersiz."""

    def __init__(
        self,
        message: str = "",
        *,
        required: int | None = None,
        available: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context=context or {})
        self.required = required
        self.available = available


class ProviderUnavailableError(AIProviderError):
    """Servis kapalı, zaman aşımı veya ağ hatası."""

    def __init__(
        self,
        message: str = "",
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        ctx = dict(context or {})
        if status_code is not None:
            ctx["status_code"] = status_code
        if response_body is not None:
            ctx["response_body"] = response_body[:4000] if response_body else ""
        super().__init__(message, context=ctx)
        self.status_code = status_code
        self.response_body = response_body


class InvalidInputError(AIProviderError):
    """Doğrulanamayan girdi (URL, payload)."""

    def __init__(
        self,
        message: str = "",
        *,
        field: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        ctx = dict(context or {})
        if field:
            ctx["field"] = field
        super().__init__(message, context=ctx)
        self.field = field


class ProviderAuthenticationError(AIProviderError):
    """401 / geçersiz API anahtarı."""

    pass


class ProviderRateLimitError(AIProviderError):
    """HTTP 429 veya yerel oran sınırı."""

    def __init__(
        self,
        message: str = "",
        *,
        retry_after: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        ctx = dict(context or {})
        if retry_after is not None:
            ctx["retry_after"] = retry_after
        super().__init__(message, context=ctx)
        self.retry_after = retry_after


class TaskCancellationError(AIProviderError):
    """Uzak veya yerel iptal başarısız."""

    pass


class WebhookValidationError(AIProviderError):
    """Webhook imza veya gövde doğrulaması."""

    pass


class ConfigurationError(AIProviderError):
    """Eksik base_url, anahtar veya sağlayıcı yapılandırması."""

    pass
