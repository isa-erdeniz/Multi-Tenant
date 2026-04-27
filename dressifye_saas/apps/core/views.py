from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone


def landing_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    from apps.subscriptions.models import Plan

    plans = Plan.objects.filter(is_active=True).order_by("order", "pk")
    return render(
        request,
        "core/landing.html",
        {
            "plans": plans,
            "has_plans": plans.exists(),
        },
    )


def _dashboard_plan_limits(user, sub):
    """(garment_limit, tryon_monthly_limit); None = sınırsız."""
    from apps.subscriptions.services import get_effective_plan

    plan = sub.plan if sub and sub.plan_id else None
    if plan is None:
        plan = get_effective_plan(user)
    if not plan:
        return 10, 3

    wl = plan.wardrobe_limit
    tl = plan.tryon_limit
    return (None if wl == 0 else wl), (None if tl == 0 else tl)


def _dashboard_weather_context(profile):
    from apps.services.weather import get_weather_data

    city = (profile.city.strip() if profile and profile.city else "") or "İstanbul"
    data = get_weather_data(city)
    emoji_map = {
        "Clear": "☀️",
        "Clouds": "☁️",
        "Rain": "🌧️",
        "Drizzle": "🌦️",
        "Thunderstorm": "⛈️",
        "Snow": "❄️",
    }
    if data:
        key = data.get("condition_key") or ""
        emoji = emoji_map.get(key, "🌤️")
        cond = (data.get("condition") or "").lower()
        if data.get("is_rainy"):
            tip = f"Bugün {cond} — bot ve mont önerilir."
        elif data.get("temp") is not None and float(data["temp"]) >= 26:
            tip = f"Bugün {cond} — hafif ve nefes alan kumaşlar uygun."
        else:
            tip = f"Bugün {cond} — katmanlı giyinmek rahat olur."
        return {
            "weather_emoji": emoji,
            "weather_city": data.get("city_name") or city,
            "weather_temp": data.get("temp"),
            "weather_tip": tip,
        }
    return {
        "weather_emoji": "🌤️",
        "weather_city": city,
        "weather_temp": None,
        "weather_tip": "Hava durumu alınamadı; yağmurlu günlere karşılık mont ve bot hazır bulundurun.",
    }


def _dashboard_ai_cards(user, limit=2):
    demos = [
        {
            "type": "demo",
            "title": "Yağmurlu Gün Kombini",
            "description": "Su geçirmez mont, deri bot ve şemsiye ile hazır olun.",
            "icons": ["🧥", "👢", "☂️"],
        },
        {
            "type": "demo",
            "title": "Ofis Şıklığı",
            "description": "Profesyonel ve rahat; günlük toplantılar için ideal.",
            "icons": ["👔", "👖", "👞"],
        },
    ]
    sessions = list(
        user.style_sessions.filter(status="completed")
        .prefetch_related("garments_suggested")[:limit]
    )
    cards = [{"type": "session", "session": s} for s in sessions]
    i = 0
    while len(cards) < limit:
        cards.append(demos[i % len(demos)].copy())
        i += 1
    return cards[:limit]


def _tryon_count_this_month(user):
    """Plan kotası ile uyum için FeatureUsage (tenant bazlı) ile hizalanır."""
    from apps.subscriptions.models import FeatureUsage
    from apps.subscriptions.services import get_usage, month_start

    return get_usage(user, FeatureUsage.FEATURE_TRYON, month_start())


@login_required
def dashboard_view(request):
    user = request.user
    profile = getattr(user, "profile", None)
    sub = getattr(user, "subscription", None)

    garment_count = user.garments.filter(is_active=True).count()
    trial_days_left = sub.trial_days_left() if sub else 0
    is_trial = sub.status == "trial" if sub else False

    garment_limit, tryon_limit = _dashboard_plan_limits(user, sub)
    tryon_used = _tryon_count_this_month(user)

    if garment_limit:
        garment_usage_pct = min(100, int(round(100 * garment_count / max(garment_limit, 1))))
    else:
        garment_usage_pct = 100
    if tryon_limit:
        tryon_usage_pct = min(100, int(round(100 * tryon_used / max(tryon_limit, 1))))
    else:
        tryon_usage_pct = 100

    trial_expired = bool(sub and sub.is_trial_expired())

    show_upgrade_cta = False
    if trial_expired:
        show_upgrade_cta = True
    if garment_limit and garment_count >= max(1, int(garment_limit * 0.8)):
        show_upgrade_cta = True
    if tryon_limit and tryon_used >= max(1, int(tryon_limit * 0.8)):
        show_upgrade_cta = True

    if user.first_name:
        welcome_name = user.first_name
    elif profile and profile.first_name:
        welcome_name = profile.first_name
    elif profile:
        welcome_name = profile.get_display_name()
    else:
        welcome_name = "Stil Sever"

    recent_garments = user.garments.filter(is_active=True).select_related("category")[:6]
    weather_ctx = _dashboard_weather_context(profile)
    ai_cards = _dashboard_ai_cards(user, 2)

    from apps.subscriptions.models import FeatureUsage
    from apps.subscriptions.services import get_effective_plan, get_remaining

    effective_plan = get_effective_plan(user)
    quota_remaining = {
        "tryon": get_remaining(user, FeatureUsage.FEATURE_TRYON),
        "editor": get_remaining(user, FeatureUsage.FEATURE_EDITOR),
        "style_session": get_remaining(user, FeatureUsage.FEATURE_STYLE_SESSION),
    }

    ctx = {
        "profile": profile,
        "sub": sub,
        "garment_count": garment_count,
        "trial_days_left": trial_days_left,
        "is_trial": is_trial,
        "welcome_name": welcome_name,
        "recent_garments": recent_garments,
        "ai_cards": ai_cards,
        "garment_limit": garment_limit,
        "tryon_limit": tryon_limit,
        "tryon_used": tryon_used,
        "garment_usage_pct": garment_usage_pct,
        "tryon_usage_pct": tryon_usage_pct,
        "show_upgrade_cta": show_upgrade_cta,
        "trial_expired": trial_expired,
        "effective_plan": effective_plan,
        "quota_remaining": quota_remaining,
        **weather_ctx,
    }
    return render(request, "dashboard/home.html", ctx)


def health_check(request):
    return JsonResponse({"status": "ok", "service": "dressifye_saas"})
