from django.db import migrations


def forward(apps, schema_editor):
    """
    Flag wa_ssi for the WA white label as selectable on the has-benefits step.
    Matches the pattern from 0142_audit_show_in_has_benefits_step.py for ssi
    in other white labels.
    """
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(white_label__code="wa", name_abbreviated="wa_ssi").update(
        show_in_has_benefits_step=True,
        active=True,
    )


def reverse(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(white_label__code="wa", name_abbreviated="wa_ssi").update(
        show_in_has_benefits_step=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0149_backfill_wa_ssi_base_program"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
