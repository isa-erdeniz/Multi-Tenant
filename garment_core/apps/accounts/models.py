from django.contrib.auth.models import AbstractUser
from django.db import models


class DressifyeUser(AbstractUser):
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="members",
        null=True,
        blank=True,
        help_text="Kayıtta post_save ile kişisel tenant atanır; çoklu kiracı üyeliği için genişletilebilir.",
    )

    # Trial sistemi
    trial_end_date = models.DateTimeField(null=True, blank=True)
    is_trial_active = models.BooleanField(default=True)
