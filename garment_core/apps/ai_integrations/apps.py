from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AIIntegrationsConfig(AppConfig):
    """Django app config for external AI provider orchestration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_integrations"
    verbose_name = _("AI Integrations")

    def ready(self) -> None:
        import apps.ai_integrations.signals  # noqa: F401
