"""
mehlr_1.0 AI Motor Servisi — Google Gemini API (google-genai SDK).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("mehlr")

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None
    logger.warning("google-genai paketi bulunamadı.")

MEHLR_CONFIG = getattr(settings, "MEHLR_CONFIG", {})
PRIMARY_MODEL = MEHLR_CONFIG.get("PRIMARY_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = MEHLR_CONFIG.get("FALLBACK_MODEL", "gemini-2.5-flash")
MAX_TOKENS = MEHLR_CONFIG.get("MAX_TOKENS", 4096)
TEMPERATURE = MEHLR_CONFIG.get("TEMPERATURE", 0.7)
CACHE_TTL = MEHLR_CONFIG.get("CACHE_TTL", 300)
RATE_LIMIT = MEHLR_CONFIG.get("RATE_LIMIT_PER_MINUTE", 15)
MAX_HISTORY = MEHLR_CONFIG.get("MAX_CONVERSATION_HISTORY", 20)


def _get_client():
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY tanımlı değil.")
    http_options = types.HttpOptions(timeout=30_000)  # 30 saniye (ms)
    return genai.Client(api_key=api_key, http_options=http_options)


def query_ai(project_key, user_message, conversation_history=None,
             is_analysis=False, system_prompt=None):
    """
    Gemini'ye istek gönderir.
    Döner: {"response": str, "confidence": str, "tokens_used": int, "error": str|None}
    """
    if not GENAI_AVAILABLE:
        return {"response": "", "confidence": "DÜŞÜK", "tokens_used": 0,
                "error": "google-genai paketi yüklü değil."}

    from mehlr.prompts.base_prompt import build_system_prompt, build_analysis_prompt
    from mehlr.prompts.project_prompts import PROJECT_PROMPTS

    meta = PROJECT_PROMPTS.get(project_key, {})
    project_system = meta.get("system_prompt", "")

    if system_prompt:
        full_system = system_prompt
    elif is_analysis:
        full_system = build_analysis_prompt(project_system)
    else:
        full_system = build_system_prompt(project_system)

    # Geçmiş mesajları formatla
    history = conversation_history or []
    contents = []
    for msg in list(history)[-MAX_HISTORY:]:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append(types.Content(
            role=role,
            parts=[types.Part(text=msg.get("content", ""))]
        ))
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=user_message)]
    ))

    config = types.GenerateContentConfig(
        system_instruction=full_system,
        max_output_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=contents,
            config=config,
        )
        text = response.text or ""
        tokens = getattr(response.usage_metadata, "total_token_count", 0) or 0
        confidence = _extract_confidence(text)
        return {"response": text, "confidence": confidence,
                "tokens_used": tokens, "error": None}

    except Exception as e:
        err_str = str(e).lower()
        if "timeout" in err_str or "deadline" in err_str:
            logger.warning(f"query_ai timeout: {e}")
            return {
                "response": "Yanıt süresi aşıldı, lütfen tekrar deneyin.",
                "confidence": "DÜŞÜK",
                "tokens_used": 0,
                "error": "timeout",
            }
        logger.error(f"query_ai primary failed: {e}")
        return _fallback_query(contents, config, str(e))


def _fallback_query(contents, config, original_error):
    try:
        client = _get_client()
        fallback_config = types.GenerateContentConfig(
            system_instruction=getattr(config, "system_instruction", None),
            max_output_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        response = client.models.generate_content(
            model=FALLBACK_MODEL,
            contents=contents,
            config=fallback_config,
        )
        text = response.text or ""
        tokens = getattr(response.usage_metadata, "total_token_count", 0) or 0
        logger.info("Fallback model kullanıldı.")
        return {"response": text, "confidence": "ORTA",
                "tokens_used": tokens, "error": None}
    except Exception as e:
        err_str = str(e).lower()
        if "timeout" in err_str or "deadline" in err_str:
            return {"response": "Yanıt süresi aşıldı, lütfen tekrar deneyin.",
                    "confidence": "DÜŞÜK", "tokens_used": 0,
                    "error": "timeout"}
        logger.error(f"Fallback da başarısız: {e}")
        return {"response": "Şu an yanıt üretemiyorum, lütfen tekrar deneyin.",
                "confidence": "DÜŞÜK", "tokens_used": 0,
                "error": str(e)}


def _build_wardrobe_analysis_prompt(
    wardrobe_context: dict[str, Any],
    user_query: str | None = None,
) -> str:
    """
    Gardırop analizi için zengin kullanıcı mesajı (tek JSON çıktısı hedeflenir).

    İçerik: trend / stil profili / renk paleti / kombin potansiyeli / alışveriş listesi / bakım.
    """
    prefix = _tenant_ai_prefix()
    wt = str(wardrobe_context.get("wardrobe_text") or "")
    stats = wardrobe_context.get("stats") or {}
    prof = wardrobe_context.get("user_profile") or {}
    extra = ""
    if user_query and str(user_query).strip():
        extra = f"\nKullanıcının ek sorusu: {user_query.strip()}\n"

    integ = str(wardrobe_context.get("integration_text") or "").strip()
    integ_block = f"\n---\n{integ}\n" if integ else ""

    schema_hint = """
