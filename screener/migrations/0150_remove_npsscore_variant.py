# Generated migration to remove the variant field from NPSScore.
# The NPS survey is no longer an A/B experiment — it is controlled solely
# by the 'nps_survey' feature flag and always renders the inline variant.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0149_backfill_has_head_start_from_has_chs"),
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
