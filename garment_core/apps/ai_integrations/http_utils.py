"""
HTTP yanıtlarını AI sağlayıcı istisnalarına eşler.
"""

from __future__ import annotations

import httpx
from django.utils.translation import gettext_lazy as _

from apps.ai_integrations.exceptions import (
    InvalidInputError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)


def raise_for_ai_http_status(resp: httpx.Response) -> None:
    """
    httpx yanıtını işler; başarısızsa uygun AIProviderError alt sınıfını fırlatır.

    Args:
        resp: Tamamlanmış HTTP yanıtı.

    Raises:
        ProviderAuthenticationError: 401.
        ProviderRateLimitError: 429 (Retry-After okunur).
        ProviderUnavailableError: 5xx veya ağ benzeri sunucu hataları.
        InvalidInputError: Diğer 4xx.
    """
    if resp.is_success:
        return
    code = resp.status_code
    text = (resp.text or "")[:8000]
    if code == 401:
        raise ProviderAuthenticationError(_("Sağlayıcı kimlik doğrulaması başarısız."))
    if code == 429:
        raw = resp.headers.get("Retry-After", "60")
        try:
            retry_after = max(1, int(raw))
        except (TypeError, ValueError):
            retry_after = 60
        raise ProviderRateLimitError(
            _("Sağlayıcı oran sınırı."),
            retry_after=retry_after,
        )
    if code >= 500:
        raise ProviderUnavailableError(
            _("Sağlayıcı geçici olarak kullanılamıyor."),
            status_code=code,
            response_body=text,
        )
    raise InvalidInputError(text[:2000] or _("Geçersiz istek."), field="http_response")
