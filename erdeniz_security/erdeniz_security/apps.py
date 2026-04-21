from django.apps import AppConfig


class ErdenizSecurityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erdeniz_security"
    verbose_name = "ErdenizTech Güvenlik"

    def ready(self) -> None:
        import logging
        import os
        from django.conf import settings

        from .config import validate_configuration

        logger = logging.getLogger(__name__)
        for e in validate_configuration():
            logger.warning("ErdenizGüvenlik: %s", e)

        # Türkçe dil ayarını kontrol et
        if not hasattr(settings, "LANGUAGE_CODE"):
            import warnings
            warnings.warn(
                "LANGUAGE_CODE ayarı bulunamadı. Türkçe için LANGUAGE_CODE='tr' ekleyin.",
                UserWarning,
                stacklevel=2,
            )

        # Locale path'i otomatik ekle
        locale_path = os.path.join(os.path.dirname(__file__), "locale")
        if hasattr(settings, "LOCALE_PATHS") and locale_path not in list(settings.LOCALE_PATHS):
            settings.LOCALE_PATHS = list(settings.LOCALE_PATHS) + [locale_path]
