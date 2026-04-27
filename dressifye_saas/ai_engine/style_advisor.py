"""
Stil önerisi motoru — gardırop + MEHLR akışı `apps.styling.tasks` üzerinden.
"""


def run_style_session(session_id: int) -> None:
    """StyleSession işlemini başlat; Celery varsa delay, aksi halde senkron."""
    from apps.styling.tasks import process_style_session

    if hasattr(process_style_session, "delay"):
        try:
            process_style_session.delay(session_id)
            return
        except Exception:
            pass
    try:
        process_style_session(session_id)
    except Exception:
        pass
