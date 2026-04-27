import logging

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse

from apps.analytics.services import record_usage_event
from apps.subscriptions.models import FeatureUsage
from apps.subscriptions.services import can_use_feature, increment_usage
from apps.wardrobe.models import Garment

from ai_engine.tryon_processor import run_tryon_session

from .models import TryOnSession

logger = logging.getLogger(__name__)


def _garment_tryon_json(g: Garment) -> dict:
    return {
        "id": g.id,
        "name": g.name,
        "imageUrl": g.image.url if g.image else "",
        "icon": (g.category.icon if g.category else "") or "👗",
    }


@login_required
def tryon_view(request):
    """Try-On ana sayfası — 4 aşamalı akış (fotoğraf → kıyafet → işlem → sonuç)."""
    garments = (
        Garment.objects.filter(user=request.user, is_active=True)
        .select_related("category")
        .order_by("-created_at")
    )

    selected_garment_id = request.GET.get("kiyafet")
    selected_garment = None
    if selected_garment_id:
        selected_garment = garments.filter(pk=selected_garment_id).first()

    garments_payload = [_garment_tryon_json(g) for g in garments]

    return render(
        request,
        "tryon/index.html",
        {
            "garments": garments,
            "garments_json": garments_payload,
            "selected_garment": selected_garment,
        },
    )


@login_required
def tryon_start_view(request):
    """Try-On oturumu başlat — fotoğraf + kıyafet alır"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    photo = request.FILES.get("photo")
    garment_id = request.POST.get("garment_id")

    if not photo:
        return JsonResponse({"error": "Fotoğraf gerekli"}, status=400)
    if not garment_id:
        return JsonResponse({"error": "Kıyafet seçin"}, status=400)

    garment = get_object_or_404(Garment, pk=garment_id, user=request.user)

    if not can_use_feature(request.user, FeatureUsage.FEATURE_TRYON):
        return JsonResponse(
            {
                "error": "Limit doldu",
                "redirect": reverse("subscriptions:plan_list"),
            },
            status=403,
        )

    session = TryOnSession.objects.create(
        user=request.user,
        garment=garment,
        status="pending",
    )
    try:
        session.user_photo.save(f"tryon_{session.id}.jpg", photo, save=True)
    except Exception:
        logger.exception("tryon fotoğraf kaydı başarısız")
        session.delete()
        return JsonResponse(
            {"error": "Fotoğraf kaydedilemedi. Lütfen tekrar deneyin."},
            status=500,
        )

    # Kota: fotoğraf ve oturum başarıyla oluştuktan sonra (require_feature_usage
    # consume=True view öncesinde çalıştığı için burada manuel artırım)
    increment_usage(request.user, FeatureUsage.FEATURE_TRYON)
    record_usage_event(
        request.user,
        "tryon",
        metadata={"session_id": session.id},
        session_id=str(session.id),
    )
    run_tryon_session(session.id)

    return JsonResponse(
        {
            "session_id": session.id,
            "status": "processing",
        }
    )


@login_required
def tryon_status_view(request, pk):
    """Polling endpoint"""
    session = get_object_or_404(TryOnSession, pk=pk, user=request.user)
    data = {
        "status": session.status,
        "progress": {
            "pending": 10,
            "processing": 60,
            "completed": 100,
            "failed": 0,
        }.get(session.status, 0),
    }
    if session.status == "completed":
        if session.canvas_settings:
            data["ai_feedback"] = session.canvas_settings.get("ai_feedback", "")
        if session.user_photo:
            data["user_photo_url"] = session.user_photo.url
        if session.result_image:
            data["result_image_url"] = session.result_image.url
    if session.status == "failed":
        data["error_message"] = (session.error_message or "").strip() or "İşlem tamamlanamadı."
    return JsonResponse(data)


@login_required
def tryon_history_view(request):
    """Kullanıcının geçmiş try-on oturumları"""
    sessions = TryOnSession.objects.filter(user=request.user).select_related(
        "garment", "garment__category"
    )[:20]

    return render(request, "tryon/history.html", {"sessions": sessions})
