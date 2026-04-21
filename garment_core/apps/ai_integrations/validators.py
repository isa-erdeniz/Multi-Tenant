"""
Girdi doğrulama: Django URLValidator + SSRF ve görev türüne göre şema.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _

from apps.ai_integrations.exceptions import InvalidInputError
from apps.ai_integrations.models import AIProcessingTask

_PRIVATE_IP_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)

BLOCKED_PORTS = frozenset(
    {22, 23, 25, 53, 110, 143, 3306, 3389, 5432, 6379, 9200, 9300}
)

_BLOCKED_HOST_PATTERNS = (
    re.compile(r"^localhost$", re.I),
    re.compile(r"^127\.\d+\.\d+\.\d+$"),
    re.compile(r"^0\.0\.0\.0$"),
    re.compile(r"^metadata\.google\.internal$", re.I),
    re.compile(r"^metadata$", re.I),
)

_ALLOWED_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
MAX_URL_LENGTH = 2048


def _host_is_blocked(host: str) -> bool:
    if not host or host.startswith("."):
        return True
    h = host.strip("[]").lower()
    for pat in _BLOCKED_HOST_PATTERNS:
        if pat.match(h):
            return True
    try:
        ip = ipaddress.ip_address(h)
        for net in _PRIVATE_IP_NETWORKS:
            if ip in net:
                return True
        return False
    except ValueError:
        return False


def _django_url_validate(url: str) -> None:
    """Django URLValidator ile biçim kontrolü."""
    validator = URLValidator(schemes=("http", "https"))
    try:
        validator(url)
    except ValidationError as exc:
        raise InvalidInputError(exc.messages[0], field="url") from exc


def validate_safe_https_url(url: str) -> str:
    """
    URLValidator + http(s) + özel ağ / port SSRF koruması.

    Args:
        url: Tam URL.

    Returns:
        Şeritlenmiş URL.

    Raises:
        InvalidInputError: Geçersiz veya güvensiz URL.
    """
    if not url or not isinstance(url, str):
        raise InvalidInputError(_("Geçerli bir URL gerekli."), field="url")
    u = url.strip()
    if len(u) > MAX_URL_LENGTH:
        raise InvalidInputError(_("URL çok uzun."), field="url")
    _django_url_validate(u)
    parsed = urlparse(u)
    if parsed.scheme not in {"http", "https"}:
        raise InvalidInputError(_("Yalnızca http ve https URL'lerine izin verilir."), field="url")
    if not parsed.hostname:
        raise InvalidInputError(_("URL ana bilgisayar içermiyor."), field="url")
    if parsed.port and parsed.port in BLOCKED_PORTS:
        raise InvalidInputError(_("Bu porta istek gönderilemez."), field="url")
    if _host_is_blocked(parsed.hostname):
        raise InvalidInputError(_("Bu hedefe istek gönderilemez (SSRF koruması)."), field="url")
    return u


def validate_input_image_urls(input_data: dict[str, Any]) -> None:
    """
    Try-on için zorunlu görsel URL alanlarını doğrular.

    Args:
        input_data: İstemci JSON nesnesi.

    Raises:
        InvalidInputError: Eksik veya geçersiz alan.
    """
    if not isinstance(input_data, dict):
        raise InvalidInputError(_("input_data bir nesne olmalıdır."), field="input_data")
    garment = input_data.get("garment_image") or input_data.get("garment_image_url")
    model_img = input_data.get("model_image") or input_data.get("model_image_url")
    for label, val in (
        ("garment_image", garment),
        ("model_image", model_img),
    ):
        if val is None or val == "":
            raise InvalidInputError(_("{field} zorunludur.").format(field=label), field=label)
        validate_image_style_url(str(val), field=label)


def validate_image_style_url(url: str, *, field: str = "url") -> str:
    """
    Görsel URL için isteğe bağlı uzantı kontrolü + SSRF.

    Args:
        url: Kaynak adresi.
        field: Hata bağlamı için alan adı.

    Returns:
        Doğrulanmış URL.
    """
    u = validate_safe_https_url(url)
    path = urlparse(u).path.split("?")[0].lower()
    base = path.rsplit("/", 1)[-1] if path else ""
    if base and "." in base:
        suf = "." + base.rsplit(".", 1)[-1]
        if suf not in _ALLOWED_IMAGE_EXT:
            raise InvalidInputError(
                _("Desteklenmeyen görsel uzantısı."),
                field=field,
            )
    return u


def _check_url_accessible_head(url: str, timeout: float = 5.0) -> None:
    """HEAD ile erişilebilirlik (isteğe bağlı, sıkı mod)."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.head(url)
            if r.status_code >= 400:
                raise InvalidInputError(_("URL erişilebilir değil."), field="url")
            ct = (r.headers.get("content-type") or "").lower()
            if ct and not ct.startswith("image/"):
                raise InvalidInputError(_("Beklenen içerik türü image/* değil."), field="url")
    except httpx.RequestError as exc:
        raise InvalidInputError(str(exc), field="url") from exc


