import logging
import time

logger = logging.getLogger(__name__)


def _process_hair_session_impl(session_id: int) -> None:
    from django.conf import settings
    from apps.core.clients.mehlr_client import MEHLRClient
    from apps.core.tenant_context import use_tenant
    from apps.hair.models import HairSession
    from apps.analytics.services import record_usage_event

    try:
        session = HairSession.objects.select_related(
            "user", "applied_style", "applied_color"
        ).get(id=session_id)
    except HairSession.DoesNotExist:
        logger.error("HairSession bulunamadı: %s", session_id)
        return

    tenant = getattr(session.user, "tenant", None)
    with use_tenant(tenant):
        session.status = "processing"
        session.save(update_fields=["status"])

        start = time.time()

        style_name = session.applied_style.name if session.applied_style else "Belirtilmemiş"
        style_category = session.applied_style.category if session.applied_style else "Belirtilmemiş"
        color_name = session.applied_color.name if session.applied_color else "Belirtilmemiş"
        color_hex = session.applied_color.hex_code if session.applied_color else ""

        client = MEHLRClient()
        result = client.analyze(
            project=settings.MEHLR_PROJECT,
            prompt=(
                f"Kullanıcı saç stilini sanal olarak değiştirmek istiyor:\n"
                f"Stil: {style_name} ({style_category})\n"
                f"Renk: {color_name}{' (' + color_hex + ')' if color_hex else ''}\n\n"
                f"Bu saç stili ve rengi kullanıcıya yakışır mı? "
                f"Yüz şekline ve genel görünüme göre kısa bir değerlendirme yap."
            ),
            context={
                "task": "virtual_hair_feedback",
                "session_id": session_id,
                "style_id": session.applied_style.id if session.applied_style else None,
                "color_id": session.applied_color.id if session.applied_color else None,
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
                "ai_feedback": "Bu saç stili size çok yakışacak!",
                "mode": "placeholder",
                "processing_time": elapsed,
            }

        session.save()

        record_usage_event(
            session.user,
            "hair",
            metadata={"session_id": session_id},
            session_id=str(session_id),
        )

        logger.info("HairSession %s tamamlandı", session_id)


try:
    from celery import shared_task

    @shared_task(bind=True, max_retries=3)
    def process_hair_session(self, session_id: int):
        """MEHLR'e saç stili + renk bilgisi gönder, AI geri bildirimi al."""
        _process_hair_session_impl(session_id)

except ImportError:

    def process_hair_session(session_id: int):
        """Celery yoksa senkron çalıştır."""
        _process_hair_session_impl(session_id)
