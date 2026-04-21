from django.apps import AppConfig


class MehlrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mehlr'
    verbose_name = 'MEHLR AI Engine'

    def ready(self):
        import mehlr.signals  # noqa — sinyalleri kayıt et
