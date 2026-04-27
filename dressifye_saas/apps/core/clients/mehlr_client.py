import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MEHLRClient:
    """
    MEHLR 1.0 AI motoruna bağlanan client.
    EvidenceHome ile aynı auth mekanizması: X-API-Key header.
    """

    def __init__(self):
        self.enabled = getattr(settings, "MEHLR_ENABLED", False)
        self.base_url = getattr(settings, "MEHLR_URL", "").rstrip("/")
        self.api_key = getattr(settings, "MEHLR_API_KEY", "")

    def _headers(self):
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def analyze(self, project: str, prompt: str, context: dict = None) -> dict:
        """
        MEHLR'e analiz isteği gönder.

        Args:
            project: MEHLR'deki proje adı — settings.MEHLR_PROJECT (varsayılan dressifye_saas)
            prompt: Kullanıcının isteği
            context: Ek bağlam (gardırop, vücut ölçüleri vs.)

        Returns:
            {'success': True, 'data': {...}}
            veya
            {'success': False, 'error': '...'}
        """
        if not self.enabled:
            logger.debug("MEHLR devre dışı (MEHLR_ENABLED=False)")
            return {"success": False, "reason": "disabled"}

        if not self.base_url or not self.api_key:
            logger.warning("MEHLR_URL veya MEHLR_API_KEY eksik")
            return {"success": False, "reason": "config_missing"}

        endpoint = f"{self.base_url}/mehlr/api/analyze/"

        payload = {
            "project": project,
            "prompt": prompt,
            "context": context or {},
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=self._headers(),
                timeout=60,
            )

            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data}

            elif response.status_code == 401:
                logger.error("MEHLR API key geçersiz")
                return {"success": False, "error": "Geçersiz API key"}

            elif response.status_code == 429:
                logger.warning("MEHLR rate limit aşıldı")
                return {"success": False, "error": "İstek limiti aşıldı"}

            else:
                logger.error(
                    f"MEHLR hata: {response.status_code} — {response.text[:200]}"
                )
                return {
                    "success": False,
                    "error": f"MEHLR {response.status_code} hatası",
                }

        except requests.Timeout:
            logger.error("MEHLR zaman aşımı (60s)")
            return {"success": False, "error": "Zaman aşımı"}

        except requests.ConnectionError:
            logger.error(f"MEHLR bağlantı hatası: {self.base_url}")
            return {"success": False, "error": "Bağlantı kurulamadı"}

        except Exception as e:
            logger.exception(f"MEHLR beklenmeyen hata: {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> bool:
        """MEHLR'in ayakta olup olmadığını kontrol et."""
        if not self.enabled:
            return False
        try:
            response = requests.get(
                f"{self.base_url}/mehlr/",
                headers=self._headers(),
                timeout=10,
            )
            return response.status_code in (200, 302)
        except Exception:
            return False
