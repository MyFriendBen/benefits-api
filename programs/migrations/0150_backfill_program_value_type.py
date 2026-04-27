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


def backfill_program_value_type(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(name_abbreviated__in=TAX_CREDIT_PROGRAMS).update(value_type="tax_credit")
    Program.objects.exclude(name_abbreviated__in=TAX_CREDIT_PROGRAMS).update(value_type="benefit")


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0149_convert_program_value_type_to_charfield"),
    ]

    operations = [
        migrations.RunPython(backfill_program_value_type, reverse_backfill),
    ]
