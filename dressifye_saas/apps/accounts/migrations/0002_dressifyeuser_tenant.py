# Generated manually — personal Tenant per existing user, then require tenant

import django.db.models.deletion
from django.db import migrations, models
from django.utils.text import slugify


def backfill_personal_tenants(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    User = apps.get_model("accounts", "DressifyeUser")
    for u in User.objects.filter(tenant_id__isnull=True).iterator():
        email = (getattr(u, "email", None) or "") or ""
        base = (slugify(email.split("@")[0] or "workspace") or "workspace")[:50]
        slug = f"{base}-u{u.pk}"
        n = 0
        while Tenant.objects.filter(slug=slug).exists():
            n += 1
            slug = f"{base}-u{u.pk}-{n}"
        t = Tenant.objects.create(
            name=email or getattr(u, "username", None) or str(u.pk),
            slug=slug,
            domain="",
            owner_user_id=u.pk,
            is_active=True,
        )
        User.objects.filter(pk=u.pk).update(tenant_id=t.id)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="dressifyeuser",
            name="tenant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="members",
                to="tenants.tenant",
            ),
        ),
        migrations.RunPython(backfill_personal_tenants, noop_reverse),
    ]
