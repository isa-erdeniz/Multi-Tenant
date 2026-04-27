"""
AI Avatar Oluşturma Motoru — MEHLR tabanlı selfie → avatar pipeline.
"""
import logging

logger = logging.getLogger(__name__)


def run_avatar_session(session_id: int) -> None:
    """Avatar oluşturma oturumunu işle; Celery varsa kuyruğa alınır, yoksa senkron."""
    from apps.avatar.tasks import process_avatar_session

    try:
        process_avatar_session.delay(session_id)
    except AttributeError:
        process_avatar_session(session_id)
