"""
Görüntü işleme — Remove.bg ve gardırop parça analizi (MEHLR) için ortak giriş noktası.
"""


def remove_background(image_file):
    """Remove.bg ile arka plan silme; `apps.services.image_processing` delegasyonu."""
    from apps.services.image_processing import remove_background as _remove_background

    return _remove_background(image_file)


def run_garment_analysis(garment_id: int) -> None:
    """Arka plan temizliği + MEHLR analizi; Celery varsa kuyruk, yoksa senkron."""
    from apps.wardrobe.tasks import analyze_garment_task

    try:
        analyze_garment_task.delay(garment_id)
    except Exception:
        try:
            analyze_garment_task(garment_id)
        except Exception:
            pass
