import logging

from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from apps.analytics.services import record_usage_event
from apps.subscriptions.models import FeatureUsage
from apps.subscriptions.services import (
    can_use_feature,
    get_effective_plan,
    increment_usage,
)
from apps.wardrobe.models import Garment

from ai_engine.style_advisor import run_style_session

from .models import StyleSession

logger = logging.getLogger(__name__)


COMBO_BUCKETS = [
    {"key": "elbise", "label": "Elbise", "emoji": "👗", "modal_title": "Elbise seç"},
    {"key": "ust", "label": "Üst Giyim", "emoji": "👔", "modal_title": "Üst giyim seç"},
    {"key": "alt", "label": "Alt Giyim", "emoji": "👖", "modal_title": "Alt giyim seç"},
    {"key": "ayakkabi", "label": "Ayakkabı", "emoji": "👠", "modal_title": "Ayakkabı seç"},
    {"key": "dis", "label": "Dış Giyim", "emoji": "🧥", "modal_title": "Dış giyim seç"},
    {"key": "aksesuar", "label": "Aksesuar", "emoji": "💍", "modal_title": "Aksesuar seç"},
]


def _garment_combo_dict(garment, bucket_key):
    return {
        "id": garment.id,
        "name": garment.name,
        "icon": (garment.category.icon if garment.category and garment.category.icon else "") or "👗",
        "imageUrl": garment.image_url,
        "bucket": bucket_key,
        "subKey": garment.subcategory or "",
    }


def _garments_for_bucket(qs, key):
    if key == "elbise":
        return (
            qs.filter(
                Q(category__slug__icontains="elbise")
                | Q(category__name__icontains="elbise")
                | Q(name__icontains="elbise")
            )
            .distinct()
            .order_by("-created_at")[:80]
        )
    return qs.filter(subcategory=key).order_by("-created_at")[:80]


def _wardrobe_by_bucket_json(user):
    base = Garment.objects.filter(user=user, is_active=True).select_related("category")
    out = {}
    for b in COMBO_BUCKETS:
        key = b["key"]
        out[key] = [
            _garment_combo_dict(g, key) for g in _garments_for_bucket(base, key)
        ]
    return out, COMBO_BUCKETS


@login_required
def styling_index_view(request):
    """Stil oturumları listesi"""
    sessions = StyleSession.objects.filter(
        user=request.user
    ).prefetch_related("garments_suggested")

    saved = sessions.filter(is_saved=True)
    recent = sessions.filter(is_saved=False)[:10]

    return render(
        request,
        "styling/index.html",
        {
            "saved": saved,
            "recent": recent,
        },
    )


