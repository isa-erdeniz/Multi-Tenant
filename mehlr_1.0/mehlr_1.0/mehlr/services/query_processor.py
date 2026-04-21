"""
Doğal dil sorgu işleme — sorgu tipi, proje ve niyet tespiti.
"""
import re
from mehlr.prompts.project_prompts import PROJECT_CONTEXTS

# Sorgu sınıfları
QUERY_ANALYSIS = 'analysis'
QUERY_REPORT = 'report'
QUERY_QUESTION = 'question'
QUERY_ACTION = 'action'
QUERY_GENERAL = 'general'

# Proje adı → slug eşlemesi
PROJECT_ALIASES = {
    'looopone': ['looopone', 'atık', 'çöp', 'konteyner', 'belediye'],
    'worktrackere': ['worktrackere', 'worktracker', 'randevu', 'salon', 'kuaför'],
    'garment_core': ['garment', 'core', 'kıyafet', 'moda', 'e-ticaret'],
    'hairinfinitye': ['hairinfinitye', 'saç', 'bakım', 'hair'],
    'edulingoe': ['edulingoe', 'dil', 'öğrenme', 'edu'],
    'stylecoree': ['stylecoree', 'tasarım', 'stüdyo', 'style'],
    'drivetrackere': ['drivetrackere', 'araç', 'bakım', 'drive', 'km'],
}


def classify_query(query):
    """
    Sorgu tipini belirler: analiz, rapor, soru, aksiyon veya genel.
    """
    if not query or not query.strip():
        return QUERY_GENERAL
    q = query.lower().strip()
    if any(w in q for w in ['analiz', 'analiz et', 'incele', 'trend', 'durum', 'nasıl']):
        return QUERY_ANALYSIS
    if any(w in q for w in ['rapor', 'özet', 'günlük', 'haftalık', 'aylık', 'report']):
        return QUERY_REPORT
    if any(w in q for w in ['ne yapmalı', 'öner', 'tavsiye', 'aksiyon', 'yapılmalı']):
        return QUERY_ACTION
    if any(w in q for w in ['kaç', 'ne kadar', 'kim', 'hangi', '?', 'mi ', 'mı ']):
        return QUERY_QUESTION
    return QUERY_GENERAL


def extract_project(query):
    """
    Sorgu metninden hangi projeye atıf yapıldığını bulur.
    Proje slug'ı veya None (genel) döner.
    """
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
    """
    Kullanıcı niyetini tespit eder: analiz / rapor / bilgi / öneri / genel.
    """
    query_type = classify_query(query)
    project = extract_project(query)
    return {
        'type': query_type,
        'project': project,
        'is_cross_project': 'genel' in (query or '').lower() or 'tüm proje' in (query or '').lower(),
    }
