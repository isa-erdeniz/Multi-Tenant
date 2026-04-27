# Generated manually for weather integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0003_faz2_body_measurements"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="city",
            field=models.CharField(
                blank=True,
                max_length=100,
                help_text="Hava durumu için şehir (örn: İstanbul, İzmir)",
            ),
        ),
    ]
