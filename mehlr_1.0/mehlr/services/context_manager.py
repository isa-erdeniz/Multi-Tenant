"""
mehlr_1.0 Context Manager — Dinamik bağlam yönetimi ve Dressifye gardırop → prompt.
"""
from __future__ import annotations

import hashlib
import logging
import random
from typing import Any

from django.core.cache import cache

from mehlr.integrations.dressifye_client import DressifyeClient
from mehlr.models import DressifyeUser, Project
from mehlr.prompts.project_prompts import PROJECT_CONTEXTS, PROJECT_PROMPTS

logger = logging.getLogger(__name__)

# Dressifye context cache (gardırop sık değişmez)
DRESSIFYE_CONTEXT_CACHE_TTL = 300  # 5 dakika
DRESSIFYE_CONTEXT_CACHE_PREFIX = "dressifye_context"
MAX_PROMPT_WARDROBE_ITEMS = 30
TOKENS_PER_ITEM_ESTIMATE = 100

# DressifyeUser.profile_data — HairInfinity saç/yüz verisi
PROFILE_KEY_HAIR_INFINITY = "hair_infinity"

# API yok veya boş yanıt — geliştirme / yedek
_MOCK_WARDROBE: list[dict[str, Any]] = [
    {
        "id": "mock-ext-1",
        "name": "Siyah Blazer",
        "category": "Üst Giyim",
        "color": "Siyah",
        "size": "M",
        "metadata": {"season": "ilkbahar"},
    },
    {
        "id": "mock-ext-2",
        "name": "Beyaz Gömlek",
        "category": "Üst Giyim",
        "color": "Beyaz",
        "size": "L",
        "metadata": {"season": "yaz"},
    },
    {
        "id": "mock-ext-3",
        "name": "Lacivert Pantolon",
        "category": "Alt Giyim",
        "color": "Lacivert",
        "size": "32",
        "metadata": {"season": "genel"},
    },
    {
        "id": "mock-ext-4",
        "name": "Deri Ayakkabı",
        "category": "Ayakkabı",
        "color": "Kahverengi",
        "size": "42",
        "metadata": {"season": "genel"},
    },
]


def get_enriched_context(
    project_key: str,
    conversation_history: list,
    user_message: str,
    extra_data: dict | None = None,
) -> str:
    """
    Proje bağlamını konuşma geçmişi ve ek veriyle zenginleştir.
    ai_engine'e geçmeden önce final system prompt için kullanılabilir.
    """
    project = PROJECT_PROMPTS.get(project_key)
    if not project:
        return PROJECT_CONTEXTS.get("general", "")

    context_parts = [
        f"Proje: {project['display_name']}",
        f"Domain: {project['domain']}",
        f"Aktif Özellikler: {', '.join(project.get('capabilities', []))}",
    ]

    if conversation_history:
        summary = _summarize_history(conversation_history)
        if summary:
            context_parts.append(f"Konuşma Özeti: {summary}")

    intent = _detect_intent(user_message, project.get("capabilities", []))
    if intent:
        context_parts.append(f"Tespit Edilen Niyet: {intent}")

    if extra_data:
        context_parts.append(f"Ek Bağlam: {extra_data}")

    return "\n".join(context_parts)


def _summarize_history(conversation_history: list) -> str:
    """Son 3 mesajdan kısa bağlam özeti üret."""
    recent = (
        conversation_history[-3:]
        if len(conversation_history) >= 3
        else conversation_history
    )
    return " | ".join(
        [
            f"{m.get('role', '?')}: {str(m.get('content', ''))[:80]}"
            for m in recent
        ]
    )


def _detect_intent(user_message: str, capabilities: list) -> str:
    """Basit keyword → intent eşleştirme."""
    msg_lower = (user_message or "").lower()
    intent_map = {
        "rapor": "reporting",
        "analiz": "analysis",
        "öneri": "recommendation",
        "sorun": "troubleshooting",
        "karşılaştır": "comparison",
        "tahmin": "prediction",
        "liste": "listing",
        "özet": "summarization",
    }
    for keyword, intent in intent_map.items():
        if keyword in msg_lower:
            return intent
    return "general_query"


