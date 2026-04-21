from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator

from apps.analytics.services import record_usage_event
from apps.subscriptions.services import get_effective_plan

from .models import Garment, GarmentCategory, Outfit
from .forms import GarmentForm
from .utils import suggest_outfits, generate_outfit_suggestions, OCCASION_CHOICES

try:
    from apps.services.weather import get_weather_data
except ImportError:
    get_weather_data = None

from ai_engine.image_processor import run_garment_analysis

# Liste / filtre çipleri (?kategori=) — alt kategori alanı veya kategori slug
WARDROBE_SUBCATEGORY_SLUGS = frozenset({"ust", "alt", "dis", "ayakkabi", "aksesuar"})

WARDROBE_FILTER_CHIPS = [
    {"slug": "", "name": "Tümü"},
    {"slug": "elbise", "name": "Elbiseler"},
    {"slug": "ust", "name": "Üst Giyim"},
    {"slug": "alt", "name": "Alt Giyim"},
    {"slug": "ayakkabi", "name": "Ayakkabı"},
    {"slug": "aksesuar", "name": "Aksesuar"},
    {"slug": "dis", "name": "Dış Giyim"},
]


def _get_wardrobe_queryset(request):
    """Ortak filtreli queryset."""
    qs = Garment.objects.filter(user=request.user, is_active=True).select_related("category")
    kat = (request.GET.get("kategori") or "").strip()
    if kat:
        if kat in WARDROBE_SUBCATEGORY_SLUGS:
            qs = qs.filter(subcategory=kat)
        else:
            qs = qs.filter(category__slug=kat)
    if request.GET.get("mevsim"):
        qs = qs.filter(season=request.GET["mevsim"])
    if request.GET.get("renk"):
        color = request.GET["renk"].lower()
        qs = qs.filter(Q(color__icontains=color) | Q(color_hex__iexact=color))
    if request.GET.get("favori"):
        qs = qs.filter(is_favorite=True)
    if request.GET.get("q"):
        q = request.GET["q"].strip()
        qs = qs.filter(
            Q(name__icontains=q) | Q(brand__icontains=q) | Q(notes__icontains=q)
        )
    return qs


def _apply_sort(queryset, sort_key):
    """Sıralama uygula."""
    if sort_key == "worn":
        return queryset.order_by("-times_worn", "-created_at")
    if sort_key == "favorite":
        return queryset.order_by("-is_favorite", "-created_at")
    if sort_key == "color":
        return queryset.order_by("color", "name")
    return queryset.order_by("-created_at")


def _wardrobe_list_page_context(request):
    """Gardırop kart ızgarası + sayfalama (20) için ortak bağlam."""
    garments_qs = _get_wardrobe_queryset(request)
    garments_qs = _apply_sort(garments_qs, request.GET.get("sira", ""))
    total_items = garments_qs.count()

    paginator = Paginator(garments_qs, 20)
    page_obj = paginator.get_page(request.GET.get("sayfa"))

    q = request.GET.copy()
    q.pop("sayfa", None)
    qs = q.urlencode()
    pagination_prefix = ("?" + qs + "&") if qs else "?"

    cur = page_obj.number
    total_pages = page_obj.paginator.num_pages
    if total_pages <= 7:
        page_numbers = list(range(1, total_pages + 1))
    else:
        start = max(1, cur - 2)
        end = min(total_pages, cur + 2)
        page_numbers = list(range(start, end + 1))

    current_category = (request.GET.get("kategori") or "").strip()
    search_query = (request.GET.get("q") or "").strip()

    def _chip_href(k_slug):
        qd = request.GET.copy()
        qd.pop("sayfa", None)
        if k_slug:
            qd["kategori"] = k_slug
        else:
            qd.pop("kategori", None)
        return "?" + qd.urlencode() if qd else "?"

    filter_chips = []
    for chip in WARDROBE_FILTER_CHIPS:
        slug = chip["slug"]
        active = current_category == slug if slug else not current_category
        filter_chips.append(
            {**chip, "active": active, "href": _chip_href(slug)}
        )

    return {
        "garments": page_obj,
        "page_obj": page_obj,
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page_obj.number,
        "page_numbers": page_numbers,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "previous_page_number": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "next_page_number": page_obj.next_page_number() if page_obj.has_next() else None,
        "pagination_prefix": pagination_prefix,
        "current_category": current_category,
        "search_query": search_query,
        "filter_chips": filter_chips,
    }


