"""FAZ 6: Fotoğraf Düzenleme Modülü."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

from apps.analytics.services import record_usage_event
from apps.subscriptions.models import FeatureUsage
from apps.subscriptions.services import (
    can_use_feature,
    get_effective_plan,
    increment_usage,
)


@login_required
def editor_view(request):
    """Fotoğraf düzenleme sayfası — ayrı işlem endpoint'i olmadığı için her ziyarette 1 kota."""
    plan = get_effective_plan(request.user)
    if not plan or not plan.has_feature("advanced_editor"):
        messages.error(
            request,
            "Gelişmiş editör mevcut planınızda yok. Yükseltmek için plan seçin.",
        )
        return redirect("payments:upgrade")

    if not can_use_feature(request.user, FeatureUsage.FEATURE_EDITOR):
        messages.error(
            request,
            "Görsel editör kullanım limitiniz doldu. Plan yükselterek devam edebilirsiniz.",
        )
        return redirect("payments:upgrade")

    increment_usage(request.user, FeatureUsage.FEATURE_EDITOR)
    record_usage_event(request.user, "editor", metadata={})
    return render(request, "editor/editor.html")
