"""FAZ 10: AI Avatar Oluşturma."""
import logging

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse

from apps.subscriptions.models import FeatureUsage
from apps.subscriptions.services import can_use_feature, increment_usage

from ai_engine.avatar_generator import run_avatar_session

from .models import AvatarStyle, BackgroundTemplate, AvatarSession

logger = logging.getLogger(__name__)


@login_required
def avatar_index_view(request):
    """Avatar oluşturma ana sayfası."""
    styles = AvatarStyle.objects.all()[:12]
    backgrounds = BackgroundTemplate.objects.all()[:8]
    return render(request, "avatar/index.html", {"styles": styles, "backgrounds": backgrounds})


@login_required
def avatar_start_view(request):
    """Avatar oturumu başlat — selfie + stil alır, AI işlemi başlatır."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    photo = request.FILES.get("photo")
    style_id = request.POST.get("style_id")

    if not photo:
        return JsonResponse({"error": "Selfie fotoğrafı gerekli"}, status=400)

    style = None
    if style_id:
        style = AvatarStyle.objects.filter(pk=style_id).first()

    if not can_use_feature(request.user, FeatureUsage.FEATURE_AVATAR):
        return JsonResponse(
            {
                "error": "Limit doldu",
                "redirect": reverse("subscriptions:plan_list"),
            },
            status=403,
        )

    session = AvatarSession.objects.create(
        user=request.user,
        style=style,
        status="pending",
    )
    try:
        session.input_selfie.save(f"avatar_{session.id}.jpg", photo, save=True)
    except Exception:
        logger.exception("avatar selfie kaydı başarısız")
        session.delete()
        return JsonResponse(
            {"error": "Fotoğraf kaydedilemedi. Lütfen tekrar deneyin."},
            status=500,
        )

    run_avatar_session(session.id)

    return JsonResponse(
        {
            "session_id": session.id,
            "status": "processing",
        }
    )


@login_required
def avatar_status_view(request, pk):
    """Avatar oturumu durum polling endpoint."""
    session = AvatarSession.objects.filter(pk=pk, user=request.user).first()
    if not session:
        return JsonResponse({"error": "Oturum bulunamadı"}, status=404)

    data = {
        "status": session.status,
        "progress": {
            "pending": 10,
            "processing": 60,
            "completed": 100,
            "failed": 0,
        }.get(session.status, 0),
    }
    if session.status == "completed" and session.output_data:
        data["ai_feedback"] = session.output_data.get("ai_feedback", "")
    return JsonResponse(data)
