import logging
import time

logger = logging.getLogger(__name__)


def _process_avatar_session_impl(session_id: int) -> None:
    from django.conf import settings
    from apps.core.clients.mehlr_client import MEHLRClient
    from apps.core.tenant_context import use_tenant
    from apps.avatar.models import AvatarSession
    from apps.analytics.services import record_usage_event
    from apps.subscriptions.models import FeatureUsage
    from apps.subscriptions.services import can_use_feature, increment_usage

    try:
        session = AvatarSession.objects.select_related("user", "style").get(id=session_id)
    except AvatarSession.DoesNotExist:
        logger.error("AvatarSession bulunamadı: %s", session_id)
        return

    if not can_use_feature(session.user, FeatureUsage.FEATURE_AVATAR):
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
        face_context = get_face_context_for_prompt(session.input_selfie)

        style_name = session.style.name if session.style else "Gerçekçi"
        style_category = session.style.category if session.style else "Genel"

        prompt = (
            f"Kullanıcı için AI avatar oluşturulacak.\n"
            f"Stil: {style_name} ({style_category})\n"
        )
        if session.style and session.style.prompt_template:
            prompt += f"Stil şablonu: {session.style.prompt_template}\n"
        if face_context:
            prompt += f"\nKullanıcı yüz bilgileri:\n{face_context}\n"
        prompt += "\nBu stile uygun bir avatar açıklaması üret."

        client = MEHLRClient()
        result = client.analyze(
            project=settings.MEHLR_PROJECT,
            prompt=prompt,
            context={
                "task": "virtual_avatar_feedback",
                "session_id": session_id,
                "style_id": session.style.id if session.style else None,
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
                "ai_feedback": "Avatarınız oluşturuluyor, çok yakında hazır olacak!",
                "mode": "placeholder",
                "processing_time": elapsed,
            }

        session.save()

        increment_usage(session.user, FeatureUsage.FEATURE_AVATAR)
        record_usage_event(
            session.user,
            "avatar",
            metadata={"session_id": session_id},
            session_id=str(session_id),
        )

        logger.info("AvatarSession %s tamamlandı", session_id)


try:
    from celery import shared_task

    @shared_task(bind=True, max_retries=3)
    def process_avatar_session(self, session_id: int):
        """MEHLR'e avatar stili + selfie bilgisi gönder, AI geri bildirimi al."""
        _process_avatar_session_impl(session_id)

except ImportError:

    def process_avatar_session(session_id: int):
        """Celery yoksa senkron çalıştır."""
        _process_avatar_session_impl(session_id)
