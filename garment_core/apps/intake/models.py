from django.db import models


class IntakeRecord(models.Model):
    """
    Marka / proje hatlarından gelen çok kaynaklı veri (Dressifye vitrinine akıtılabilir).
    """

    tenant_slug = models.SlugField(max_length=120, db_index=True)
    source_origin = models.CharField(max_length=512, blank=True, default="")
    event_type = models.CharField(max_length=120, blank=True, default="generic")
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_slug", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_slug}:{self.event_type}@{self.created_at:%Y-%m-%d %H:%M}"
