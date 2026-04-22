# Migration to remove the variant field from NPSScore.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0150_backfill_screen_current_benefits"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="npsscore",
            name="nps_variant_idx",
        ),
        migrations.RemoveField(
            model_name="npsscore",
            name="variant",
        ),
    ]