def get_project_context(project_slug: str | None = None) -> str:
    """
    Proje slug'ına göre AI bağlam metnini döndürür.
    garment_core / garment-core uyumsuzluğunu da çözer.
    """
    if not project_slug or project_slug == "general":
        return PROJECT_CONTEXTS.get("general", "")
    slug = project_slug.lower().strip()
    normalized = slug.replace("-", "_")
    ctx = PROJECT_CONTEXTS.get(slug) or PROJECT_CONTEXTS.get(normalized)
    if ctx:
        return ctx
    try:
        p = Project.objects.get(slug=slug, is_active=True)
        return p.context_prompt or PROJECT_CONTEXTS.get("general", "")
    except Project.DoesNotExist:
        try:
            p = Project.objects.get(slug=normalized, is_active=True)
            return p.context_prompt or PROJECT_CONTEXTS.get("general", "")
        except Project.DoesNotExist:
            return PROJECT_CONTEXTS.get("general", "")


def get_cross_project_context() -> str:
    """Tüm aktif projelerin özet bağlamını döndürür."""
    parts = [PROJECT_CONTEXTS.get("general", "")]
    for p in Project.objects.filter(is_active=True).order_by("name"):
        parts.append(f"- {p.name} ({p.slug}): {p.description[:100]}...")
    return "\n".join(parts)


def enrich_context(project_slug: str | None, user_query: str) -> str:
    """Sorguya göre bağlamı zenginleştirir (geriye dönük uyumluluk)."""
    return get_project_context(project_slug)


# ─────────────────────────────────────────────
# Dressifye — gardırop → AI prompt
# ─────────────────────────────────────────────


def _normalize_garment(raw: dict[str, Any]) -> dict[str, Any]:
    """API / DB farklı anahtarlarını tek şemaya indirger."""
    gid = raw.get("id") or raw.get("external_id") or raw.get("pk") or ""
    meta = raw.get("metadata") or {}
    if not isinstance(meta, dict):
        meta = {}
    return {
        "id": str(gid),
        "name": str(raw.get("name") or raw.get("title") or ""),
        "category": str(raw.get("category") or raw.get("type") or ""),
        "color": str(raw.get("color") or ""),
        "size": str(raw.get("size") or ""),
        "image_url": str(raw.get("image_url") or raw.get("image") or ""),
        "metadata": meta,
    }


def _category_bucket(category: str) -> str:
    """Kategori çeşitliliği için kaba gruplama."""
    c = (category or "").lower()
    if any(k in c for k in ("üst", "top", "gömlek", "bluz", "tişört", "shirt", "blazer", "kazak")):
        return "top"
    if any(k in c for k in ("alt", "pantolon", "etek", "jean", "bottom", "şort")):
        return "bottom"
    if any(k in c for k in ("ayakkabı", "shoe", "bot", "sneaker", "loafer")):
        return "shoes"
    if any(k in c for k in ("dış", "ceket", "mont", "coat", "jacket", "parka")):
        return "outer"
    if any(k in c for k in ("aksesuar", "çanta", "kemer", "şapka", "accessory", "bag")):
        return "accessory"
    return "other"


def _filter_by_season(items: list[dict[str, Any]], season: str) -> list[dict[str, Any]]:
    if not season:
        return items
    s = season.lower().strip()
    season_aliases = {
        "yaz": ("yaz", "summer"),
        "kış": ("kış", "kis", "winter"),
        "ilkbahar": ("ilkbahar", "spring"),
        "sonbahar": ("sonbahar", "autumn", "fall"),
    }
    needles = season_aliases.get(s, (s,))
    out: list[dict[str, Any]] = []
    for g in items:
        blob = f"{g.get('name', '')} {g.get('category', '')} {g.get('metadata', {})}".lower()
        meta = g.get("metadata") or {}
        meta_season = str(meta.get("season", "")).lower()
        if meta_season and any(n in meta_season for n in needles):
            out.append(g)
            continue
        if any(n in blob for n in needles):
            out.append(g)
    return out if out else items


def _filter_by_occasion(items: list[dict[str, Any]], occasion: str) -> list[dict[str, Any]]:
    if not occasion:
        return items
    o = occasion.lower().strip()
    keywords = {
        "iş": ("iş", "ofis", "business", "formal"),
        "spor": ("spor", "gym", "fitness", "antrenman"),
        "gece": ("gece", "party", "davet", "kına", "düğün"),
        "günlük": ("günlük", "casual", "daily"),
    }
    needles = keywords.get(o, (o,))
    out = [
        g
        for g in items
        if any(
            n in f"{g.get('name', '')} {g.get('category', '')}".lower()
            for n in needles
        )
    ]
    return out if out else items


