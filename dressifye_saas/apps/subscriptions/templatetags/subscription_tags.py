from django import template

from apps.subscriptions.services import can_use_feature, get_remaining

register = template.Library()


@register.simple_tag(takes_context=True)
def can_use(context, feature_type):
    request = context.get("request")
    if not request or not request.user.is_authenticated:
        return False
    return can_use_feature(request.user, feature_type)


@register.simple_tag(takes_context=True)
def usage_remaining(context, feature_type):
    request = context.get("request")
    if not request or not request.user.is_authenticated:
        return None
    return get_remaining(request.user, feature_type)
