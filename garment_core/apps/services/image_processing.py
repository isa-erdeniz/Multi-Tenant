"""
Görsel işleme servisleri — arka plan silme vb.
"""
import io
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def remove_background(image_file):
    """
    Remove.bg API ile arka planı temizle, transparent PNG döndür.

    Args:
        image_file: Django ImageField veya açık dosya objesi.
            path veya .open() ile okunabilir olmalı.

    Returns:
        bytes: Transparent PNG içeriği, başarılıysa.
        None: API hatası, kota veya geçersiz istek — orijinal kullan (fallback).
    """
    api_key = getattr(settings, "REMOVE_BG_API_KEY", "") or ""
    if not api_key:
        logger.debug("REMOVE_BG_API_KEY tanımlı değil, arka plan silme atlanıyor")
        return None

    try:
        if hasattr(image_file, "open"):
            with image_file.open("rb") as f:
                file_content = f.read()
                file_obj = io.BytesIO(file_content)
        elif hasattr(image_file, "read"):
            file_obj = image_file
        else:
            with open(image_file, "rb") as f:
                file_obj = io.BytesIO(f.read())

        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        filename = "image.jpg"
        if hasattr(image_file, "name"):
            filename = image_file.name or filename
        elif isinstance(image_file, str):
            import os
            filename = os.path.basename(image_file) or filename

        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "jpg"
        content_type = {"png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
        files = {"image_file": (filename, file_obj, content_type)}
        data = {"size": "auto"}
        headers = {"X-Api-Key": api_key}

        resp = requests.post(
            "https://api.remove.bg/v1.0/removebg",
            files=files,
            data=data,
            headers=headers,
            timeout=60,
        )

        if resp.status_code == 200:
            return resp.content

        # Kota, yetkisiz, veya diğer hatalar — fallback (orijinal bırak)
        if resp.status_code == 402:
            logger.warning("Remove.bg: API kotası aşıldı (402)")
        elif resp.status_code == 403:
            logger.warning("Remove.bg: Geçersiz veya eksik API key (403)")
        else:
            logger.warning("Remove.bg: %s — %s", resp.status_code, resp.text[:200])
        return None

    except requests.RequestException as e:
        logger.warning("Remove.bg API hatası: %s", e)
        return None
    except (IOError, OSError) as e:
        logger.warning("Remove.bg dosya okuma hatası: %s", e)
        return None
