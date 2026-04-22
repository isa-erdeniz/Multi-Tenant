"""
erdeniz_security/audit.py — SecurityAuditLog modeli ve log_event/get_alerts/get_stats.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _get_request_meta(request: Any | None) -> tuple[str | None, str]:
    if request is None:
        return None, ""
    ip = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")
    ua = request.META.get("HTTP_USER_AGENT", "")
    return ip, ua


def log_event(
    event_type: str,
    resource: str,
    project: str,
    user: Any = None,
    request: Any = None,
    success: bool = True,
    details: dict | None = None,
    duration_ms: int | None = None,
) -> None:
    """Audit kaydı oluştur."""
    ip, user_agent = _get_request_meta(request)
    details = details or {}
    try:
        from .models import SecurityAuditLog
        SecurityAuditLog.objects.create(
            event_type=event_type,
            user_id=user.pk if user and getattr(user, "pk", None) else None,
            ip_address=ip,
            user_agent=user_agent or "",
            resource=resource[:255],
            project=project[:50],
            success=success,
            details=details,
            duration_ms=duration_ms,
        )
    except Exception as e:
        logger.warning("Audit log: %s — %s", event_type, e)


def get_alerts(project: str | None = None, hours: int = 24) -> list[Any]:
    """Son X saatteki SECURITY_ALERT kayıtları."""
    try:
        from django.utils import timezone
        from datetime import timedelta
        from .models import SecurityAuditLog
        since = timezone.now() - timedelta(hours=hours)
        qs = SecurityAuditLog.objects.filter(event_type="SECURITY_ALERT", timestamp__gte=since)
        if project:
            qs = qs.filter(project=project)
        return list(qs.order_by("-timestamp")[:100])
    except Exception:
        return []


def get_stats(project: str | None = None, days: int = 7) -> dict[str, Any]:
    """İstatistik özeti."""
    try:
        from django.utils import timezone
        from datetime import timedelta
        from .models import SecurityAuditLog
        since = timezone.now() - timedelta(days=days)
        qs = SecurityAuditLog.objects.filter(timestamp__gte=since)
        if project:
            qs = qs.filter(project=project)
        return {"total": qs.count(), "failed": qs.filter(success=False).count(), "auth_fail": qs.filter(event_type="AUTH_FAIL").count(), "days": days}
    except Exception:
        return {"total": 0, "failed": 0, "auth_fail": 0, "days": days}


def _parse_datetime(value: Any) -> Any:
    """datetime veya ISO string'i datetime'a çevir."""
    if value is None:
        return None
    from django.utils.dateparse import parse_datetime
    if hasattr(value, "isoformat"):
        return value
    if isinstance(value, str):
        return parse_datetime(value) or value
    return value


def audit_trail(
    action: str = "ACTION",
    project: str = "erdeniz_security",
    include_result: bool = False,
):
    """
    View veya servis fonksiyonunu otomatik audit logla.
    @audit_trail(action="user_export", project="worktrackere")
    def my_view(request): ...
    """
    from functools import wraps
    import time

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            request = None
            user = None
            if args and hasattr(args[0], "META"):
                request = args[0]
                user = getattr(request, "user", None)
            start = time.time()
            success = True
            details: dict[str, Any] = {}
            result = None
            try:
                result = func(*args, **kwargs)
                if hasattr(result, "status_code") and result.status_code >= 400:
                    success = False
                if include_result and result is not None:
                    details["result"] = str(result)[:200]
                return result
            except Exception as e:
                success = False
                details["error"] = str(e)[:200]
                raise
            finally:
                duration_ms = int((time.time() - start) * 1000)
                resource = (request.path[:255] if request and getattr(request, "path", None) else action)
                log_event(
                    action,
                    resource,
                    project,
                    user=user,
                    request=request,
                    success=success,
                    details=details or None,
                    duration_ms=duration_ms,
                )
        return _wrapped
    return decorator


def export_audit_logs(
    project: str | None = None,
    since: Any = None,
    until: Any = None,
    event_types: list[str] | None = None,
    format: str = "json",
    limit: int = 10000,
) -> str:
    """
    Audit logları dışa aktar. JSON veya CSV.
    Dönen JSON: {"count": N, "project": "...", "records": [...]}
    """
    import json
    import csv
    from io import StringIO

    try:
        from .models import SecurityAuditLog

        qs = SecurityAuditLog.objects.all().order_by("-timestamp")
        if project:
            qs = qs.filter(project=project)
        since_dt = _parse_datetime(since)
        if since_dt:
            qs = qs.filter(timestamp__gte=since_dt)
        until_dt = _parse_datetime(until)
        if until_dt:
            qs = qs.filter(timestamp__lte=until_dt)
        if event_types:
            qs = qs.filter(event_type__in=event_types)
        qs = qs[:limit]

        def record_to_dict(rec: Any) -> dict[str, Any]:
            return {
                "id": rec.pk,
                "timestamp": rec.timestamp.isoformat() if hasattr(rec.timestamp, "isoformat") else str(rec.timestamp),
                "event_type": rec.event_type,
                "project": rec.project,
                "resource": rec.resource,
                "success": rec.success,
                "ip_address": str(rec.ip_address) if rec.ip_address else "",
                "user_id": rec.user_id,
                "duration_ms": rec.duration_ms,
                "details": rec.details if isinstance(rec.details, dict) else {},
            }

        records = [record_to_dict(r) for r in qs]
        count = len(records)

        if format == "csv":
            out = StringIO()
            if not records:
                return "timestamp,event_type,project,resource,success,ip_address,user_id,duration_ms,details\n"
            writer = csv.DictWriter(out, fieldnames=list(records[0].keys()), extrasaction="ignore")
            writer.writeheader()
            for r in records:
                r["details"] = json.dumps(r["details"], ensure_ascii=False, default=str)
                writer.writerow(r)
            return out.getvalue()

        return json.dumps(
            {"count": count, "project": project or "", "records": records},
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    except Exception as e:
        return json.dumps({"error": str(e), "records": []}, ensure_ascii=False, indent=2, default=str)
