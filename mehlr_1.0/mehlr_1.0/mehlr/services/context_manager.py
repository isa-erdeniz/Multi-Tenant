"""
Proje bağlam yönetimi — AI'a verilecek bağlam bilgisini hazırlar.
"""
from mehlr.models import Project
from django.conf import settings
from mehlr.prompts.project_prompts import PROJECT_CONTEXTS


def get_project_context(project_slug=None):
    """
    Proje slug'ına göre AI bağlam metnini döndürür.
    project_slug None veya 'general' ise genel bağlam döner.
    """
    if not project_slug or project_slug == 'general':
        return PROJECT_CONTEXTS.get('general', '')
    slug = project_slug.lower().strip()
    if slug in PROJECT_CONTEXTS:
        return PROJECT_CONTEXTS[slug]
    try:
        p = Project.objects.get(slug=slug, is_active=True)
        return p.context_prompt or PROJECT_CONTEXTS.get('general', '')
    except Project.DoesNotExist:
        return PROJECT_CONTEXTS.get('general', '')


def enrich_context(project_slug, user_query):
    """
    Sorguya göre bağlamı zenginleştirir (ileride sorgu tipine göre ek bilgi eklenebilir).
    """
    base = get_project_context(project_slug)
    return base


def get_cross_project_context():
    """
    Tüm aktif projelerin özet bağlamını döndürür.
    """
    parts = [PROJECT_CONTEXTS.get('general', '')]
    for p in Project.objects.filter(is_active=True).order_by('name'):
        parts.append(f"- {p.name} ({p.slug}): {p.description[:100]}...")
    return '\n'.join(parts)
