import django.db.models.deletion
from django.db import migrations, models

from apps.core.tenant_context import tenant_unscoped


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "DressifyeUser")
    StyleSession = apps.get_model("styling", "StyleSession")
    with tenant_unscoped():
        for row in StyleSession.objects.filter(tenant_id__isnull=True).iterator():
            tid = (
                User.objects.filter(pk=row.user_id)
                .values_list("tenant_id", flat=True)
                .first()
            )
            if tid:
                StyleSession.objects.filter(pk=row.pk).update(tenant_id=tid)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("styling", "0002_alter_stylesession_options_stylesession_context_and_more"),
        ("accounts", "0002_dressifyeuser_tenant"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="stylesession",
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
            model_name="stylesession",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tenants.tenant",
            ),
        ),
    ]
