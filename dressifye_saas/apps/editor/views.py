"""FAZ 6: Fotoğraf Düzenleme Modülü."""
import json
import os
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

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


@login_required
@require_POST
def editor_upload_view(request):
    """
    POST /duzenle/yukle/
    Dosya yükler → arka plan silme (remove.bg) → JSON sonuç.
    """
    photo = request.FILES.get("photo")
    if not photo:
        return JsonResponse({"error": "Fotoğraf gerekli"}, status=400)

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if photo.content_type not in allowed_types:
        return JsonResponse(
            {"error": "Geçersiz dosya türü. JPEG, PNG veya WebP yükleyin."}, status=400
        )

    if photo.size > 10 * 1024 * 1024:
        return JsonResponse({"error": "Dosya 10 MB sınırını aşıyor."}, status=400)

    from apps.services.image_processing import remove_background as _remove_bg

    result_bytes = _remove_bg(photo)

    timestamp = int(time.time())
    ext = "png" if result_bytes else (os.path.splitext(photo.name)[1].lstrip(".") or "jpg")
    save_name = f"editor/sessions/{request.user.pk}/{timestamp}.{ext}"

    if result_bytes:
        saved_path = default_storage.save(save_name, ContentFile(result_bytes))
        bg_removed = True
    else:
        photo.seek(0)
        saved_path = default_storage.save(save_name, photo)
        bg_removed = False

    file_url = default_storage.url(saved_path)

    return JsonResponse({
        "ok": True,
        "file_url": file_url,
        "bg_removed": bg_removed,
        "saved_path": saved_path,
    })


@login_required
@require_POST
def editor_analyze_view(request):
    """
    POST /duzenle/analiz/
    Yüklü fotoğrafı MEHLR ile analiz eder (stil önerisi, renk uyumu vb.).
    """
    try:
        body = json.loads(request.body)
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Geçersiz JSON"}, status=400)

    file_url = body.get("file_url", "")
    user_note = body.get("note", "")

    if not file_url:
        return JsonResponse({"error": "file_url gerekli"}, status=400)

    from apps.core.clients.mehlr_client import MEHLRClient

    client = MEHLRClient()
    result = client.analyze(
        project=settings.MEHLR_PROJECT,
        prompt=(
            f"Kullanıcı bir fotoğrafı düzenlemek ve analiz ettirmek istiyor.\n"
            f"Fotoğraf URL: {file_url}\n"
            f"Kullanıcı notu: {user_note or 'Belirtilmemiş'}\n\n"
            f"Bu fotoğraf için stil değerlendirmesi, renk uyumu ve öneriler ver."
        ),
        context={
            "task": "editor_analysis",
            "file_url": file_url,
            "user_id": request.user.pk,
        },
    )

    if result.get("success"):
        return JsonResponse({
            "ok": True,
            "analysis": result["data"].get("response", ""),
        })
    else:
        return JsonResponse({
            "ok": False,
            "analysis": "Analiz şu an mevcut değil, fotoğrafınız kaydedildi.",
            "error": result.get("error", ""),
        })