Yanıtı YALNIZCA geçerli tek bir JSON nesnesi olarak ver; markdown veya açıklama metni ekleme.
Şema (alanları mümkün olduğunca doldur):
{
  "wardrobe_summary": {
    "total_items": <sayı>,
    "top_categories": ["..."],
    "dominant_colors": ["..."],
    "style_profile": "ör. Minimalist-Klasik karışımı"
  },
  "trend_gaps": ["Bu sezon eksik veya trend uyumsuzlukları"],
  "outfit_suggestions": [
    {"name": "Kombin adı", "items": ["ID:...", "ID:..."], "description": "..."}
  ],
  "shopping_list": [
    {"priority": 1, "item": "...", "reason": "..."}
  ],
  "color_analysis": {
    "current_palette": ["#HEX veya renk adı"],
    "missing_basics": ["..."],
    "suggested_accent": "..."
  },
  "care_and_season": ["Mevsim geçişi / bakım önerileri"],
  "combination_potential": "Mevcut parçalarla tahmini kombin çeşitliliği (kısa metin)"
}
"""
    return (
        prefix
        + "Sen profesyonel bir stil analisti ve gardırop danışmanısın. Türkçe yanıt ver.\n"
        "Aşağıdaki gardırop verisini ve istatistikleri kullanarak detaylı analiz üret.\n"
        "1) Trend ve mevsim eksikleri  2) Stil profili (minimalist/klasik/spor vb.)  "
        "3) Renk paleti ve eksik temel renkler  4) Kombin potansiyeli  "
        "5) Öncelikli alışveriş listesi (en fazla 5 kalem)  6) Bakım ve mevsim geçişi\n"
        f"{schema_hint}\n"
        "---\n"
        f"İstatistik özeti: {stats}\n"
        f"Profil (varsa): {prof}\n"
        "---\n"
        f"{wt}"
        f"{integ_block}"
        f"{extra}"
    )


def _extract_confidence(text):
    text_upper = text.upper()
    if "YÜKSEK" in text_upper or "HIGH" in text_upper:
        return "YÜKSEK"
    if "ORTA" in text_upper or "MEDIUM" in text_upper:
        return "ORTA"
    if "DÜŞÜK" in text_upper or "LOW" in text_upper:
        return "DÜŞÜK"
    return "ORTA"


def _generate_dressifye_content(system_instruction: str, user_text: str) -> tuple[str, int, str | None]:
    """
    Tek tur Dressifye isteği (Gemini). Döner: (metin, token, hata).
    """
    if not GENAI_AVAILABLE:
        return "", 0, "google-genai paketi yüklü değil."

    try:
        client = _get_client()
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=user_text)],
            )
        ]
        temp = _tenant_ai_temperature()
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=MAX_TOKENS,
            temperature=temp,
        )
        response = client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=contents,
            config=config,
        )
        text = response.text or ""
        tokens = getattr(response.usage_metadata, "total_token_count", 0) or 0
        return text, tokens, None
    except Exception as e:
        logger.error("Dressifye Gemini çağrısı başarısız: %s", e)
        err_str = str(e).lower()
        if "timeout" in err_str or "deadline" in err_str:
            return "", 0, "timeout"
        return "", 0, str(e)


def _tenant_ai_prefix() -> str:
    try:
        from apps.tenant.middleware import get_current_tenant

        t = get_current_tenant()
        if t and getattr(t, "ai_prompt_prefix", None):
            return str(t.ai_prompt_prefix).strip() + "\n\n"
    except Exception:
        pass
    return ""


def _tenant_ai_temperature() -> float:
    try:
        from apps.tenant.middleware import get_current_tenant

        t = get_current_tenant()
        if t is not None and hasattr(t, "ai_temperature"):
            return float(t.ai_temperature)
    except Exception:
        pass
    return float(TEMPERATURE)


def _build_dressifye_prompt(
    user_query: str,
    wardrobe_context: dict[str, Any] | None,
    conversation_history: list[dict[str, Any]] | None,
) -> tuple[str, str]:
    """
    System + kullanıcı mesajını üretir (dressifye system prompt + gardırop + soru).
    Döner: (system_instruction, user_message)
    """
    from mehlr.prompts.project_prompts import PROJECT_PROMPTS

    meta = PROJECT_PROMPTS.get("dressifye", {})
    base_system = _tenant_ai_prefix() + meta.get(
        "system_prompt",
        "Sen Dressifye AI stil danışmanısın. Türkçe yanıt ver.",
    )

    wardrobe_block = ""
    if wardrobe_context is None:
        wardrobe_source = "none"
    else:
        meta_src = (wardrobe_context or {}).get("metadata") or {}
        wardrobe_source = meta_src.get("wardrobe_source", "api")

    if wardrobe_context and wardrobe_context.get("wardrobe_text"):
        wardrobe_block = "\n\n---\n" + str(wardrobe_context["wardrobe_text"])
    else:
        wardrobe_block = "\n\n---\n(Gardırop metni yok.)"

    integ = str((wardrobe_context or {}).get("integration_text") or "").strip()
    if integ:
        wardrobe_block += "\n\n---\n" + integ

    if wardrobe_source == "mock":
        wardrobe_block += (
            "\n\nÖNEMLİ: Kullanıcının gerçek gardırop API verisine şu an erişilemedi veya gardırop boş. "
            "Gardırobunuzu görüntüleyemiyorum; genel kombin ve stil önerisi sun. "
            "Var olmayan gardırop ID'leri uydurma; kullanıcıya durumu kısaca belirt."
        )

    history_str = ""
    if conversation_history:
        for msg in list(conversation_history)[-6:]:
            role = msg.get("role", "?")
            content = str(msg.get("content", ""))[:400]
            history_str += f"{role}: {content}\n"

    system_full = base_system + wardrobe_block + (
        "\n\nYanıtın yalnızca geçerli JSON olmalı; markdown kod bloğu kullanma veya tek bir JSON nesnesi olarak ver."
    )

    user_msg = f"Kullanıcı sorusu:\n{user_query.strip()}\n"
    if history_str:
        user_msg += f"\nKonuşma geçmişi (özet):\n{history_str}"

    return system_full, user_msg


def _extract_json_text(raw_response: str) -> str:
    """Markdown ```json ... ``` veya ham { ... } çıkarır."""
    text = (raw_response or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    if text.startswith("{") or text.startswith("["):
        return text
    m2 = re.search(r"(\{[\s\S]*\})\s*$", text)
    if m2:
        return m2.group(1).strip()
    return text


def _parse_dressifye_response(raw_response: str) -> dict[str, Any]:
    """Gemini çıktısını PROJECT_PROMPTS dressifye şemasına yaklaştırır."""
    fallback: dict[str, Any] = {
        "outfit_recommendation": {
            "garment_ids": [],
            "description": "Yanıt JSON olarak işlenemedi.",
            "style_notes": "",
            "color_palette": [],
        },
        "missing_items": [],
        "confidence": 0.0,
        "raw_response": raw_response,
    }

    try:
        js = _extract_json_text(raw_response)
        data = json.loads(js)
    except (json.JSONDecodeError, TypeError, ValueError):
        return fallback

    if not isinstance(data, dict):
        return fallback

    outfit_wrap = data.get("outfit") or {}
    if not isinstance(outfit_wrap, dict):
        outfit_wrap = {}

    rows = outfit_wrap.get("outfit") or []
    garment_ids: list[int] = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and "garment_id" in row:
                try:
                    garment_ids.append(int(row["garment_id"]))
                except (TypeError, ValueError):
                    pass
            elif isinstance(row, (int, str)):
                try:
                    garment_ids.append(int(row))
                except (TypeError, ValueError):
                    pass

    desc = str(data.get("response") or outfit_wrap.get("description") or "").strip()
    style_notes = str(outfit_wrap.get("style_notes") or "").strip()
    palette = outfit_wrap.get("color_palette") or []
    if not isinstance(palette, list):
        palette = []
    palette_str = [str(x) for x in palette]

    tips = outfit_wrap.get("tips") or []
    missing: list[str] = []
    if isinstance(tips, list):
        missing = [str(t) for t in tips if t]

    fit = str(outfit_wrap.get("occasion_fit") or "").lower()
    if "yüksek" in fit or "high" in fit:
        conf = 0.9
    elif "düşük" in fit or "low" in fit:
        conf = 0.4
    elif "orta" in fit or "medium" in fit:
        conf = 0.7
    else:
        conf = 0.65

    return {
        "outfit_recommendation": {
            "garment_ids": garment_ids,
            "description": desc or "Kombin önerisi",
            "style_notes": style_notes,
            "color_palette": palette_str,
        },
        "missing_items": missing,
        "confidence": conf,
        "raw_response": raw_response,
    }


def _save_recommendation(
    user_id: str,
    recommendation_data: dict[str, Any],
    conversation_id: str | None,
) -> int:
    """
    OutfitRecommendation kaydı oluşturur. conversation_id yoksa veya bulunamazsa 0.
    """
    if not conversation_id:
        return 0

    from mehlr.models import Conversation, DressifyeGarment, DressifyeUser, OutfitRecommendation

    try:
        conv = Conversation.objects.get(pk=int(conversation_id))
    except (ValueError, Conversation.DoesNotExist):
        logger.warning("Dressifye kayıt: geçersiz conversation_id=%s", conversation_id)
        return 0

    du, _ = DressifyeUser.objects.get_or_create(
        external_id=str(user_id),
        defaults={
            "username": f"user_{str(user_id)[:40]}",
        },
    )

    outfit = recommendation_data.get("outfit_recommendation") or {}
    occ = str(outfit.get("occasion") or "")[:100]
    style_notes = str(outfit.get("style_notes") or "")[:2000]
    palette = outfit.get("color_palette") or []

    desc = str(outfit.get("description") or "").strip()
    combined_notes = f"{desc}\n\n{style_notes}".strip() if desc else style_notes

    rec = OutfitRecommendation.objects.create(
        user=du,
        conversation=conv,
        occasion=occ,
        style_notes=combined_notes[:2000],
        color_palette=palette if isinstance(palette, (list, dict)) else [],
        synced_to_dressifye=False,
    )

    ids = outfit.get("garment_ids") or []
    to_add = []
    for gid in ids:
        g = DressifyeGarment.objects.filter(
            user=du,
            external_id=str(gid),
        ).first()
        if g:
            to_add.append(g)
    if to_add:
        rec.garments.set(to_add)

    return rec.pk


async def query_dressifye_ai(
    user_id: str,
    user_query: str,
    conversation_id: str | None = None,
    occasion: str | None = None,
    include_wardrobe: bool = True,
    hair_form: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Dressifye kullanıcısı için AI kombin önerisi üretir (Gemini + gardırop bağlamı).

    hair_form: HairInfinity'den gelen saç/yüz alanları (ör. sac_formu, yuz_sekli, sac_rengi);
    isteğe bağlı; gardırop bağlamındaki entegrasyon metnine birleştirilir.
    """
    from mehlr.services.context_manager import get_dressifye_context, merge_hair_form_into_wardrobe_context

    wardrobe_context: dict[str, Any] | None = None
    if include_wardrobe:
        wardrobe_context = await sync_to_async(get_dressifye_context)(
            user_id,
            occasion=occasion,
            include_profile=True,
        )
        if hair_form:
            merge_hair_form_into_wardrobe_context(wardrobe_context, hair_form)
    else:
        from mehlr.services.context_manager import (
            build_core_context,
            extract_hair_form,
            format_integration_context_for_prompt,
        )

        core = build_core_context(user_id)
        wardrobe_context = {
            "wardrobe_text": "",
            "wardrobe_items": [],
            "metadata": {"wardrobe_source": "none"},
            "stats": {},
            "core_context": core,
            "hair_form": extract_hair_form(core),
            "integration_text": format_integration_context_for_prompt(core),
        }
        if hair_form:
            merge_hair_form_into_wardrobe_context(wardrobe_context, hair_form)

    history: list[dict[str, Any]] = []
    if conversation_id:
        from mehlr.models import Conversation, Message

        def _load_history() -> list[dict[str, Any]]:
            try:
                conv = Conversation.objects.get(pk=int(conversation_id))
            except (ValueError, Conversation.DoesNotExist):
                return []
            msgs = list(
                Message.objects.filter(conversation=conv).order_by("created_at")[: MAX_HISTORY]
            )
            return [{"role": m.role, "content": m.content} for m in msgs]

        history = await sync_to_async(_load_history)()

    system_instr, user_msg = _build_dressifye_prompt(
        user_query,
        wardrobe_context if include_wardrobe else None,
        history or None,
    )

    raw_text, _tokens, err = await asyncio.to_thread(
        _generate_dressifye_content,
        system_instr,
        user_msg,
    )

    if err:
        empty = {
            "outfit_recommendation": {
                "garment_ids": [],
                "description": (
                    "Gardırobunuzu şu an işleyemiyorum veya servis hatası oluştu; "
                    "genel olarak: düz renkler, katmanlı giyim ve mevsime uygun kumaş seçimi iyi bir başlangıçtır."
                ),
                "style_notes": "",
                "color_palette": [],
            },
            "missing_items": [],
            "confidence": 0.0,
            "raw_response": raw_text or str(err),
        }
        rid = await sync_to_async(_save_recommendation)(
            user_id,
            {**empty, "outfit_recommendation": {**empty["outfit_recommendation"], "occasion": occasion or ""}},
            conversation_id,
        )
        out = {**empty, "recommendation_id": rid}
        return out

    parsed = _parse_dressifye_response(raw_text)
    parsed["outfit_recommendation"]["occasion"] = occasion or ""

    rid = await sync_to_async(_save_recommendation)(
        user_id,
        parsed,
        conversation_id,
    )
    parsed["recommendation_id"] = rid
    return parsed