@login_required
def styling_new_view(request):
    """Yeni stil oturumu — kombin oluştur arayüzü + AI isteği."""

    if not request.user.garments.filter(is_active=True).exists():
        messages.warning(
            request,
            "Önce gardırobunuza kıyafet eklemeniz gerekiyor.",
        )
        return redirect("wardrobe:add")

    plan = get_effective_plan(request.user)
    if not plan or not plan.has_feature("ai_stylist"):
        messages.error(
            request,
            "AI stilist özelliği mevcut planınızda yok. Yükseltmek için plan seçin.",
        )
        return redirect("payments:upgrade")

    wardrobe_by_bucket, combo_buckets = _wardrobe_by_bucket_json(request.user)

    if request.method == "POST":
        raw_ids = (request.POST.get("selected_garment_ids") or "").replace(" ", "")
        id_parts = [p for p in raw_ids.split(",") if p.isdigit()]
        ids = [int(p) for p in id_parts][:6]

        if len(id_parts) > 6:
            messages.error(request, "En fazla 6 parça seçebilirsiniz.")
        elif len(ids) < 1:
            messages.error(request, "En az bir kıyafet seçmelisiniz.")
        elif len(ids) != len(set(ids)):
            messages.error(request, "Aynı parçayı iki kez ekleyemezsiniz.")
        else:
            garments_sel = list(
                Garment.objects.filter(
                    user=request.user, is_active=True, pk__in=ids
                ).select_related("category")
            )
            by_id = {g.id: g for g in garments_sel}
            ordered = [by_id[i] for i in ids if i in by_id]
            if len(ordered) != len(ids):
                messages.error(
                    request,
                    "Bazı seçilen kıyafetler bulunamadı. Lütfen tekrar deneyin.",
                )
            else:
                name = (request.POST.get("combination_name") or "").strip()[:200]
                notes = (request.POST.get("combination_notes") or "").strip()[:2000]
                lines = []
                if name:
                    lines.append(f"Kombin adı: {name}")
                if notes:
                    lines.append(notes)
                lines.append(
                    "Şu gardırop parçalarını kullanarak uyumlu bir kombin öner: "
                    + ", ".join(g.name for g in ordered)
                    + "."
                )
                lines.append("Eksik parça varsa gardırobumdan uygun öneriler ekle.")
                user_prompt = "\n".join(lines)[:500]

                if not can_use_feature(request.user, FeatureUsage.FEATURE_STYLE_SESSION):
                    messages.error(
                        request,
                        "Aylık stil danışmanlığı limitiniz doldu.",
                    )
                    return redirect("payments:upgrade")

                session = StyleSession.objects.create(
                    user=request.user,
                    title=name or "",
                    user_prompt=user_prompt,
                    context={
                        "occasion": "",
                        "weather": "",
                        "mood": "",
                        "seed_garment_ids": [g.id for g in ordered],
                        "combination_name": name,
                    },
                )

                increment_usage(request.user, FeatureUsage.FEATURE_STYLE_SESSION)
                record_usage_event(
                    request.user,
                    "stylist",
                    metadata={"style_session_id": session.id},
                    session_id=str(session.id),
                )

                run_style_session(session.id)

                return redirect("styling:result", pk=session.pk)

    preselect = None
    gp = request.GET.get("garment")
    if gp and str(gp).isdigit():
        g = Garment.objects.filter(
            user=request.user, is_active=True, pk=int(gp)
        ).select_related("category").first()
        if g:
            preselect = _garment_combo_dict(
                g,
                g.subcategory or "elbise",
            )

    return render(
        request,
        "styling/new.html",
        {
            "wardrobe_by_bucket": wardrobe_by_bucket,
            "combo_buckets": combo_buckets,
            "preselect_garment": preselect,
        },
    )


@login_required
def styling_result_view(request, pk):
    """Stil oturumu sonucu — polling ile AI yanıtını bekler"""
    session = get_object_or_404(StyleSession, pk=pk, user=request.user)

    garment_map = {}
    if session.suggested_outfit:
        outfit_items = session.suggested_outfit.get("outfit", [])
        garment_ids = [
            item.get("garment_id")
            for item in outfit_items
            if isinstance(item, dict) and item.get("garment_id")
        ]

        from apps.wardrobe.models import Garment

        garments = Garment.objects.filter(id__in=garment_ids, user=request.user)
        garment_map = {g.id: g for g in garments}

    return render(
        request,
        "styling/result.html",
        {
            "session": session,
            "garment_map": garment_map,
        },
    )


@login_required
def styling_status_view(request, pk):
    """Polling endpoint"""
    session = get_object_or_404(StyleSession, pk=pk, user=request.user)
    progress_map = {
        "pending": 10,
        "processing": 60,
        "completed": 100,
        "failed": 0,
    }
    return JsonResponse(
        {
            "status": session.status,
            "progress": progress_map.get(session.status, 0),
        }
    )


@login_required
def styling_save_view(request, pk):
    """Öneriyi kaydet / kayıttan çıkar"""
    session = get_object_or_404(StyleSession, pk=pk, user=request.user)
    if request.method == "POST":
        session.is_saved = not session.is_saved
        session.save(update_fields=["is_saved"])
        return JsonResponse({"is_saved": session.is_saved})
    return JsonResponse({"error": "Method not allowed"}, status=405)
