"""
Dressifye HTTP API istemcisi — gardırop, profil ve kombin senkronizasyonu.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class DressifyeClient:
    """
    Dressifye REST API ile konuşur.
    Tüm isteklerde ``X-API-Key`` (Dressifye anahtarı) ve ``X-Service-Name: mehlr`` gönderilir.
    """

    SERVICE_NAME = "mehlr"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self._base_url = (base_url or getattr(settings, "DRESSIFYE_API_URL", "") or "").rstrip("/")
        self._api_key = api_key if api_key is not None else getattr(settings, "DRESSIFYE_API_KEY", "") or ""
        self._timeout = timeout or _DEFAULT_TIMEOUT

    def _headers(self, *, json_body: bool = False) -> dict[str, str]:
        h: dict[str, str] = {
            "X-API-Key": self._api_key,
            "X-Service-Name": self.SERVICE_NAME,
            "Accept": "application/json",
        }
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    def get_user_wardrobe(self, user_id: str) -> list[dict[str, Any]]:
        """
        Kullanıcının gardırobunu Dressifye API'den çeker.
        Beklenen yol: ``GET /users/{user_id}/wardrobe/`` (JSON dizi veya ``items`` anahtarı).
        """
        if not self._base_url:
            logger.warning("DressifyeClient: DRESSIFYE_API_URL tanımlı değil; gardırop boş dönüyor.")
            return []
        url = f"{self._base_url}/users/{user_id}/wardrobe/"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, headers=self._headers(json_body=False))
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
            if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
                return [x for x in data["items"] if isinstance(x, dict)]
            if isinstance(data, dict) and "wardrobe" in data and isinstance(data["wardrobe"], list):
                return [x for x in data["wardrobe"] if isinstance(x, dict)]
            logger.warning(
                "DressifyeClient.get_user_wardrobe: beklenmeyen JSON şekli user_id=%s keys=%s",
                user_id,
                list(data.keys()) if isinstance(data, dict) else type(data).__name__,
            )
            return []
        except httpx.HTTPStatusError as e:
            logger.error(
                "DressifyeClient.get_user_wardrobe HTTP hatası user_id=%s status=%s body=%s",
                user_id,
                e.response.status_code,
                e.response.text[:500] if e.response else "",
            )
            return []
        except httpx.RequestError as e:
            logger.error("DressifyeClient.get_user_wardrobe bağlantı hatası user_id=%s: %s", user_id, e)
            return []
        except ValueError as e:
            logger.error("DressifyeClient.get_user_wardrobe JSON parse hatası user_id=%s: %s", user_id, e)
            return []

    def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """
        Kullanıcı profil bilgilerini çeker.
        Beklenen yol: ``GET /users/{user_id}/profile/``.
        """
        if not self._base_url:
            logger.warning("DressifyeClient: DRESSIFYE_API_URL tanımlı değil; profil boş dönüyor.")
            return {}
        url = f"{self._base_url}/users/{user_id}/profile/"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, headers=self._headers(json_body=False))
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data
            logger.warning(
                "DressifyeClient.get_user_profile: dict bekleniyordu user_id=%s tip=%s",
                user_id,
                type(data).__name__,
            )
            return {}
        except httpx.HTTPStatusError as e:
            logger.error(
                "DressifyeClient.get_user_profile HTTP hatası user_id=%s status=%s body=%s",
                user_id,
                e.response.status_code,
                e.response.text[:500] if e.response else "",
            )
            return {}
        except httpx.RequestError as e:
            logger.error("DressifyeClient.get_user_profile bağlantı hatası user_id=%s: %s", user_id, e)
            return {}
        except ValueError as e:
            logger.error("DressifyeClient.get_user_profile JSON parse hatası user_id=%s: %s", user_id, e)
            return {}

    def sync_recommendation_to_dressifye(self, recommendation_data: dict[str, Any]) -> bool:
        """
        MEHLR'ın ürettiği kombin önerisini Dressifye'a gönderir.
        Beklenen yol: ``POST /recommendations/sync/``.
        """
        if not self._base_url:
            logger.warning("DressifyeClient: DRESSIFYE_API_URL tanımlı değil; senkron başarısız.")
            return False
        url = f"{self._base_url}/recommendations/sync/"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    url,
                    headers=self._headers(json_body=True),
                    json=recommendation_data,
                )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error(
                "DressifyeClient.sync_recommendation_to_dressifye HTTP hatası status=%s body=%s",
                e.response.status_code,
                e.response.text[:500] if e.response else "",
            )
            return False
        except httpx.RequestError as e:
            logger.error("DressifyeClient.sync_recommendation_to_dressifye bağlantı hatası: %s", e)
            return False
        except (TypeError, ValueError) as e:
            logger.error("DressifyeClient.sync_recommendation_to_dressifye serileştirme hatası: %s", e)
            return False
