from django.db import migrations, models

from programs.fpl_values import MAX_MATERIALIZED_SIZE, limits_for_period


# Creates the FederalPovertyLimitValue mirror and does its initial fill. See the
# model docstring for why it exists; MFB-1182 needs it to band the CESN dashboard
# by income without exposing a household's actual income.
#
# A migration runs once, so it is the initial fill and not the mechanism: the
# deploy runs `manage.py sync_fpl_values` on every release to keep the table
# current as years are added to the constant.
def populate(apps, schema_editor):
    from programs.models import _get_fpl_data

    FederalPovertyLimitValue = apps.get_model("programs", "FederalPovertyLimitValue")

    rows = [
        FederalPovertyLimitValue(period=period, household_size=size, annual_limit=limit)
        for period, table in _get_fpl_data().items()
        for size, limit in limits_for_period(table, MAX_MATERIALIZED_SIZE).items()
    ]

    FederalPovertyLimitValue.objects.bulk_create(rows)
    print(f"✅ materialized {len(rows)} FPL threshold rows")


def clear(apps, schema_editor):
    FederalPovertyLimitValue = apps.get_model("programs", "FederalPovertyLimitValue")
    FederalPovertyLimitValue.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0172_consolidate_shared_program_categories"),
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
