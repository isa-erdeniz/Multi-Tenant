from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="IntakeRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tenant_slug", models.SlugField(db_index=True, max_length=120)),
                ("source_origin", models.CharField(blank=True, default="", max_length=512)),
                ("event_type", models.CharField(blank=True, default="generic", max_length=120)),
                ("payload", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="intakerecord",
            index=models.Index(fields=["tenant_slug", "-created_at"], name="intake_inta_tenant__idx"),
        ),
    ]
