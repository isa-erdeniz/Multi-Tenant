from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Şablon içinde sözlükten integer key ile değer almak için."""
    if dictionary is None:
        return None
    try:
        k = int(key) if key is not None else key
        return dictionary.get(k)
    except (ValueError, TypeError):
        return dictionary.get(key)
