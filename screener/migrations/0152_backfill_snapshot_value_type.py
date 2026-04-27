from django.db import migrations

TAX_CREDIT_PROGRAMS = {
    "eitc",
    "ctc",
    "coctc",
    "coeitc",
    "fatc",
    "il_ctc",
    "il_eitc",
    "ma_maeitc",
    "shitc",
    "tx_eitc",
    "tx_ctc",
}


def backfill_snapshot_value_type(apps, schema_editor):
    ProgramEligibilitySnapshot = apps.get_model("screener", "ProgramEligibilitySnapshot")
    ProgramEligibilitySnapshot.objects.filter(name_abbreviated__in=TAX_CREDIT_PROGRAMS).update(value_type="tax_credit")
    ProgramEligibilitySnapshot.objects.exclude(name_abbreviated__in=TAX_CREDIT_PROGRAMS).update(value_type="benefit")


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("screener", "0151_remove_npsscore_variant"),
    ]

    operations = [
        migrations.RunPython(backfill_snapshot_value_type, reverse_backfill),
    ]
