"""FAZ 9: Sanal Saç Değiştirme."""
import logging

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse

from apps.analytics.services import record_usage_event
from apps.subscriptions.models import FeatureUsage
from apps.subscriptions.services import can_use_feature, increment_usage

from ai_engine.hair_engine import run_hair_session

from .models import HairStyle, HairColor, HairSession

logger = logging.getLogger(__name__)


@login_required
def hair_index_view(request):
    """Saç değiştirme ana sayfası."""
    styles = HairStyle.objects.all()[:20]
    colors = HairColor.objects.all()[:20]
    return render(request, "hair/index.html", {"styles": styles, "colors": colors})


@login_required
def hair_start_view(request):
    """Saç değiştirme oturumu başlat — fotoğraf + stil/renk alır, AI işlemi başlatır."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    photo = request.FILES.get("photo")
    style_id = request.POST.get("style_id")
    color_id = request.POST.get("color_id")

    if not photo:
        return JsonResponse({"error": "Fotoğraf gerekli"}, status=400)

    style = None
    if style_id:
        style = HairStyle.objects.filter(pk=style_id).first()

    color = None
    if color_id:
        color = HairColor.objects.filter(pk=color_id).first()

    if not can_use_feature(request.user, FeatureUsage.FEATURE_TRYON):
        return JsonResponse(
            {
                "error": "Limit doldu",
                "redirect": reverse("subscriptions:plan_list"),
            },
            status=403,
        )

    session = HairSession.objects.create(
        user=request.user,
        applied_style=style,
        applied_color=color,
        status="pending",
    )
    try:
        session.input_image.save(f"hair_{session.id}.jpg", photo, save=True)
    except Exception:
        logger.exception("hair fotoğraf kaydı başarısız")
        session.delete()
        return JsonResponse(
            {"error": "Fotoğraf kaydedilemedi. Lütfen tekrar deneyin."},
            status=500,
        )

    increment_usage(request.user, FeatureUsage.FEATURE_TRYON)
    run_hair_session(session.id)

    return JsonResponse(
        {
            "session_id": session.id,
            "status": "processing",
        }
    )


@login_required
def hair_status_view(request, pk):
    """Saç oturumu durum polling endpoint."""
    session = HairSession.objects.filter(pk=pk, user=request.user).first()
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
