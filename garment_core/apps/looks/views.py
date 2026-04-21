"""FAZ 11: Hazır Görünüm Paketleri."""
import logging

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse

from apps.subscriptions.models import FeatureUsage
from apps.subscriptions.services import can_use_feature, increment_usage

from .models import LookPackage, LookApplySession

logger = logging.getLogger(__name__)


@login_required
def looks_index_view(request):
    """Görünüm galerisi."""
    looks = LookPackage.objects.all()[:24]
    return render(request, "looks/index.html", {"looks": looks})


@login_required
def looks_apply_view(request):
    """Look uygulama oturumu başlat — fotoğraf + look alır, AI işlemi başlatır."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    from apps.looks.tasks import process_look_apply_session

    photo = request.FILES.get("photo")
    look_id = request.POST.get("look_id")

    if not photo:
        return JsonResponse({"error": "Fotoğraf gerekli"}, status=400)
    if not look_id:
        return JsonResponse({"error": "Görünüm paketi seçin"}, status=400)

    look = LookPackage.objects.filter(pk=look_id).first()
    if not look:
        return JsonResponse({"error": "Görünüm paketi bulunamadı"}, status=404)

    if not can_use_feature(request.user, FeatureUsage.FEATURE_LOOK_APPLY):
        return JsonResponse(
            {
                "error": "Limit doldu",
                "redirect": reverse("subscriptions:plan_list"),
            },
            status=403,
        )

    session = LookApplySession.objects.create(
        user=request.user,
        look=look,
        status="pending",
    )
    try:
        session.photo.save(f"look_{session.id}.jpg", photo, save=True)
    except Exception:
        logger.exception("look fotoğraf kaydı başarısız")
        session.delete()
        return JsonResponse(
            {"error": "Fotoğraf kaydedilemedi. Lütfen tekrar deneyin."},
            status=500,
        )

    try:
        process_look_apply_session.delay(session.id)
    except AttributeError:
        process_look_apply_session(session.id)

    return JsonResponse(
        {
            "session_id": session.id,
            "status": "processing",
        }
    )


@login_required
def looks_status_view(request, pk):
    """Look oturumu durum polling endpoint."""
    session = LookApplySession.objects.filter(pk=pk, user=request.user).first()
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
