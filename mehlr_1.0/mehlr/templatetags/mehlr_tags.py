"""
mehlr_1.0 — Template Tags
"""
from django import template
from django.utils.safestring import mark_safe
from mehlr.utils import markdown_to_html as _markdown_to_html
from mehlr.prompts.project_prompts import PROJECT_PROMPTS

register = template.Library()


def _project_meta(slug):
    if not slug:
        return {}
    return PROJECT_PROMPTS.get(slug) or PROJECT_PROMPTS.get(slug.replace("_", "-")) or {}


@register.filter
def markdown_to_html(value):
    """Markdown metnini HTML'e çevirir."""
    if not value:
        return ""
    return mark_safe(_markdown_to_html(str(value)))


@register.simple_tag
def project_display_name(project_slug):
    """{{ project.slug|project_display_name }} yerine {% project_display_name project.slug %}"""
    meta = _project_meta(project_slug)
    return meta.get("display_name", (project_slug or "").replace("_", " ").replace("-", " ").title())


@register.simple_tag
def project_capabilities(project_slug):
    """Proje capability listesini döner."""
    meta = _project_meta(project_slug)
    return meta.get("capabilities", [])


@register.simple_tag
def project_domain(project_slug):
    meta = _project_meta(project_slug)
    return meta.get("domain", "")


@register.simple_tag
def project_report_types(project_slug):
    meta = _project_meta(project_slug)
    return meta.get("analytics_config", {}).get("report_types", [])


@register.filter
def capability_label(capability_key):
    """'outfit_recommendation' → 'Outfit Recommendation'"""
    return (capability_key or "").replace("_", " ").title()


@register.filter
def confidence_color(score):
    """'YÜKSEK' → 'text-green-600'"""
    mapping = {"YÜKSEK": "text-green-600", "ORTA": "text-yellow-500", "DÜŞÜK": "text-red-500"}
    return mapping.get((score or "").upper(), "text-gray-400")


@register.filter
def quality_badge(score):
    """score: int 0-100 → Tailwind renk sınıfı"""
    try:
        s = int(score)
    except (TypeError, ValueError):
        return "bg-gray-100 text-gray-800"
    if s >= 80:
        return "bg-green-100 text-green-800"
    if s >= 60:
        return "bg-yellow-100 text-yellow-800"
    return "bg-red-100 text-red-800"


@register.inclusion_tag("mehlr/components/project_selector.html")
def project_selector(projects, active_slug=""):
    """{% project_selector projects active_slug=project.slug %}"""
    projects_with_meta = []
    for p in projects:
        slug = getattr(p, "slug", str(p))
        meta = _project_meta(slug)
        projects_with_meta.append({
            "project": p,
            "display_name": meta.get("display_name", getattr(p, "name", slug)),
            "domain": meta.get("domain", ""),
            "is_active": slug == active_slug,
        })
    return {"projects_with_meta": projects_with_meta, "active_slug": active_slug, "projects": projects}
