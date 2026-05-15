from django.db import migrations


def deactivate_my_spark(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    co_wl = WhiteLabel.objects.get(code="co")
    Program.objects.filter(name_abbreviated="myspark", white_label=co_wl).update(active=False)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0152_backfill_has_benefits_categories"),
        ("screener", "0152_backfill_snapshot_value_type"),
    ]
    operations = [
        # noop reverse: rolling back should not reactivate — reactivation should be handled separately
        migrations.RunPython(deactivate_my_spark, migrations.RunPython.noop),
    ]
