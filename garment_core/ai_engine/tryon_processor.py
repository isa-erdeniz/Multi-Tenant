"""
Sanal deneme (try-on) pipeline — MEHLR tabanlı işlem `apps.tryon.tasks` üzerinden.
"""
import logging

logger = logging.getLogger(__name__)


def run_tryon_session(session_id: int) -> None:
    """Try-on oturumunu işle; Celery varsa kuyruğa alınır, yoksa senkron çalışır."""
    from apps.tryon.tasks import process_tryon_session

    try:
        process_tryon_session.delay(session_id)
    except AttributeError:
        process_tryon_session(session_id)