def generate_response(user_message, conversation, project_slug=None):
    """
    Eski API — views.py uyumluluğu için korundu.
    Döner: (response_text, tokens_used, elapsed, error)
    """
    start = time.time()

    # Rate limit cache kontrolü (kullanıcı bazlı)
    user_id = getattr(conversation, "user_id", None) or "anon"
    cache_key = f"mehlr:rate:{user_id}"
    count = cache.get(cache_key, 0)
    if count >= RATE_LIMIT:
        return ("Dakikada izin verilen sorgu sayısına ulaştınız. Lütfen bekleyin.", 0, 0.0, "rate_limit")
    cache.set(cache_key, count + 1, timeout=60)

    # Konuşma geçmişi
    if conversation:
        msgs = list(conversation.messages.order_by("created_at"))[-MAX_HISTORY:]
        history = [{"role": m.role, "content": m.content} for m in msgs]
        # Son mesaj user ise (views'da az önce eklenen), history'den çıkar
        # çünkü query_ai zaten user_message'ı sonuna ekliyor
        if history and history[-1]["role"] == "user":
            history = history[:-1]
    else:
        history = []

    result = query_ai(
        project_key=project_slug or "general",
        user_message=user_message,
        conversation_history=history,
    )

    elapsed = round(time.time() - start, 2)
    return (
        result["response"],
        result["tokens_used"],
        elapsed,
        result["error"],
    )