def _diversify_and_cap(items: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    """Kategori kovalarına göre round-robin seç, gerekirse kalanı rastgele doldur."""
    if max_items <= 0:
        return []
    if len(items) <= max_items:
        return list(items)

    buckets: dict[str, list[dict[str, Any]]] = {}
    for g in items:
        b = _category_bucket(str(g.get("category", "")))
        buckets.setdefault(b, []).append(g)

    order = ["top", "bottom", "shoes", "outer", "accessory", "other"]
    picked: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def _push(g: dict[str, Any]) -> bool:
        gid = str(g.get("id", ""))
        if gid and gid in seen_ids:
            return False
        if gid:
            seen_ids.add(gid)
        picked.append(g)
        return True

    while len(picked) < max_items:
        progressed = False
        for bname in order:
            if len(picked) >= max_items:
                break
            while buckets.get(bname) and len(picked) < max_items:
                g = buckets[bname].pop(0)
                if _push(g):
                    progressed = True
                    break
        if not progressed:
            break

    for bname in order:
        while len(picked) < max_items and buckets.get(bname):
            g = buckets[bname].pop(0)
            _push(g)

    if len(picked) < max_items:
        pool = [g for g in items if g not in picked]
        random.shuffle(pool)
        for g in pool:
            if len(picked) >= max_items:
                break
            _push(g)

    return picked[:max_items]


def filter_wardrobe_for_prompt(
    garments: list[dict],
    occasion: str | None = None,
    season: str | None = None,
    max_items: int = MAX_PROMPT_WARDROBE_ITEMS,
) -> list[dict]:
    """
    Token limiti için gardırop küçültür: mevsim / etkinlik filtresi ve kategori çeşitliliği.
    50+ parçada max_items (varsayılan 30) ile sınırlar.
    """
    normalized = [_normalize_garment(g) for g in garments if isinstance(g, dict)]
    items = _filter_by_season(normalized, season) if season else normalized
    items = _filter_by_occasion(items, occasion) if occasion else items
    if not items:
        return []
    if len(items) <= max_items:
        return list(items)
    return _diversify_and_cap(items, max_items)


def format_wardrobe_for_prompt(
    garments: list[dict],
    *,
    total_source_count: int | None = None,
) -> str:
    """
    AI system prompt'una eklenecek Türkçe metin bloğu.

    total_source_count: Filtreleme / token sınırı öncesi toplam parça sayısı.
    Gönderilen parça sayısı bundan küçükse AI'ya alt örneklem uyarısı eklenir.
    """
    lines: list[str] = []
    n = len(garments)
    total = total_source_count if total_source_count is not None else n
    if total > n:
        lines.append(
            f"Sana kullanıcının tüm gardırobunu değil, en alakalı {n} parçayı gönderiyorum "
            f"(gardıropta toplam {total} parça var). Bu listede olmayan başka kıyafetler de olabilir; "
            "kullanıcının yalnızca bu ürünlere sahip olduğunu varsayma."
        )
        lines.append("")
    lines.append("Kullanıcının mevcut gardırobundaki ürünler:")
    for g in garments:
        ng = _normalize_garment(g) if isinstance(g, dict) else _normalize_garment({})
        lines.append(
            f"- ID: {ng['id']}, İsim: {ng['name']}, Kategori: {ng['category']}, "
            f"Renk: {ng['color']}, Beden: {ng['size']}"
        )
    lines.append("Bu ürünlerin ID'lerini kullanarak kombin öner.")
    return "\n".join(lines)


def build_core_context(user_id: str) -> dict[str, Any]:
    """
    Garment-Core için birleşik bağlam: MEHLR tarafında saklanan HairInfinity + cross-tenant saç verisi.
    """
    try:
        user = DressifyeUser.objects.filter(external_id=str(user_id)).first()
    except Exception as e:
        logger.debug("build_core_context: DressifyeUser okunamadı user_id=%s: %s", user_id, e)
        return {"hair_infinity": {}, "merged_hair": {}, "profile_data": {}}

    if user is None:
        return {"hair_infinity": {}, "merged_hair": {}, "profile_data": {}}

    pd = user.profile_data if isinstance(user.profile_data, dict) else {}
    hair = pd.get(PROFILE_KEY_HAIR_INFINITY)
    if not isinstance(hair, dict):
        hair = {}

    merged: dict[str, Any] = dict(hair)
    cts = pd.get("cross_tenant_sources")
    if isinstance(cts, dict):
        blob = cts.get("hair")
        if isinstance(blob, dict):
            merged = {**blob, **merged}

    return {"hair_infinity": hair, "merged_hair": merged, "profile_data": pd}


def extract_hair_form(core: dict[str, Any] | None) -> dict[str, Any]:
    """Prompt / API için yapılandırılmış saç formu (sac_formu, yüz, renk)."""
    if not core:
        return {}
    m = core.get("merged_hair") or {}
    if not isinstance(m, dict):
        return {}
    form = {
        "sac_formu": m.get("sac_formu") or m.get("hair_form") or m.get("hair_shape"),
        "sac_rengi": m.get("sac_rengi") or m.get("hair_color"),
        "yuz_sekli": m.get("yuz_sekli") or m.get("face_shape"),
        "sac_tipi": m.get("sac_tipi") or m.get("hair_type"),
        "notlar": m.get("notlar") or m.get("notes"),
    }
    return {k: v for k, v in form.items() if v not in (None, "", [])}


def format_integration_context_for_prompt(core: dict[str, Any]) -> str:
    """Dressifye kombin prompt'una eklenecek 'Entegrasyon Verisi' metni."""
    merged = core.get("merged_hair") if isinstance(core, dict) else {}
    if not isinstance(merged, dict) or not merged:
        return ""

    lines = [
        "Entegrasyon Verisi (HairInfinity / çapraz tenant):",
        "Bu kullanıcı için saç ve yüz profili; yaka tipi, aksesuar ve renk uyumunda kullan.",
    ]
    for k in sorted(merged.keys()):
        v = merged[k]
        if v in (None, "", {}):
            continue
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def merge_hair_form_into_wardrobe_context(
    wardrobe_context: dict[str, Any],
    hair_form: dict[str, Any] | None,
) -> None:
    """
    API isteğinde gelen saç formunu mevcut core_context ile birleştirir (Dressifye kombin).
    """
    if not hair_form:
        return
    core = wardrobe_context.get("core_context") or {}
    if not isinstance(core, dict):
        core = {}
    merged = dict(core.get("merged_hair") or {})
    merged.update({k: v for k, v in hair_form.items() if v not in (None, "")})
    wardrobe_context["core_context"] = {**core, "merged_hair": merged}
    wardrobe_context["hair_form"] = extract_hair_form(wardrobe_context["core_context"])
    wardrobe_context["integration_text"] = format_integration_context_for_prompt({"merged_hair": merged})


def store_hair_infinity_profile_data(user_id: str, hair_data: dict[str, Any]) -> None:
    """
    HairInfinity domain'inden gelen saç/yüz verisini DressifyeUser.profile_data içinde saklar.
    API veya webhook bu fonksiyonu çağırmalıdır.
    """
    user, _ = DressifyeUser.objects.get_or_create(
        external_id=str(user_id),
        defaults={"username": f"user_{str(user_id)[:40]}"},
    )
    pd = user.profile_data if isinstance(user.profile_data, dict) else {}
    existing = pd.get(PROFILE_KEY_HAIR_INFINITY)
    if not isinstance(existing, dict):
        existing = {}
    merged_hair = {**existing, **hair_data}
    pd[PROFILE_KEY_HAIR_INFINITY] = merged_hair
    user.profile_data = pd
    user.save(update_fields=["profile_data", "updated_at"])
    invalidate_dressifye_context_cache(user_id)


def bump_dressifye_context_cache_version(user_id: str) -> int:
    """
    Kullanıcıya ait tüm dressifye_context cache anahtarlarını geçersiz kılar (sürüm artışı).
    """
    vk = f"{DRESSIFYE_CONTEXT_CACHE_PREFIX}:v:{user_id}"
    try:
        v = int(cache.get(vk) or 0) + 1
        cache.set(vk, v, timeout=86400 * 365)
        return v
    except Exception as e:
        logger.warning("Dressifye cache sürümü artırılamadı user_id=%s: %s", user_id, e)
        return 0


def invalidate_dressifye_context_cache(user_id: str) -> None:
    """Webhook / senkron sonrası gardırop bağlamı önbelleğini temizlemek için sürüm artır."""
    bump_dressifye_context_cache_version(user_id)


_CACHE_KEYS_STRIP = frozenset({"core_context", "hair_form", "integration_text"})


def _attach_core_context(user_id: str, result: dict[str, Any]) -> None:
    """Önbellekten bağımsız taze HairInfinity / entegrasyon metni."""
    core = build_core_context(user_id)
    result["core_context"] = core
    result["hair_form"] = extract_hair_form(core)
    result["integration_text"] = format_integration_context_for_prompt(core)


def _cache_key(user_id: str, occasion: str | None, include_profile: bool, season: str | None) -> str:
    vk = f"{DRESSIFYE_CONTEXT_CACHE_PREFIX}:v:{user_id}"
    try:
        ver = int(cache.get(vk) or 0)
    except (TypeError, ValueError):
        ver = 0
    raw = f"{user_id}|v{ver}|{occasion or ''}|{include_profile}|{season or ''}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{DRESSIFYE_CONTEXT_CACHE_PREFIX}:{user_id}:{h}"


def _fetch_from_garment_core(user_id: str) -> list[dict[str, Any]]:
    """
    garment-core API'den tüm izin verilen tenant'lar için gardırop çeker.
    GARMENT_CORE_API_URL/KEY yoksa boş döner — sistem mock'a düşer.
    """
    from django.conf import settings as _settings
    from mehlr.integrations.garment_core_context_source import fetch_garments_from_core

    tenant_slugs: list[str] = getattr(_settings, "GARMENT_CORE_TENANT_SLUGS", [])
    if not tenant_slugs:
        return []

    merged: list[dict[str, Any]] = []
    for slug in tenant_slugs:
        try:
            items = fetch_garments_from_core(slug, limit=50)
            merged.extend(items)
        except Exception as exc:
            logger.warning(
                "_fetch_from_garment_core: tenant=%s user_id=%s hata: %s", slug, user_id, exc
            )
    if merged:
        logger.info(
            "_fetch_from_garment_core: %s parça çekildi user_id=%s", len(merged), user_id
        )
    return merged


def get_dressifye_context(
    user_id: str,
    occasion: str | None = None,
    include_profile: bool = True,
    season: str | None = None,
    client: DressifyeClient | None = None,
) -> dict[str, Any]:
    """
    Dressifye gardırobunu çeker, filtreler ve prompt metnine dönüştürür.

    Returns:
        wardrobe_text: AI'ye eklenecek metin
        wardrobe_items: filtrelenmiş ham öğeler
        user_profile: Dressifye profil dict veya {}
        stats: total_items, included_items, categories, estimated_tokens
        core_context: HairInfinity + cross-tenant birleşik profil
        hair_form: yapılandırılmış saç formu alanları
        integration_text: prompt'a eklenecek \"Entegrasyon Verisi\" metni
    """
    key = _cache_key(user_id, occasion, include_profile, season)
    cached = cache.get(key)
    if cached is not None:
        result = dict(cached)
        if "metadata" not in result:
            result = {**result, "metadata": {"wardrobe_source": "unknown"}}
        _attach_core_context(user_id, result)
        return result

    cli = client or DressifyeClient()
    raw_wardrobe: list[dict[str, Any]] = []
    profile: dict[str, Any] = {}

    try:
        raw_wardrobe = cli.get_user_wardrobe(user_id)
        if include_profile:
            profile = cli.get_user_profile(user_id)
    except Exception as e:
        logger.exception("DressifyeClient gardırop/profil okunamadı user_id=%s: %s", user_id, e)
        raw_wardrobe = []
        profile = {}

    # Dressifye API boş döndüyse garment-core'dan dene
    if not raw_wardrobe:
        raw_wardrobe = _fetch_from_garment_core(user_id)

    wardrobe_source = "api" if raw_wardrobe else "mock"
    if not raw_wardrobe:
        wardrobe_source = "mock"
        logger.info(
            "Dressifye gardırop boş veya API yok; mock gardırop kullanılıyor user_id=%s",
            user_id,
        )
        raw_wardrobe = list(_MOCK_WARDROBE)

    filtered = filter_wardrobe_for_prompt(
        raw_wardrobe,
        occasion=occasion,
        season=season,
        max_items=MAX_PROMPT_WARDROBE_ITEMS,
    )
    wardrobe_text = format_wardrobe_for_prompt(
        filtered,
        total_source_count=len(raw_wardrobe),
    )

    categories = sorted({_category_bucket(g.get("category", "")) for g in filtered})

    result: dict[str, Any] = {
        "wardrobe_text": wardrobe_text,
        "wardrobe_items": filtered,
        "user_profile": profile if include_profile else {},
        "stats": {
            "total_items": len(raw_wardrobe),
            "included_items": len(filtered),
            "categories": categories,
            "estimated_tokens": len(filtered) * TOKENS_PER_ITEM_ESTIMATE,
        },
        "metadata": {
            "wardrobe_source": wardrobe_source,
        },
    }

    try:
        to_cache = {k: v for k, v in result.items() if k not in _CACHE_KEYS_STRIP}
        cache.set(key, to_cache, DRESSIFYE_CONTEXT_CACHE_TTL)
    except Exception as e:
        logger.warning("Dressifye context cache yazılamadı: %s", e)

    _attach_core_context(user_id, result)
    return result
