"""
Gardırop yardımcı fonksiyonları — AI kombin önerisi vb.
"""
import json
import logging
import re

logger = logging.getLogger(__name__)

OCCASION_CHOICES = [
    ("gunluk", "Günlük"),
    ("is", "İş"),
    ("gece", "Gece"),
    ("spor", "Spor"),
    ("ozel", "Özel Gün"),
]


def _build_wardrobe_list(garments):
    """Garment queryset'i AI için liste formatına çevir."""
    items = []
    for g in garments:
        cat_name = g.category.name if g.category else (g.get_subcategory_display() if g.subcategory else "Belirtilmemiş")
        items.append({
            "id": g.id,
            "name": g.name,
            "category": cat_name,
            "subcategory": g.subcategory or "",
            "color": g.color or "",
            "color_hex": g.color_hex or "",
            "brand": g.brand or "",
            "season": g.get_season_display(),
        })
    return items


def generate_outfit_suggestions(user, weather_data=None):
    """
    Kullanıcının gardırobundaki parçalardan renk ve tarz uyumuna göre 3 kombin öner.

    Args:
        user: Kullanıcı
        weather_data: get_weather_data()'dan dönen dict veya metin.
            dict ise: temp, condition, is_rainy kullanılır.

    Returns:
        list: [{"garments": [Garment, ...], "stil_notu": str}, ...]
    """
    return suggest_outfits(user, occasion="gunluk", weather_data=weather_data)


def suggest_outfits(user, occasion, weather_data=None):
    """
    Kullanıcının gardırobundan AI ile 3 farklı kombin öner.

    Args:
        user: Kullanıcı
        occasion: Etkinlik (gunluk, is, gece, spor, ozel)
        weather_data: get_weather_data() dict, veya metin. Dict ise temp/condition/is_rainy kullanılır.

    Returns:
        list: [{"garments": [Garment, ...], "stil_notu": str}, ...]
        veya boş liste (hata / yetersiz gardırop)
    """
    from apps.core.tenant_context import use_tenant

    tenant = getattr(user, "tenant", None)
    if tenant is None:
        logger.info("suggest_outfits: kullanıcı tenant yok")
        return []
    with use_tenant(tenant):
        return _suggest_outfits_scoped(user, occasion, weather_data)


