from django.db import migrations, models

from programs.fpl_values import MAX_MATERIALIZED_SIZE, limits_for_period


# The FPL thresholds live in the _FPL_DEFAULTS constant in programs/models.py;
# FederalPoveryLimit stores only a year and a period pointing into it. That works for
# the calculators, which resolve limits in Python through get_limit(), but it means
# anything reading the database alone -- the dbt/Metabase analytics pipeline -- cannot
# compute a percent-of-FPL band. MFB-1182 needs exactly that, to segment the CESN
# dashboard by income without ever exposing a household's actual income.
#
# This creates the mirror table and fills it from the constant. Nothing about the
# eligibility path changes: get_limit() and as_dict() still read the constant, and a
# test asserts the table reproduces get_limit() for every period and size so the two
# cannot drift. When a new year is added to the constant, `manage.py sync_fpl_values`
# brings the table forward -- this migration is the initial fill, not the mechanism.
#
# The constant is imported here rather than inlined. A data migration that reads app
# code is normally a smell, because the code can change under a migration that already
# ran. It is safe in this direction: the table is a derived mirror, re-running the sync
# is idempotent, and the parity test fails loudly if the two ever disagree.
def populate(apps, schema_editor):
    from programs.models import _get_fpl_data

    FederalPovertyLimitValue = apps.get_model("programs", "FederalPovertyLimitValue")

    rows = [
        FederalPovertyLimitValue(period=period, household_size=size, annual_limit=limit)
        for period, table in _get_fpl_data().items()
        for size, limit in limits_for_period(table, MAX_MATERIALIZED_SIZE).items()
    ]

    FederalPovertyLimitValue.objects.bulk_create(rows, ignore_conflicts=True)
    print(f"✅ materialized {len(rows)} FPL threshold rows")


def clear(apps, schema_editor):
    FederalPovertyLimitValue = apps.get_model("programs", "FederalPovertyLimitValue")
    FederalPovertyLimitValue.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0170_deactivate_il_rent_asst"),
    ]

    operations = [
        migrations.CreateModel(
            name="FederalPovertyLimitValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period", models.CharField(db_index=True, max_length=32)),
                ("household_size", models.PositiveSmallIntegerField()),
                ("annual_limit", models.PositiveIntegerField()),
            ],
            options={
                "ordering": ("period", "household_size"),
            },
        ),
        migrations.AddConstraint(
            model_name="federalpovertylimitvalue",
            constraint=models.UniqueConstraint(
                fields=("period", "household_size"), name="unique_fpl_value_per_size"
            ),
        ),
        migrations.RunPython(populate, clear),
    ]
