import json
import logging
import re

logger = logging.getLogger(__name__)


def _process_background_removal(garment):
    """
    Remove.bg ile arka plan sil. Başarılıysa garment.image güncelle.
    Hata/kota durumunda orijinal bırak (fallback).
    """
    if not garment.image:
        return
    try:
        from django.core.files.base import ContentFile
        from apps.services.image_processing import remove_background

        png_bytes = remove_background(garment.image)
        if png_bytes:
            import os
            current = garment.image.name or "garment.jpg"
            base = os.path.splitext(os.path.basename(current))[0]
            new_name = f"{base}-nobg.png"
            garment.image.save(new_name, ContentFile(png_bytes), save=True)
            garment.is_ai_processed = True
            garment.save(update_fields=["image", "is_ai_processed"])
            logger.info(f"Garment {garment.id} arka plan temizlendi.")
    except Exception as e:
        logger.warning(f"Arka plan silme atlandı (orijinal korundu): {e}")


def _run_ai_analysis(garment):
    """MEHLR ile stil analizi yap."""
    from django.conf import settings
    from django.utils import timezone
    from apps.core.clients.mehlr_client import MEHLRClient

    client = MEHLRClient()
    result = client.analyze(
        project=settings.MEHLR_PROJECT,
        prompt=(
            f"Bu kıyafeti analiz et ve JSON formatında bilgi ver:\n"
            f"Ad: {garment.name}\n"
            f"Renk: {garment.color or 'belirtilmemiş'}\n"
            f"Marka: {garment.brand or 'belirtilmemiş'}\n"
            f"Kategori: {garment.category.name if garment.category else 'belirtilmemiş'}\n"
            f"Mevsim: {garment.get_season_display()}\n"
            f"Etiketler: {', '.join(garment.tags) if garment.tags else 'yok'}\n\n"
            f"Yanıt formatı: "
            f'{{"style": "casual|formal|sport|elegant", '
            f'"occasion": ["günlük", "iş", ...], '
            f'"color_family": "sıcak|soğuk|nötr", '
            f'"season_fit": ["ilkbahar", "yaz", ...], '
            f'"pairs_well_with": ["üst giyim", "ayakkabı", ...]}}'
        ),
        context={
            "task": "garment_analysis",
            "garment_id": garment.id,
        },
    )

    analysis = None
    if result.get("success"):
        raw = result["data"].get("response", "")
        try:
            analysis = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    analysis = json.loads(match.group())
                except json.JSONDecodeError:
                    pass

    if not analysis:
        analysis = {
            "status": "placeholder",
            "style": "belirsiz",
            "occasion": ["günlük"],
            "color_family": "nötr",
        }

    garment.ai_analysis = analysis
    garment.ai_analyzed_at = timezone.now()
    garment.save(update_fields=["ai_analysis", "ai_analyzed_at"])
    logger.info(f"Garment {garment.id} analiz edildi.")

    _push_to_dressifye_saas_ts(garment)


def _push_to_dressifye_saas_ts(garment) -> None:
    """Garment analizi tamamlandıktan sonra TS evrensel havuza push et."""
    try:
        from apps.core.clients.dressifye_saas_ts_client import DressifyeSaasTSClient

        tenant = getattr(garment.user, "tenant", None)
        tenant_slug = tenant.slug if tenant else "default"

        garment_data = {
            "id": garment.pk,
            "name": garment.name,
            "color": garment.color or "",
            "brand": garment.brand or "",
            "category": garment.category.name if garment.category else "",
            "category_slug": garment.category.slug if garment.category else "",
            "season": garment.get_season_display() if hasattr(garment, "get_season_display") else "",
            "tags": garment.tags if garment.tags else [],
            "ai_style": garment.ai_style or "",
            "ai_occasion": garment.ai_occasion or [],
            "image_url": garment.image.url if garment.image else "",
        }

        client = DressifyeSaasTSClient()
        result = client.push_garment(
            tenant_slug=tenant_slug,
            garment_data=garment_data,
            external_ref=f"django-{garment.pk}",
        )

        if result.get("success"):
            logger.info("Garment %s TS API'ye başarıyla push edildi", garment.pk)
        else:
            logger.warning(
                "Garment %s TS push başarısız: %s", garment.pk, result.get("error")
            )
    except Exception as e:
        # TS push başarısız olsa bile ana task'ı durdurma
        logger.warning(
            "TS push beklenmeyen hata (garment %s): %s", getattr(garment, "pk", "?"), e
        )


try:
    from celery import shared_task

    @shared_task(bind=True, max_retries=3)
    def analyze_garment_task(self, garment_id: int):
        """
        Arka plan silme (Remove.bg) + MEHLR stil analizi.
        Hata durumunda orijinal fotoğraf korunur, analiz devam eder.
        """
        from apps.wardrobe.models import Garment

        try:
            garment = Garment.all_objects.get(id=garment_id)
        except Garment.DoesNotExist:
            logger.error(f"Garment bulunamadı: {garment_id}")
            return

        from apps.core.tenant_context import use_tenant

        tenant = getattr(garment.user, "tenant", None)
        with use_tenant(tenant):
            _process_background_removal(garment)
            _run_ai_analysis(garment)

except ImportError:

    def analyze_garment_task(garment_id: int):
        """Celery yoksa senkron çalıştır."""
        from apps.core.tenant_context import use_tenant
        from apps.wardrobe.models import Garment

        try:
            garment = Garment.all_objects.get(id=garment_id)
        except Garment.DoesNotExist:
            return

        tenant = getattr(garment.user, "tenant", None)
        with use_tenant(tenant):
            _process_background_removal(garment)
            _run_ai_analysis(garment)
