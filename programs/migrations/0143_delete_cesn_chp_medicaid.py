from django.db import migrations


def delete_cesn_insurance_programs(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(
        white_label__code="cesn",
        name_abbreviated__in=("cesn_chp", "cesn_medicaid"),
    ).delete()


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0142_audit_show_in_has_benefits_step"),
    ]

    operations = [
        migrations.RunPython(delete_cesn_insurance_programs, reverse),
    ]
