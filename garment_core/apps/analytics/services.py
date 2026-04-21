"""
Kullanım olaylarını UsageEvent olarak kaydet.
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def record_usage_event(
    user,
    event_type: str,
    metadata: Optional[dict[str, Any]] = None,
    session_id: str = "",
) -> None:
    """
    user: request.user (anon ise kayıt yapılmaz).
    event_type: UsageEvent.EVENT_TYPES içindeki anahtarlar.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return
    try:
        from apps.analytics.models import UsageEvent

        UsageEvent.objects.create(
            user=user,
            event_type=event_type,
            metadata=metadata or {},
            session_id=(session_id or "")[:100],
        )
    except Exception:
        logger.exception("UsageEvent kaydı başarısız event_type=%s", event_type)
