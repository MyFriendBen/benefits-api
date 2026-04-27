from django.db import migrations


def backfill_wa_ssi_base_program(apps, schema_editor):
    """
    Map wa_ssi → base_program="ssi" so it groups with other SSI programs in
    cross-WL aggregations. Mirrors entries added in
    0138_backfill_has_calculator_base_program.py for ssi/tx_ssi/cesn_ssi.

    Idempotent: only updates rows where base_program is not already set.
    """
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(name_abbreviated="wa_ssi", base_program__isnull=True).update(base_program="ssi")


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0148_alter_program_external_name"),
    ]

    operations = [
        migrations.RunPython(backfill_wa_ssi_base_program, migrations.RunPython.noop),
    ]
