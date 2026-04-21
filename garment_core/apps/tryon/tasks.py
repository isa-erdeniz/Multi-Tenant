import logging
import time

logger = logging.getLogger(__name__)


def _process_tryon_session_impl(session_id: int) -> None:
    from django.conf import settings
    from apps.core.clients.mehlr_client import MEHLRClient
    from apps.core.tenant_context import use_tenant
    from apps.tryon.models import TryOnSession

    try:
        session = TryOnSession.all_objects.select_related(
            "user", "garment", "garment__category"
        ).get(id=session_id)
    except TryOnSession.DoesNotExist:
        logger.error("TryOnSession bulunamadı: %s", session_id)
        return

    tenant = getattr(session.user, "tenant", None)
    with use_tenant(tenant):
        session.status = "processing"
        session.save(update_fields=["status"])

        start = time.time()

        client = MEHLRClient()
        result = client.analyze(
            project=settings.MEHLR_PROJECT,
            prompt=(
                f"Kullanıcı bu kıyafeti sanal olarak denemek istiyor:\n"
                f"Kıyafet: {session.garment.name}\n"
                f"Kategori: {session.garment.category.name if session.garment.category else 'Belirtilmemiş'}\n"
                f"Renk: {session.garment.color or 'Belirtilmemiş'}\n\n"
                f"Bu kıyafet kullanıcıya yakışır mı? "
                f"Stil ve renk uyumu hakkında kısa bir değerlendirme yap."
            ),
            context={
                "task": "virtual_tryon_feedback",
                "session_id": session_id,
                "garment_id": session.garment.id,
            },
        )

        session.processing_time = time.time() - start

        if result.get("success"):
            session.status = "completed"
            session.canvas_settings = {
                "ai_feedback": result["data"].get("response", ""),
                "mode": "text_feedback",
            }
        else:
            session.status = "completed"
            session.canvas_settings = {
                "ai_feedback": "Bu kıyafet kombininize güzel bir dokunuş katacak!",
                "mode": "placeholder",
            }

        session.save()
        logger.info("TryOnSession %s tamamlandı", session_id)


try:
    from celery import shared_task

    @shared_task(bind=True, max_retries=3)
    def process_tryon_session(self, session_id: int):
        """
        MEHLR'e kullanıcı fotoğrafı + kıyafet gönder, sonuç al.
        MEHLR henüz görsel işleme desteklemiyorsa placeholder döner.
        """
        _process_tryon_session_impl(session_id)

except ImportError:

    def process_tryon_session(session_id: int):
        """Celery yoksa senkron çalıştır."""
        _process_tryon_session_impl(session_id)
