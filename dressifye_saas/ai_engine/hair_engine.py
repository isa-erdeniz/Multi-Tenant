"""
Saç Stili & Renk Değiştirme Motoru — MEHLR tabanlı saç analizi.
"""
import logging

logger = logging.getLogger(__name__)


def run_hair_session(session_id: int) -> None:
    """Saç değiştirme oturumunu işle; Celery varsa kuyruğa alınır, yoksa senkron."""
    from apps.hair.tasks import process_hair_session

    try:
        process_hair_session.delay(session_id)
    except AttributeError:
        process_hair_session(session_id)
