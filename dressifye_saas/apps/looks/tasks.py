import logging
import time

logger = logging.getLogger(__name__)


def _process_look_apply_session_impl(session_id: int) -> None:
    import json
    from django.conf import settings
    from apps.core.clients.mehlr_client import MEHLRClient
    from apps.core.tenant_context import use_tenant
    from apps.looks.models import LookApplySession
    from apps.analytics.services import record_usage_event
    from apps.subscriptions.models import FeatureUsage
    from apps.subscriptions.services import can_use_feature, increment_usage

    try:
        session = LookApplySession.objects.select_related("user", "look").get(id=session_id)
    except LookApplySession.DoesNotExist:
        logger.error("LookApplySession bulunamadı: %s", session_id)
        return

    if not can_use_feature(session.user, FeatureUsage.FEATURE_LOOK_APPLY):
        session.status = "failed"
        session.output_data = {"error": "quota_exceeded"}
        session.save()
        return

    tenant = getattr(session.user, "tenant", None)
    with use_tenant(tenant):
        session.status = "processing"
        session.save(update_fields=["status"])

        start = time.time()

        look_name = session.look.name if session.look else "Belirtilmemiş"
        look_category = session.look.category if session.look else "Genel"
        components = session.look.components_json if session.look else {}
        components_summary = json.dumps(components, ensure_ascii=False)[:300] if components else "Bileşen bilgisi yok"

        client = MEHLRClient()
        result = client.analyze(
            project=settings.MEHLR_PROJECT,
            prompt=(
                f"Kullanıcı şu hazır görünüm paketini uygulamak istiyor:\n"
                f"Look: {look_name} ({look_category})\n"
                f"Bileşenler: {components_summary}\n\n"
                f"Bu görünüm paketi kullanıcıya yakışır mı? "
                f"Makyaj, saç ve kıyafet kombinasyonu hakkında kısa bir değerlendirme yap."
            ),
            context={
                "task": "virtual_look_apply_feedback",
                "session_id": session_id,
                "look_id": session.look.id if session.look else None,
            },
        )

        elapsed = time.time() - start

        if result.get("success"):
            session.status = "completed"
            session.output_data = {
                "ai_feedback": result["data"].get("response", ""),
                "mode": "text_feedback",
                "processing_time": elapsed,
            }
        else:
            session.status = "completed"
            session.output_data = {
                "ai_feedback": "Bu görünüm paketi size çok yakışacak!",
                "mode": "placeholder",
                "processing_time": elapsed,
            }

        session.save()

        increment_usage(session.user, FeatureUsage.FEATURE_LOOK_APPLY)
        record_usage_event(
            session.user,
            "look_apply",
            metadata={"session_id": session_id},
            session_id=str(session_id),
        )

        logger.info("LookApplySession %s tamamlandı", session_id)


try:
    from celery import shared_task

    @shared_task(bind=True, max_retries=3)
    def process_look_apply_session(self, session_id: int):
        """MEHLR'e look paket bileşenleri gönder, AI geri bildirimi al."""
        _process_look_apply_session_impl(session_id)

except ImportError:

    def process_look_apply_session(session_id: int):
        """Celery yoksa senkron çalıştır."""
        _process_look_apply_session_impl(session_id)
