"""
Multi-Tenant ecosystem registry — dinamik köken ve tenant slug eşlemesi.

registry.json şeması:
  { "version": 1, "tenants": [ { "slug", "folder?", "origins": [...] }, ... ] }

Yol: ERDENIZ_ECOSYSTEM_REGISTRY ortam değişkeni veya Multi-Tenant kökünde ecosystem/registry.json
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator


def _default_registry_path() -> Path:
    env = (
        os.environ.get("ERDENIZ_ECOSYSTEM_REGISTRY", "").strip()
        or os.environ.get("ECOSYSTEM_REGISTRY_PATH", "").strip()
    )
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    # .../Multi-Tenant/erdeniz_security/erdeniz_security/ecosystem_registry.py
    multi_tenant_root = here.parents[2]
    return (multi_tenant_root / "ecosystem" / "registry.json").resolve()


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    path = _default_registry_path()
    if not path.is_file():
        return {"version": 1, "tenants": []}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"version": 1, "tenants": []}
        tenants = data.get("tenants")
        if not isinstance(tenants, list):
            data["tenants"] = []
        return data
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "tenants": []}


def reload_registry() -> dict[str, Any]:
    load_registry.cache_clear()
    return load_registry()


def iter_ecosystem_origins() -> Iterator[str]:
    for row in load_registry().get("tenants", []):
        if not isinstance(row, dict):
            continue
        for o in row.get("origins") or []:
            if isinstance(o, str) and o.strip():
                yield o.strip().rstrip("/")


def slug_for_origin(origin: str) -> str | None:
    if not origin or not isinstance(origin, str):
        return None
    norm = origin.strip().rstrip("/")
    for row in load_registry().get("tenants", []):
        if not isinstance(row, dict):
            continue
        slug = row.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            continue
        for o in row.get("origins") or []:
            if isinstance(o, str) and o.strip().rstrip("/") == norm:
                return slug.strip()
    return None


def origins_for_slug(slug: str) -> list[str]:
    out: list[str] = []
    s = (slug or "").strip().lower()
    for row in load_registry().get("tenants", []):
        if not isinstance(row, dict):
            continue
        if str(row.get("slug", "")).strip().lower() == s:
            for o in row.get("origins") or []:
                if isinstance(o, str) and o.strip():
                    out.append(o.strip())
            break
    return out
