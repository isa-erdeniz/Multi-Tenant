"""
Yüz Tespiti & Özellik Analizi — MEHLR tabanlı.
beauty ve avatar task'larına yüz bağlamı sağlar.
"""
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def analyze_face_from_session(photo_field) -> dict:
    """
    Fotoğraftan yüz özelliklerini MEHLR ile analiz et.

    Args:
        photo_field: Django ImageField (session.photo gibi).

    Returns:
        dict: {
            "detected": bool,
            "skin_tone": str | None,       # "açık", "orta", "koyu"
            "face_shape": str | None,      # "oval", "yuvarlak", "kare", "kalp", "uzun"
            "undertone": str | None,       # "sıcak", "soğuk", "nötr"
            "recommendations": list[str],  # makyaj/saç önerileri
            "raw_response": str | None,
        }
        Hata durumunda: {"detected": False, "error": str}
    """
    from django.conf import settings
    from apps.core.clients.mehlr_client import MEHLRClient

    if not photo_field:
        return {"detected": False, "error": "Fotoğraf yok"}

    client = MEHLRClient()
    result = client.analyze(
        project=settings.MEHLR_PROJECT,
        prompt=(
            "Bir portre fotoğrafındaki yüzü analiz et ve JSON formatında yanıt ver.\n\n"
            "Yanıt formatı (sadece JSON, başka hiçbir şey yazma):\n"
            '{"detected": true, '
            '"skin_tone": "açık|orta|koyu", '
            '"face_shape": "oval|yuvarlak|kare|kalp|uzun", '
            '"undertone": "sıcak|soğuk|nötr", '
            '"recommendations": ["öneri1", "öneri2"]}'
        ),
        context={
            "task": "face_analysis",
            "photo_name": getattr(photo_field, "name", ""),
        },
    )

    if not result.get("success"):
        logger.warning("Yüz analizi MEHLR hatası: %s", result.get("error"))
        return {"detected": False, "error": result.get("error", "MEHLR hatası")}

    raw = result["data"].get("response", "") or ""

    try:
        # MEHLR bazen markdown code block içinde JSON döndürür — temizle
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        data = json.loads(clean)
        data["raw_response"] = raw
        return data
    except (json.JSONDecodeError, ValueError):
        logger.warning("Yüz analizi JSON parse hatası: %s", raw[:200])
        return {
            "detected": True,
            "skin_tone": None,
            "face_shape": None,
            "undertone": None,
            "recommendations": [],
            "raw_response": raw,
        }


def get_face_context_for_prompt(photo_field) -> str:
    """
    beauty/avatar task'larının MEHLR prompt'una ekleyeceği yüz bağlamı.
    Analiz başarısızsa boş string döner (task duraksın istemiyoruz).
    """
    try:
        face = analyze_face_from_session(photo_field)
        if not face.get("detected"):
            return ""
        parts = []
        if face.get("skin_tone"):
            parts.append(f"Ten tonu: {face['skin_tone']}")
        if face.get("face_shape"):
            parts.append(f"Yüz şekli: {face['face_shape']}")
        if face.get("undertone"):
            parts.append(f"Renk alt tonu: {face['undertone']}")
        return "\n".join(parts)
    except Exception as e:
        logger.warning("get_face_context_for_prompt hata: %s", e)
        return ""
