from django.db import migrations


def seed_dynamic_fpl_rows(apps, schema_editor):
    FederalPoveryLimit = apps.get_model("programs", "FederalPoveryLimit")
    # Deliberately reads live _FPL_DEFAULTS instead of hardcoding a snapshot, so a
    # brand-new environment seeds current years, not whatever was current when
    # this migration was written. Already-migrated environments are unaffected,
    # get_or_create makes this a no-op there. Imported here, not at module level,
    # so a database that already applied this migration never re-imports it: the
    # constant could be renamed or removed later without breaking migration
    # loading for every environment, only (loudly, at migrate time) for a brand
    # new one applying this migration for the first time after that happened.
    from programs.models import _FPL_DEFAULTS

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
        ("programs", "0175_ks_lieap_on_has_benefits_step"),
    ]
    operations = [
        migrations.RunPython(seed_dynamic_fpl_rows, migrations.RunPython.noop),
    ]
