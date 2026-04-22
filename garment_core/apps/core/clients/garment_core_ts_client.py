"""
packages/garment_core TypeScript API istemcisi.
Django garment analizi tamamlandıktan sonra TS API'ye garment push eder
ve TS API'den garment listesi okuyabilir.
"""
import hashlib
import hmac
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class GarmentCoreTSClient:
    """
    packages/garment_core TypeScript API ile iletişim kurar.

    Env / settings gereksinimleri:
      GARMENT_CORE_TS_URL         → TS servisinin base URL'i (ör. https://garment-core-ts.railway.app)
      GARMENT_CORE_TS_ENABLED     → bool, varsayılan False
      GARMENT_CORE_WEBHOOK_SECRET → HMAC imzalama için paylaşılan secret
      GARMENT_CORE_TS_API_KEY     → /api/v1/garments okuma için Bearer token
    """

    def __init__(self):
        self.enabled = getattr(settings, "GARMENT_CORE_TS_ENABLED", False)
        self.base_url = getattr(settings, "GARMENT_CORE_TS_URL", "").rstrip("/")
        self.webhook_secret = getattr(settings, "GARMENT_CORE_WEBHOOK_SECRET", "")
        self.api_key = getattr(settings, "GARMENT_CORE_TS_API_KEY", "")

    def _sign(self, body_bytes: bytes) -> str:
        """X-Hub-Signature-256 HMAC imzası üret."""
        if not self.webhook_secret:
            return ""
        sig = hmac.new(
            self.webhook_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={sig}"

    def push_garment(
        self,
        tenant_slug: str,
        garment_data: dict,
        external_ref: str = "",
    ) -> dict:
        """
        Garment analizi tamamlandığında TS API'ye gönder.

        Args:
            tenant_slug:   Kiracı slug'ı (ör. "stylecoree")
            garment_data:  MEHLR'den gelen veya Django'daki ham garment verisi
            external_ref:  Kaynak sistemdeki ID (yoksa garment Django PK kullanılır)

        Returns:
            {"success": True, "id": "...", "verdict": "allowed"}
            veya {"success": False, "error": "..."}
        """
        if not self.enabled:
            logger.debug("GarmentCoreTSClient devre dışı (GARMENT_CORE_TS_ENABLED=False)")
            return {"success": False, "reason": "disabled"}

        if not self.base_url or not self.webhook_secret:
            logger.warning("GARMENT_CORE_TS_URL veya GARMENT_CORE_WEBHOOK_SECRET eksik")
            return {"success": False, "reason": "config_missing"}

        payload = {
            "event": "garment.upserted",
            "tenant_slug": tenant_slug,
            "payload": {
                "external_ref": external_ref or str(garment_data.get("id", "")),
                "raw": garment_data,
            },
        }
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        signature = self._sign(body_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        }

        try:
            response = requests.post(
                f"{self.base_url}/webhook/mehlr",
                data=body_bytes,
                headers=headers,
                timeout=15,
            )
            if response.status_code == 200:
                return {"success": True, **response.json()}
            elif response.status_code == 401:
                logger.error("GarmentCoreTS HMAC doğrulama başarısız")
                return {"success": False, "error": "Geçersiz imza"}
            elif response.status_code == 422:
                data = response.json()
                logger.warning("GarmentCoreTS güvenlik reddi: %s", data.get("verdict"))
                return {
                    "success": False,
                    "error": "security_rejected",
                    "verdict": data.get("verdict"),
                }
            else:
                logger.error(
                    "GarmentCoreTS hata %s: %s",
                    response.status_code,
                    response.text[:200],
                )
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except requests.Timeout:
            logger.error("GarmentCoreTS zaman aşımı")
            return {"success": False, "error": "Zaman aşımı"}
        except requests.ConnectionError:
            logger.error("GarmentCoreTS bağlantı hatası: %s", self.base_url)
            return {"success": False, "error": "Bağlantı kurulamadı"}
        except Exception as e:
            logger.exception("GarmentCoreTS beklenmeyen hata: %s", e)
            return {"success": False, "error": str(e)}

    def list_garments(
        self,
        tenant_slug: str,
        limit: int = 25,
        cursor: str = "",
    ) -> dict:
        """
        TS API'den kiracıya ait garment listesini oku.

        Returns:
            {"success": True, "garments": [...], "next_cursor": "..."}
            veya {"success": False, "error": "..."}
        """
        if not self.enabled or not self.base_url or not self.api_key:
            return {"success": False, "reason": "disabled_or_config_missing"}

        params: dict = {"tenant_slug": tenant_slug, "limit": limit}
        if cursor:
            params["cursor"] = cursor

        try:
            response = requests.get(
                f"{self.base_url}/v1/garments",
                params=params,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            if response.status_code == 200:
                return {"success": True, **response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def health_check(self) -> bool:
        """TS servisinin ayakta olup olmadığını kontrol et."""
        if not self.enabled or not self.base_url:
            return False
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
