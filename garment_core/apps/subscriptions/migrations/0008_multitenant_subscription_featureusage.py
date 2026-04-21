# Multi-tenant: UserSubscription.tenant, FeatureUsage tenant bazlı benzersiz kısıt

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_subscription_tenant(apps, schema_editor):
    UserSubscription = apps.get_model("subscriptions", "UserSubscription")
    User = apps.get_model("accounts", "DressifyeUser")
    for sub in UserSubscription.objects.filter(tenant_id__isnull=True).iterator():
        tid = (
            User.objects.filter(pk=sub.user_id)
            .values_list("tenant_id", flat=True)
            .first()
        )
        if tid:
            UserSubscription.objects.filter(pk=sub.pk).update(tenant_id=tid)


def backfill_featureusage_tenant(apps, schema_editor):
    FeatureUsage = apps.get_model("subscriptions", "FeatureUsage")
    User = apps.get_model("accounts", "DressifyeUser")
    for fu in FeatureUsage.objects.filter(tenant_id__isnull=True).iterator():
        uid = getattr(fu, "user_id", None)
        if not uid:
            continue
        tid = (
            User.objects.filter(pk=uid).values_list("tenant_id", flat=True).first()
        )
        if tid:
            FeatureUsage.objects.filter(pk=fu.pk).update(tenant_id=tid)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0007_plan_usd_pricing"),
        ("accounts", "0002_dressifyeuser_tenant"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="usersubscription",
            name="tenant",
            field=models.ForeignKey(
                help_text="Ödeme ve kota bağlamı; kullanıcının tenant'ı ile eşleşmeli.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subscriptions",
                to="tenants.tenant",
            ),
        ),
        migrations.AddField(
            model_name="featureusage",
            name="tenant",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="feature_usages",
                to="tenants.tenant",
            ),
        ),
        migrations.AlterField(
            model_name="featureusage",
            name="user",
            field=models.ForeignKey(
                blank=True,
                help_text="İsteğe bağlı: son işlemi yapan kullanıcı (denetim).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="feature_usages",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_subscription_tenant, noop),
        migrations.RunPython(backfill_featureusage_tenant, noop),
        migrations.RemoveConstraint(
            model_name="featureusage",
            name="subscriptions_featureusage_user_feature_month_uniq",
        ),
        migrations.AddConstraint(
            model_name="featureusage",
            constraint=models.UniqueConstraint(
                fields=("tenant", "feature_type", "month"),
                name="subscriptions_featureusage_tenant_feature_month_uniq",
            ),
        ),
        migrations.AlterField(
            model_name="usersubscription",
            name="tenant",
            field=models.ForeignKey(
                help_text="Ödeme ve kota bağlamı; kullanıcının tenant'ı ile eşleşmeli.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subscriptions",
                to="tenants.tenant",
            ),
        ),
        migrations.AlterField(
            model_name="featureusage",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="feature_usages",
                to="tenants.tenant",
            ),
        ),
    ]
