"""
MEHLR custom template tag'leri.
"""
from django import template
from django.utils.safestring import mark_safe
from mehlr.utils import markdown_to_html as _markdown_to_html

register = template.Library()


@register.filter
def markdown_to_html(value):
    """Markdown metnini HTML'e çevirir (güvenli render için safe ile kullanın)."""
    if not value:
        return ""
    return mark_safe(_markdown_to_html(str(value)))
