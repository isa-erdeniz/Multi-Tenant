from django.db import models

from apps.core.tenant_context import get_current_tenant, is_unscoped


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedManager(models.Manager):
    """
    Varsayılan sorgularda tenant filtreler. Bağlam yoksa boş queryset (sızıntı önlemi).
    Migration / özel işler: tenant_unscoped() veya all_objects kullanın.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if is_unscoped():
            return qs
        tenant = get_current_tenant()
        if tenant is None:
            return qs.none()
        return qs.filter(tenant_id=tenant.pk)


class TenantModel(TimeStampedModel):
    """
    Kiracıya bağlı veri. objects = tenant kapsamlı; all_objects = filtre yok.
    """

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="+",
        db_index=True,
    )

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self._ensure_tenant_fk()
        super().save(*args, **kwargs)

    def _ensure_tenant_fk(self):
        if self.tenant_id is not None:
            return
        uid = getattr(self, "user_id", None)
        if uid:
            from django.contrib.auth import get_user_model

            tid = (
                get_user_model()
                .objects.filter(pk=uid)
                .values_list("tenant_id", flat=True)
                .first()
            )
            if tid:
                self.tenant_id = tid
                return
        gid = getattr(self, "garment_id", None)
        if gid:
            from apps.wardrobe.models import Garment

            tid = (
                Garment.all_objects.filter(pk=gid)
                .values_list("tenant_id", flat=True)
                .first()
            )
            if tid:
                self.tenant_id = tid
