from django.db import migrations

TAX_CREDIT_PROGRAMS = {
    "cesn_cpcr",
    "coctc",
    "coeitc",
    "co_tax_credit_care_worker",
    "cpcr",
    "ctc",
    "eitc",
    "fatc",
    "il_aca",
    "il_ctc",
    "il_eitc",
    "ma_aca",
    "ma_cfc",
    "ma_maeitc",
    "shitc",
    "tx_aca",
    "tx_ctc",
    "tx_eitc",
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
