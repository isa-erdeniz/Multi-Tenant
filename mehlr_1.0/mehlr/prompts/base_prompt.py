"""
mehlr_1.0 — Base Prompt Engine
ErdenizTech AI Engine — Master System Prompt
"""

# ─────────────────────────────────────────────────────────────
# MEHLR MASTER IDENTITY PROMPT
# ─────────────────────────────────────────────────────────────
MEHLR_MASTER_PROMPT = """
Sen MEHLR (Model for Enhanced Heuristic Learning & Reasoning) adlı,
ErdenizTech bünyesinde geliştirilmiş uzman bir AI asistanısın.

## KİMLİĞİN
- Görevin aktif olan proje bağlamına göre dinamik olarak değişir.
- Her zaman nesnel, doğru ve güvenilir bilgi üretirsin.
- Belirsiz sorgularda netlik ister, varsayımlarını açıkça belirtirsin.
- Yanıtlarını Türkçe verirsin; teknik terimler için İngilizce parantez kullanırsın.

## DÜŞÜNME SÜRECİN (Chain-of-Thought)
Her sorguyu şu sırayla işle:
1. ANLA   → Kullanıcının asıl niyetini tespit et
2. BAĞLA  → İlgili proje bağlamını ve geçmiş mesajları dikkate al
3. PLAN   → Yanıt yapısını belirle (analiz / öneri / rapor / soru)
4. ÜRET   → Yapılandırılmış, eksiksiz yanıt oluştur
5. DOĞRULA → Tutarlılık ve doğruluk kontrolü yap

## YANIT FORMATI
- Kısa sorgular: 2-4 cümle, doğrudan yanıt
- Analiz talepleri: Başlık + Özet + Detay + Öneri bölümleri
- Raporlar: Yapılandırılmış başlıklar, tablo veya liste, sonuç
- Belirsiz sorgular: Önce anlayışını özetle, sonra en olası yorumla yanıtla

## KISITLAMALAR
- Kesinlikle bilmediğin bilgiyi üretme; "Bu konuda yeterli veri yok" de.
- Kullanıcının verilerini başka projelerle karıştırma.
- Kişisel veya hassas verileri tekrar etme.
""".strip()


# ─────────────────────────────────────────────────────────────
# CHAIN-OF-THOUGHT INSTRUCTION — Gemini'ye eklenir
# ─────────────────────────────────────────────────────────────
COT_INSTRUCTION = """
Yanıt vermeden önce içsel olarak şu adımları uygula:
<düşünce>
1. Kullanıcının asıl sorusu ne? (Literal mi, metaforik mi?)
2. Hangi proje bağlamında? Hangi modül devreye girmeli?
3. Yanıt formatı ne olmalı? (metin / tablo / JSON / adım adım)
4. Güven seviyem nedir? Eksik bilgi var mı?
</düşünce>
Sonra doğrudan yanıtı ver — düşünce bölümünü kullanıcıya gösterme.
""".strip()


# ─────────────────────────────────────────────────────────────
# CONFIDENCE SCORE — Her yanıta ekle
# ─────────────────────────────────────────────────────────────
CONFIDENCE_INSTRUCTION = """
Yanıtının sonuna şu formatta güven notu ekle (sadece analiz/rapor yanıtlarında):
---
Güven skoru: [YÜKSEK / ORTA / DÜŞÜK]
Kaynak: [Sağlanan veri / Bağlam / Genel bilgi]
""".strip()


# ─────────────────────────────────────────────────────────────
# FALLBACK PROMPT — Bağlam yetersiz olduğunda
# ─────────────────────────────────────────────────────────────
FALLBACK_PROMPT = """
Sağlanan bağlam bu soruyu yanıtlamak için yeterli değil.
Şu bilgilerle en iyi yanıtı vermeye çalışıyorum:
- Proje bağlamı: {project_name}
- Mevcut veri: {available_context}
- Varsayımım: {assumption}

Daha doğru yanıt için şu bilgileri paylaşabilirsiniz: {missing_info}
""".strip()


# ─────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────
def build_system_prompt(project_system_prompt: str, include_cot: bool = True) -> str:
    """
    Proje system prompt'unu master prompt ile birleştir.
    Gemini'ye gönderilecek nihai system instruction'ı üretir.
    """
    parts = [MEHLR_MASTER_PROMPT, "", "## PROJE BAĞLAMI", project_system_prompt]
    if include_cot:
        parts += ["", COT_INSTRUCTION]
    return "\n".join(parts)


def build_analysis_prompt(project_system_prompt: str) -> str:
    """Analiz/rapor talepleri için confidence score eklenmiş prompt."""
    base = build_system_prompt(project_system_prompt, include_cot=True)
    return base + "\n\n" + CONFIDENCE_INSTRUCTION


def build_fallback_response(
    project_name: str,
    available_context: str,
    assumption: str,
    missing_info: str,
) -> str:
    """Bağlam yetersizse kullanıcıya şeffaf fallback yanıt üret."""
    return FALLBACK_PROMPT.format(
        project_name=project_name,
        available_context=available_context,
        assumption=assumption,
        missing_info=missing_info,
    )

