from django.db import migrations

# Deliberately reads live _FPL_DEFAULTS instead of hardcoding a snapshot, so a
# brand-new environment seeds current years, not whatever was current when
# this migration was written. Already-migrated environments are
# unaffected, get_or_create makes this a no-op there.
from programs.models import _FPL_DEFAULTS


def seed_dynamic_fpl_rows(apps, schema_editor):
    FederalPoveryLimit = apps.get_model("programs", "FederalPoveryLimit")

    years = sorted(_FPL_DEFAULTS, key=int)
    latest_year, previous_year = years[-1], years[-2]

    FederalPoveryLimit.objects.get_or_create(
        year="THIS_YEAR_FISCAL",
        defaults={"period": previous_year},
    )
    FederalPoveryLimit.objects.get_or_create(
        year="THIS_YEAR_CALENDAR",
        defaults={"period": latest_year},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0174_consolidate_missed_program_categories"),
    ]
    operations = [
        migrations.RunPython(seed_dynamic_fpl_rows, migrations.RunPython.noop),
    ]
