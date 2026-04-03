from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0150_backfill_screen_current_benefits"),
    ]

    operations = [
        migrations.RenameField(
            model_name="screen",
            old_name="has_ma_macfc",
            new_name="has_ma_cfc",
        ),
    ]