@login_required
def wardrobe_view(request):
    """Gardırop ana sayfası — kart ızgarası (/gardırop/)."""
    ctx = _wardrobe_list_page_context(request)
    ctx["show_pin_grid_link"] = True
    return render(request, "wardrobe/list.html", ctx)


@login_required
def wardrobe_list_view(request):
    """Eski /gardırop/liste/ yolu — ana liste ile aynı görünüm."""
    ctx = _wardrobe_list_page_context(request)
    ctx["show_pin_grid_link"] = False
    return render(request, "wardrobe/list.html", ctx)


@login_required
def wardrobe_pin_grid_view(request):
    """Pinterest tarzı grid (sidebar filtreler) — /gardırop/pin/."""
    garments = _get_wardrobe_queryset(request)
    garments = _apply_sort(garments, request.GET.get("sira", ""))

    categories = GarmentCategory.objects.all().order_by("order", "name")
    active_cats = GarmentCategory.objects.filter(
        garments__user=request.user, garments__is_active=True
    ).distinct()

    colors = (
        Garment.objects.filter(user=request.user, is_active=True)
        .exclude(color="")
        .values_list("color", flat=True)
        .distinct()[:12]
    )

    return render(
        request,
        "wardrobe/home.html",
        {
            "garments": garments,
            "categories": categories,
            "active_cats": active_cats,
            "colors": colors,
            "active_category": request.GET.get("kategori"),
            "garment_count": garments.count(),
            "favorites_count": Garment.objects.filter(
                user=request.user, is_active=True, is_favorite=True
            ).count(),
            "outfit_count": Outfit.objects.filter(user=request.user).count(),
        },
    )


@login_required
def wardrobe_stats_view(request):
    """Gardırop istatistikleri."""
    from django.db.models import Sum

    user = request.user
    base = Garment.objects.filter(user=user, is_active=True)

    stats = {
        "total": base.count(),
        "favorites": base.filter(is_favorite=True).count(),
        "by_category": list(
            base.values("category__name")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")
        ),
        "most_worn": base.order_by("-times_worn")[:5],
    }

    return render(request, "wardrobe/stats.html", {"stats": stats})


@login_required
def garment_add_view(request):
    """Yeni kıyafet ekle — iki aşamalı yükleme + düzenlenebilir alanlar."""
    if request.method == "POST":
        form = GarmentForm(request.POST, request.FILES, dark_ui=True)
        if form.is_valid():
            current_count = Garment.objects.filter(
                user=request.user, is_active=True
            ).count()
            plan = get_effective_plan(request.user)
            limit = plan.wardrobe_limit if plan else 10
            if limit > 0 and current_count >= limit:
                messages.error(
                    request,
                    f"Gardırop limitiniz {limit} parça. Plan yükselterek daha fazla kıyafet ekleyebilirsiniz.",
                )
                return redirect("payments:upgrade")

            garment = form.save(commit=False)
            garment.user = request.user
            garment.save()

            record_usage_event(
                request.user,
                "wardrobe_add",
                metadata={"garment_id": garment.id},
            )

            run_garment_analysis(garment.id)

            messages.success(request, f'"{garment.name}" gardıroba eklendi.')
            return redirect("wardrobe:index")
        analysis_always_visible = True
    else:
        form = GarmentForm(dark_ui=True)
        analysis_always_visible = False

    return render(
        request,
        "wardrobe/add.html",
        {
            "form": form,
            "garment": None,
            "action": "Ekle",
            "analysis_always_visible": analysis_always_visible,
        },
    )


@login_required
def garment_detail_view(request, pk):
    """Kıyafet detayı"""
    garment = get_object_or_404(Garment, pk=pk, user=request.user)
    return render(request, "wardrobe/garment_detail.html", {"garment": garment})


@login_required
def garment_edit_view(request, pk):
    """Kıyafet düzenle"""
    garment = get_object_or_404(Garment, pk=pk, user=request.user)
    if request.method == "POST":
        form = GarmentForm(request.POST, request.FILES, instance=garment)
        if form.is_valid():
            form.save()
            if request.FILES.get("image"):
                run_garment_analysis(garment.id)
            messages.success(request, "Kıyafet güncellendi.")
            return redirect("wardrobe:detail", pk=pk)
    else:
        form = GarmentForm(instance=garment)

    initial_step = 1
    if form.errors:
        error_to_step = {"image": 1, "name": 2, "category": 2, "subcategory": 2, "color": 3, "color_hex": 3, "brand": 3, "size": 3, "material": 3, "pattern": 3, "season": 3, "price": 4, "purchase_date": 4, "store_name": 4, "purchase_url": 4, "tags_input": 4, "notes": 4}
        steps_with_errors = [error_to_step.get(f, 4) for f in form.errors if f in error_to_step]
        if steps_with_errors:
            initial_step = min(steps_with_errors)

    return render(
        request,
        "wardrobe/garment_form.html",
        {
            "form": form,
            "garment": garment,
            "action": "Güncelle",
            "initial_step": initial_step,
        },
    )


