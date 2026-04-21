import logging
import time

logger = logging.getLogger(__name__)


def _process_makeup_session_impl(session_id: int) -> None:
    from django.conf import settings
    from apps.core.clients.mehlr_client import MEHLRClient
    from apps.core.tenant_context import use_tenant
    from apps.beauty.models import MakeupSession
    from apps.analytics.services import record_usage_event

    from apps.subscriptions.models import FeatureUsage
    from apps.subscriptions.services import can_use_feature, increment_usage

    try:
        session = MakeupSession.objects.select_related(
            "user", "applied_look"
        ).get(id=session_id)
    except MakeupSession.DoesNotExist:
        logger.error("MakeupSession bulunamadı: %s", session_id)
        return

    if not can_use_feature(session.user, FeatureUsage.FEATURE_MAKEUP):
        session.status = "failed"
        session.output_data = {"error": "quota_exceeded"}
        session.save()
        return

    tenant = getattr(session.user, "tenant", None)
    with use_tenant(tenant):
        session.status = "processing"
        session.save(update_fields=["status"])

        start = time.time()

        from ai_engine.face_analyzer import get_face_context_for_prompt
        face_context = get_face_context_for_prompt(session.input_image)

        look_name = session.applied_look.name if session.applied_look else "Belirtilmemiş"
        look_category = session.applied_look.category if session.applied_look else "Belirtilmemiş"

        prompt = (
            f"Kullanıcı bu makyaj görünümünü denemek istiyor:\n"
            f"Look: {look_name}\n"
            f"Kategori: {look_category}\n"
        )
        if face_context:
            prompt += f"\nKullanıcı yüz bilgileri:\n{face_context}\n"
        prompt += "\nBu look bu kullanıcıya uygun mu? Kısa değerlendirme yap."

        client = MEHLRClient()
        result = client.analyze(
            project=settings.MEHLR_PROJECT,
            prompt=prompt,
            context={
                "task": "virtual_makeup_feedback",
                "session_id": session_id,
                "look_id": session.applied_look.id if session.applied_look else None,
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
                "ai_feedback": "Bu makyaj görünümü size çok yakışacak!",
                "mode": "placeholder",
                "processing_time": elapsed,
            }

        session.save()

        increment_usage(session.user, FeatureUsage.FEATURE_MAKEUP)
        record_usage_event(
            session.user,
            "makeup",
            metadata={"session_id": session_id},
            session_id=str(session_id),
        )

        logger.info("MakeupSession %s tamamlandı", session_id)


try:
    from celery import shared_task

    @shared_task(bind=True, max_retries=3)
    def process_makeup_session(self, session_id: int):
        """MEHLR'e makyaj look + kullanıcı bilgisi gönder, AI geri bildirimi al."""
        _process_makeup_session_impl(session_id)

except ImportError:

    def process_makeup_session(session_id: int):
        """Celery yoksa senkron çalıştır."""
        _process_makeup_session_impl(session_id)
