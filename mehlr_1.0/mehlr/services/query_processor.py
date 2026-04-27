"""
mehlr_1.0 Query Processor — Sorgu ön işleme ve kalite kontrolü
"""
import re

MAX_QUERY_LENGTH = 2000

# Eski API (testler için)
QUERY_ANALYSIS = "analysis"
QUERY_REPORT = "report"
QUERY_QUESTION = "question"
QUERY_ACTION = "action"
QUERY_GENERAL = "general"

PROJECT_ALIASES = {
    "looopone": ["looopone", "atık", "çöp", "konteyner", "belediye"],
    "worktrackere": ["worktrackere", "worktracker", "randevu", "salon", "kuaför"],
    "dressifye_saas": ["garment", "core", "kıyafet", "moda", "e-ticaret"],
    "dressifye-saas": ["garment", "core", "kıyafet", "moda", "e-ticaret"],
    "hairinfinitye": ["hairinfinitye", "saç", "bakım", "hair"],
    "edulingoe": ["edulingoe", "dil", "öğrenme", "edu"],
    "stylecoree": ["stylecoree", "tasarım", "stüdyo", "style"],
    "drivetrackere": ["drivetrackere", "araç", "bakım", "drive", "km"],
}


def preprocess_query(raw_query: str) -> dict:
    """
    Kullanıcı sorgusunu temizle ve zenginleştir.
    Döner: {"query": str, "is_analysis": bool, "language": str, "warnings": list}
    """
    query = (raw_query or "").strip()
    warnings = []

    if len(query) > MAX_QUERY_LENGTH:
        query = query[:MAX_QUERY_LENGTH]
        warnings.append("Sorgu kısaltıldı (maksimum uzunluk aşıldı).")

    if not query:
        return {
            "query": "",
            "is_analysis": False,
            "language": "tr",
            "warnings": ["Boş sorgu."],
        }

    analysis_keywords = [
        "analiz", "rapor", "karşılaştır", "özet", "değerlendir",
        "incele", "istatistik", "trend", "tahmin", "forecast",
    ]
    is_analysis = any(kw in query.lower() for kw in analysis_keywords)
    language = "tr" if _is_turkish(query) else "en"

    return {
        "query": query,
        "is_analysis": is_analysis,
        "language": language,
        "warnings": warnings,
    }


def rewrite_query(query: str, project_key: str) -> str:
    if len(query.strip()) <= 10:
        from mehlr.prompts.project_prompts import PROJECT_PROMPTS
        meta = PROJECT_PROMPTS.get(project_key, {})
        project_name = meta.get("display_name") or meta.get("name", "")
        if project_name:
            return f"{project_name} hakkında: {query.strip()}"
    return query


def validate_response(response_text: str) -> dict:
    """
    AI yanıtının kalite kontrolü.
    Döner: {"valid": bool, "issues": list, "score": int (0-100)}
    """
    issues = []
    score = 100

    if not response_text or len(response_text.strip()) < 20:
        issues.append("Yanıt çok kısa veya boş.")
        score -= 50

    if len(response_text) > 10000:
        issues.append("Yanıt aşırı uzun.")
        score -= 10

    error_patterns = [
        r"hata oluştu",
        r"yanıt üretemiyorum",
        r"bilinmiyor",
        r"error",
    ]
    for pattern in error_patterns:
        if re.search(pattern, (response_text or "").lower()):
            issues.append(f"Yanıt hata içeriyor: '{pattern}'")
            score -= 20

    return {
        "valid": score >= 60,
        "issues": issues,
        "score": max(0, score),
    }


def _is_turkish(text: str) -> bool:
    """Basit Türkçe karakter kontrolü."""
    turkish_chars = set("çğıöşüÇĞİÖŞÜ")
    return bool(set(text) & turkish_chars)


# ---------- Eski API (testler için) ----------


def classify_query(query):
    """Sorgu tipini belirler: analiz, rapor, soru, aksiyon veya genel."""
    if not query or not query.strip():
        return QUERY_GENERAL
    q = query.lower().strip()
    if any(w in q for w in ["analiz", "analiz et", "incele", "trend", "durum", "nasıl"]):
        return QUERY_ANALYSIS
    if any(w in q for w in ["rapor", "özet", "günlük", "haftalık", "aylık", "report"]):
        return QUERY_REPORT
    if any(w in q for w in ["ne yapmalı", "öner", "tavsiye", "aksiyon", "yapılmalı"]):
        return QUERY_ACTION
    if any(w in q for w in ["kaç", "ne kadar", "kim", "hangi", "?", "mi ", "mı "]):
        return QUERY_QUESTION
    return QUERY_GENERAL


def extract_project(query):
    """Sorgu metninden hangi projeye atıf yapıldığını bulur."""
    if not query or not query.strip():
        return None
    q = query.lower().strip()
    for slug, aliases in PROJECT_ALIASES.items():
        if slug in q:
            return slug
        for a in aliases:
            if a in q:
                return slug
    return None


def detect_intent(query):
    """Kullanıcı niyetini tespit eder."""
    query_type = classify_query(query)
    project = extract_project(query)
    return {
        "type": query_type,
        "project": project,
        "is_cross_project": "genel" in (query or "").lower()
        or "tüm proje" in (query or "").lower(),
    }
