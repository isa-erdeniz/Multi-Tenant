import django.db.models.deletion
from django.db import migrations, models

from apps.core.tenant_context import tenant_unscoped


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "DressifyeUser")
    TryOnSession = apps.get_model("tryon", "TryOnSession")
    with tenant_unscoped():
        for row in TryOnSession.objects.filter(tenant_id__isnull=True).iterator():
            tid = (
                User.objects.filter(pk=row.user_id)
                .values_list("tenant_id", flat=True)
                .first()
            )
            if tid:
                TryOnSession.objects.filter(pk=row.pk).update(tenant_id=tid)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tryon", "0002_alter_tryonsession_options_and_more"),
        ("accounts", "0002_dressifyeuser_tenant"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tryonsession",
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
            model_name="tryonsession",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tenants.tenant",
            ),
        ),
    ]
