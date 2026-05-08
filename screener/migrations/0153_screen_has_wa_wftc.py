from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("screener", "0152_backfill_snapshot_value_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="screen",
            name="has_wa_wftc",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
