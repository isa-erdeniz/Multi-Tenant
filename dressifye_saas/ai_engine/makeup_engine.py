"""
AR Makyaj Uygulama Motoru — MEHLR tabanlı yüz analizi ve look önerisi.
"""
import logging

logger = logging.getLogger(__name__)


def run_makeup_session(session_id: int) -> None:
    """Makyaj oturumunu işle; Celery varsa kuyruğa alınır, yoksa senkron."""
    from apps.beauty.tasks import process_makeup_session

    try:
        process_makeup_session.delay(session_id)
    except AttributeError:
        process_makeup_session(session_id)
