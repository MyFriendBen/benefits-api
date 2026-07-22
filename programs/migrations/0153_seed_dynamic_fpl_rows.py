from django.db import migrations


def seed_dynamic_fpl_rows(apps, schema_editor):
    FederalPoveryLimit = apps.get_model("programs", "FederalPoveryLimit")
    FederalPoveryLimit.objects.get_or_create(
        year="THIS_YEAR_FISCAL",
        defaults={"period": "2025"},
    )
    FederalPoveryLimit.objects.get_or_create(
        year="THIS_YEAR_CALENDAR",
        defaults={"period": "2026"},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0152_backfill_has_benefits_categories"),
    ]
    operations = [
        migrations.RunPython(seed_dynamic_fpl_rows, migrations.RunPython.noop),
    ]