@login_required
def garment_delete_view(request, pk):
    """Kıyafet sil (soft delete)"""
    garment = get_object_or_404(Garment, pk=pk, user=request.user)
    if request.method == "POST":
        garment.is_active = False
        garment.save(update_fields=["is_active"])
        messages.success(request, f'"{garment.name}" silindi.')
        return redirect("wardrobe:index")

    return render(request, "wardrobe/garment_confirm_delete.html", {"garment": garment})


@login_required
@require_POST
def garment_favorite_toggle_view(request, pk):
    """Favori toggle — AJAX."""
    garment = get_object_or_404(Garment, pk=pk, user=request.user)
    garment.is_favorite = not garment.is_favorite
    garment.save(update_fields=["is_favorite"])
    return JsonResponse({"is_favorite": garment.is_favorite})


@login_required
@require_POST
def garment_bulk_delete_view(request):
    """Toplu silme."""
    import json

    try:
        data = json.loads(request.body)
        ids = data.get("ids", [])
    except json.JSONDecodeError:
        return JsonResponse({"error": "Geçersiz JSON"}, status=400)

    count = Garment.objects.filter(user=request.user, pk__in=ids).update(is_active=False)
    return JsonResponse({"deleted": count})


def _get_user_city(request):
    """Profildeki şehri al; yoksa İstanbul varsay."""
    profile = getattr(request.user, "profile", None)
    if profile and getattr(profile, "city", None) and profile.city.strip():
        return profile.city.strip()
    return "Istanbul"


@login_required
def outfit_suggest_view(request):
    """AI kombin önerisi — occasion seçimi veya tek tıkla (quick=1) sonuçlar."""
    garments = Garment.objects.filter(user=request.user, is_active=True)
    if garments.count() < 2:
        messages.warning(request, "Kombin önerisi için en az 2 kıyafet gerekir.")
        return redirect("wardrobe:add")

    weather_info = None
    if get_weather_data:
        city = _get_user_city(request)
        weather_info = get_weather_data(city)

    # Tek tıkla: ?quick=1 → hemen kombinleri göster (generate_outfit_suggestions)
    if request.GET.get("quick") == "1":
        outfits = generate_outfit_suggestions(request.user, weather_data=weather_info)
        return render(
            request,
            "wardrobe/outfit_suggest.html",
            {
                "outfits": outfits,
                "occasion": "gunluk",
                "occasion_label": "Günlük",
                "weather_info": weather_info,
            },
        )

    if request.method == "POST":
        occasion = request.POST.get("occasion", "gunluk")
        manual_weather = request.POST.get("weather", "").strip() or None
        # Manuel hava metni yoksa API'den çek
        if manual_weather:
            weather_data = manual_weather
        else:
            weather_data = weather_info
        outfits = suggest_outfits(request.user, occasion, weather_data)
        return render(
            request,
            "wardrobe/outfit_suggest.html",
            {
                "outfits": outfits,
                "occasion": occasion,
                "occasion_label": dict(OCCASION_CHOICES).get(occasion, occasion),
                "weather_info": weather_info,
            },
        )

    return render(
        request,
        "wardrobe/outfit_suggest.html",
        {
            "outfits": None,
            "occasion_choices": OCCASION_CHOICES,
            "weather_info": weather_info,
        },
    )


@login_required
@require_POST
def outfit_wear_view(request):
    """Kombini bugün giydim — times_worn +1, last_worn güncelle."""
    import json

    try:
        data = json.loads(request.body) if request.body else {}
        ids = data.get("garment_ids", [])
    except json.JSONDecodeError:
        return JsonResponse({"error": "Geçersiz JSON"}, status=400)

    if not ids:
        return JsonResponse({"error": "Kıyafet seçilmedi"}, status=400)

    today = timezone.now().date()
    qs = Garment.objects.filter(user=request.user, pk__in=ids)
    for g in qs:
        g.times_worn = (g.times_worn or 0) + 1
        g.last_worn = today
        g.save(update_fields=["times_worn", "last_worn"])

    return JsonResponse({"ok": True, "updated": qs.count()})