def _suggest_outfits_scoped(user, occasion, weather_data=None):
    from django.conf import settings
    from apps.wardrobe.models import Garment
    from apps.core.clients.mehlr_client import MEHLRClient

    garments = list(
        Garment.objects.filter(user=user, is_active=True)
        .select_related("category")
        .order_by("category__order", "subcategory", "name")
    )

    if len(garments) < 2:
        logger.info("Gardırop yetersiz, kombin önerilemez")
        return []

    wardrobe_list = _build_wardrobe_list(garments)
    occasion_labels = dict(OCCASION_CHOICES)
    occasion_label = occasion_labels.get(occasion, occasion)

    # Hava durumu prompt parçası + mantıksal kurallar
    weather_prompt = ""
    temp = None
    is_rainy = False
    require_dis = False

    if weather_data:
        if isinstance(weather_data, dict):
            temp = weather_data.get("temp")
            condition = weather_data.get("condition", "")
            is_rainy = weather_data.get("is_rainy", False)
            if temp is not None and condition:
                weather_prompt = f"""Şu an hava {temp}°C ve {condition}. Bu hava koşullarına uygun, kullanıcıyı üşütmeyecek veya terletmeyecek 3 kombin öner.
"""
                require_dis = temp is not None and float(temp) < 10
        else:
            weather_prompt = f"Hava Durumu: {weather_data}\n\n"

    # Mantıksal kontroller: temp < 10 → dis zorunlu, yağmurlu → su geçirmeyen ayakkabı
    rules = []
    if require_dis:
        rules.append("- dis (dış giyim: mont, kaban, hırka vb.) ZORUNLU — her kombinde mutlaka olmalı.")
    if is_rainy:
        rules.append("- ayakkabi seçiminde su geçirmeyen / yağmura dayanıklı ayakkabıları önceliklendir.")
    rules_text = "\n".join(rules) if rules else ""

    prompt = f"""Kullanıcının gardırobunda şu parçalar var (id ile referans ver):

{json.dumps(wardrobe_list, ensure_ascii=False, indent=2)}

Etkinlik: {occasion_label}
{f'{weather_prompt}' if weather_prompt else ''}{f'ÖNEMLİ KURALLAR:\n{rules_text}\n\n' if rules_text else ''}Bu parçalardan oluşan TAM OLARAK 3 farklı kombin öner.
Her kombin şu formatta olsun:
- ust: üst giyim parçasının id'si (gömlek, tişört, bluz, kazak vb.)
- alt: alt giyim parçasının id'si (pantolon, etek, şort vb.)
- dis: dış giyim id'si (varsa, yoksa null)
- ayakkabi: ayakkabı id'si (varsa, yoksa null)
- aksesuar: aksesuar id'si (varsa, yoksa null)
- stil_notu: Bu kombin için 1 cümle stil önerisi

SADECE aşağıdaki JSON formatında yanıt ver, başka metin ekleme:
[
  {{"ust": <id>, "alt": <id>, "dis": null, "ayakkabi": null, "aksesuar": null, "stil_notu": "..."}},
  ...
]"""

    client = MEHLRClient()
    result = client.analyze(
        project=settings.MEHLR_PROJECT,
        prompt=prompt,
        context={
            "task": "outfit_suggestion",
            "user_id": user.id,
            "occasion": occasion,
            "garment_count": len(garments),
        },
    )

    if not result.get("success"):
        logger.warning(f"MEHLR outfit önerisi başarısız: {result.get('error', result.get('reason', 'unknown'))}")
        return _fallback_outfits(garments, weather_data=weather_data)

    raw = result["data"].get("response", "")

    # JSON parse
    try:
        suggestions = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"\[[\s\S]*?\]", raw)
        if match:
            try:
                suggestions = json.loads(match.group())
            except json.JSONDecodeError:
                suggestions = None
        else:
            suggestions = None

    if not suggestions or not isinstance(suggestions, list):
        return _fallback_outfits(garments, weather_data=weather_data)

    # Map IDs to Garment objects
    id_to_garment = {g.id: g for g in garments}
    outfits = []

    for sug in suggestions[:3]:
        if not isinstance(sug, dict):
            continue
        ids = [
            sug.get("ust"),
            sug.get("alt"),
            sug.get("dis"),
            sug.get("ayakkabi"),
            sug.get("aksesuar"),
        ]
        ids = [i for i in ids if i is not None]
        garments_in = [id_to_garment[i] for i in ids if i in id_to_garment]
        garments_in = list(dict.fromkeys(garments_in))  # dedupe

        if garments_in:
            outfits.append({
                "garments": garments_in,
                "stil_notu": sug.get("stil_notu", ""),
            })

    return outfits if outfits else _fallback_outfits(garments, weather_data=weather_data)


def _fallback_outfits(garments, weather_data=None):
    """MEHLR yanıt veremezse basit eşleştirme ile 1-2 kombin üret."""
    def _get_key(g):
        if g.subcategory:
            return g.subcategory
        if g.category:
            return g.category.slug
        return "diger"

    by_key = {}
    for g in garments:
        by_key.setdefault(_get_key(g), []).append(g)

    ust = (by_key.get("ust") or by_key.get("ust-giyim") or [])[:2]
    alt = (by_key.get("alt") or by_key.get("alt-giyim") or [])[:2]
    dis = (by_key.get("dis") or by_key.get("dis-giyim") or [])[:1]
    ayakkabi = (by_key.get("ayakkabi") or [])[:1]
    aksesuar = (by_key.get("aksesuar") or [])[:1]
    elbise = (by_key.get("elbise") or [])[:2]

    # Hava durumuna göre: temp < 10 → dis zorunlu
    require_dis = False
    if weather_data and isinstance(weather_data, dict):
        temp = weather_data.get("temp")
        if temp is not None and float(temp) < 10:
            require_dis = True

    fallbacks = []
    # Elbise tek başına kombin olabilir
    for e in elbise[:2]:
        parts = [e]
        if require_dis and dis:
            parts.append(dis[0])
        if ayakkabi:
            parts.append(ayakkabi[0])
        if aksesuar:
            parts.append(aksesuar[0])
        fallbacks.append({"garments": parts, "stil_notu": "Gardırobunuzdan seçilmiş kombin."})

    for i, u in enumerate(ust):
        if len(fallbacks) >= 3:
            break
        a = alt[i % len(alt)] if alt else None
        parts = [u]
        if a:
            parts.append(a)
        if dis:
            parts.append(dis[0])
        if ayakkabi and ayakkabi[0] not in parts:
            parts.append(ayakkabi[0])
        if aksesuar and aksesuar[0] not in parts:
            parts.append(aksesuar[0])
        if len(parts) >= 2:
            fallbacks.append({"garments": parts, "stil_notu": "Gardırobunuzdan seçilmiş kombin."})

    return fallbacks[:3]