def validate_ai_input(
    input_data: dict[str, Any],
    task_type: str,
    *,
    check_urls_accessible: bool = False,
) -> None:
    """
    Görev türüne göre tüm görsel URL alanlarını doğrular.

    Args:
        input_data: Ham girdi.
        task_type: AIProcessingTask.task_type değeri.
        check_urls_accessible: True ise HEAD ile doğrulama (daha yavaş).

    Raises:
        InvalidInputError: Şema veya URL geçersizse.
    """
    if not isinstance(input_data, dict):
        raise InvalidInputError(_("input_data bir nesne olmalıdır."), field="input_data")
    opts = input_data.get("options")
    if opts is not None and not isinstance(opts, dict):
        raise InvalidInputError(_("options bir nesne olmalıdır."), field="options")

    urls_to_check: list[tuple[str, str]] = []

    if task_type == AIProcessingTask.TASK_TRYON:
        validate_input_image_urls(input_data)
        return
    if task_type == AIProcessingTask.TASK_MODEL_GENERATION:
        if not input_data.get("prompt"):
            raise InvalidInputError(_("model_generation için prompt zorunludur."), field="prompt")
        for key in ("reference_image", "model_image", "image_url"):
            v = input_data.get(key)
            if v:
                urls_to_check.append((key, str(v)))
    elif task_type == AIProcessingTask.TASK_TEXTURE:
        v = input_data.get("source_image_url")
        if not v:
            raise InvalidInputError(_("texture_creation için source_image_url zorunludur."), field="source_image_url")
        urls_to_check.append(("source_image_url", str(v)))
    elif task_type in (
        AIProcessingTask.TASK_BACKGROUND_REMOVAL,
        AIProcessingTask.TASK_POSE_TRANSFER,
    ):
        v = input_data.get("image_url") or input_data.get("source_image")
        if not v:
            raise InvalidInputError(_("image_url zorunludur."), field="image_url")
        urls_to_check.append(("image_url", str(v)))
    elif task_type == AIProcessingTask.TASK_GARMENT_3D:
        u = input_data.get("pattern_file_url") or input_data.get("texture_url")
        if u:
            urls_to_check.append(("url", str(u)))
        if not input_data.get("garment_spec") and not u:
            raise InvalidInputError(
                _("garment_spec veya pattern_file_url gerekli."),
                field="garment_spec",
            )
    else:
        for key, val in input_data.items():
            if not isinstance(val, str) or not val.startswith("http"):
                continue
            lk = key.lower()
            if "url" in lk or lk.endswith("_image"):
                urls_to_check.append((key, val))

    for field, u in urls_to_check:
        validate_image_style_url(u, field=field)
        if check_urls_accessible:
            _check_url_accessible_head(u)


def sanitize_filename(filename: str) -> str:
    """
    Yol ayırıcıları ve null baytları kaldırır.

    Args:
        filename: Ham dosya adı.

    Returns:
        Güvenli kısa ad (en fazla 255 karakter).
    """
    if not filename:
        return "file"
    name = str(filename).replace("\x00", "")
    name = name.replace("\\", "").replace("/", "")
    if ".." in name:
        name = name.replace("..", "")
    return name[:255]
