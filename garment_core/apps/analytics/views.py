"""
FAZ 21: Kullanım analitiği dashboard view'ları.
Yalnızca staff veya tenant owner erişebilir.
"""
import logging
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from apps.analytics.models import UsageEvent

logger = logging.getLogger(__name__)


@staff_member_required
def analytics_dashboard_view(request):
    """Son 30 günlük kullanım özeti — sadece staff erişebilir."""
    since = timezone.now() - timedelta(days=30)

    events_by_type = (
        UsageEvent.objects.filter(created_at__gte=since)
        .values("event_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    recent_events = (
        UsageEvent.objects.filter(created_at__gte=since)
        .select_related("user")
        .order_by("-created_at")[:50]
    )

    return render(request, "analytics/dashboard.html", {
        "events_by_type": list(events_by_type),
        "recent_events": recent_events,
        "period_days": 30,
    })
