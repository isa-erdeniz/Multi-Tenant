import django.db.models.deletion
from django.db import migrations, models

from apps.core.tenant_context import tenant_unscoped


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "DressifyeUser")
    Garment = apps.get_model("wardrobe", "Garment")
    Outfit = apps.get_model("wardrobe", "Outfit")
    WearLog = apps.get_model("wardrobe", "WearLog")
    WardrobeTag = apps.get_model("wardrobe", "WardrobeTag")

    with tenant_unscoped():
        for g in Garment.objects.filter(tenant_id__isnull=True).iterator():
            tid = (
                User.objects.filter(pk=g.user_id)
                .values_list("tenant_id", flat=True)
                .first()
            )
            if tid:
                Garment.objects.filter(pk=g.pk).update(tenant_id=tid)

        for o in Outfit.objects.filter(tenant_id__isnull=True).iterator():
            tid = (
                User.objects.filter(pk=o.user_id)
                .values_list("tenant_id", flat=True)
                .first()
            )
            if tid:
                Outfit.objects.filter(pk=o.pk).update(tenant_id=tid)

        for w in WearLog.objects.filter(tenant_id__isnull=True).iterator():
            tid = (
                User.objects.filter(pk=w.user_id)
                .values_list("tenant_id", flat=True)
                .first()
            )
            if tid:
                WearLog.objects.filter(pk=w.pk).update(tenant_id=tid)

        for t in WardrobeTag.objects.filter(tenant_id__isnull=True).iterator():
            gid = t.garment_id
            if not gid:
                continue
            tid = (
                Garment.objects.filter(pk=gid)
                .values_list("tenant_id", flat=True)
                .first()
            )
            if tid:
                WardrobeTag.objects.filter(pk=t.pk).update(tenant_id=tid)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("wardrobe", "0004_premium_wardrobe_fields"),
        ("accounts", "0002_dressifyeuser_tenant"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="garment",
            name="tenant",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tenants.tenant",
            ),
        ),
        migrations.AddField(
            model_name="outfit",
            name="tenant",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tenants.tenant",
            ),
        ),
        migrations.AddField(
            model_name="wearlog",
            name="tenant",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tenants.tenant",
            ),
        ),
        migrations.AddField(
            model_name="wardrobetag",
            name="tenant",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tenants.tenant",
            ),
        ),
        migrations.RunPython(forwards, noop),
        migrations.AlterField(
            model_name="garment",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tenants.tenant",
            ),
        ),
        migrations.AlterField(
            model_name="outfit",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tenants.tenant",
            ),
        ),
        migrations.AlterField(
            model_name="wearlog",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tenants.tenant",
            ),
        ),
        migrations.AlterField(
            model_name="wardrobetag",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tenants.tenant",
            ),
        ),
    ]
