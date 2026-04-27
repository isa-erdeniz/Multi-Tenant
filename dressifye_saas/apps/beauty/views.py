"""FAZ 8: AR Makyaj Deneme Motoru."""
import logging

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse

from apps.analytics.services import record_usage_event
from apps.subscriptions.models import FeatureUsage
from apps.subscriptions.services import can_use_feature, increment_usage

from ai_engine.makeup_engine import run_makeup_session

from .models import MakeupLook, MakeupSession

logger = logging.getLogger(__name__)


@login_required
def beauty_index_view(request):
    """Makyaj deneme ana sayfası."""
    looks = MakeupLook.objects.all()[:24]
    return render(request, "beauty/index.html", {"looks": looks})


@login_required
def beauty_start_view(request):
    """Makyaj oturumu başlat — fotoğraf + look alır, AI işlemi başlatır."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    photo = request.FILES.get("photo")
    look_id = request.POST.get("look_id")

    if not photo:
        return JsonResponse({"error": "Fotoğraf gerekli"}, status=400)

    look = None
    if look_id:
        look = MakeupLook.objects.filter(pk=look_id).first()

    if not can_use_feature(request.user, FeatureUsage.FEATURE_MAKEUP):
        return JsonResponse(
            {
                "error": "Limit doldu",
                "redirect": reverse("subscriptions:plan_list"),
            },
            status=403,
        )

    session = MakeupSession.objects.create(
        user=request.user,
        applied_look=look,
        status="pending",
    )
    try:
        session.input_image.save(f"makeup_{session.id}.jpg", photo, save=True)
    except Exception:
        logger.exception("makeup fotoğraf kaydı başarısız")
        session.delete()
        return JsonResponse(
            {"error": "Fotoğraf kaydedilemedi. Lütfen tekrar deneyin."},
            status=500,
        )

    increment_usage(request.user, FeatureUsage.FEATURE_MAKEUP)
    run_makeup_session(session.id)

    return JsonResponse(
        {
            "session_id": session.id,
            "status": "processing",
        }
    )


@login_required
def beauty_status_view(request, pk):
    """Makyaj oturumu durum polling endpoint."""
    session = MakeupSession.objects.filter(pk=pk, user=request.user).first()
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
